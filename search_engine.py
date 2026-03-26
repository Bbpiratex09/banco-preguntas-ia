"""
search_engine.py — Motor de búsqueda semántica.

Responsabilidades:
  - Cargar el banco de preguntas desde JSON.
  - Precalcular embeddings en lote (más rápido que uno por uno).
  - Buscar la pregunta más similar comparando texto original y traducido.
"""

import gc
import logging
from typing import Optional

import torch
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException

import pytesseract
from config import AppConfig

logger = logging.getLogger(__name__)


class SearchEngine:
    """Motor de búsqueda semántica sobre un banco de preguntas JSON."""

    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = AppConfig.TESSERACT_CMD

        logger.info("🧠 Cargando modelo de embeddings...")
        self.modelo = SentenceTransformer(AppConfig.MODELO_NOMBRE)

        logger.info("📂 Cargando banco de preguntas...")
        self.df = self._cargar_banco()

        logger.info("🧮 Preparando embeddings...")
        self._preparar_embeddings()
        logger.info("✅ Motor listo.")

    # ─────────────────────────────────────────────────────────────
    # Inicialización
    # ─────────────────────────────────────────────────────────────

    def _cargar_banco(self) -> pd.DataFrame:
        path = AppConfig.BANCO_JSON
        if not path.exists():
            raise FileNotFoundError(
                f"No se encontró '{path}'. "
                "Asegúrate de que el archivo esté en el mismo directorio que app.py."
            )
        return pd.read_json(path)

    def _preparar_embeddings(self) -> None:
        """Calcula embeddings en lote si no existen; de lo contrario los convierte a tensores."""
        if "embedding" not in self.df.columns or self.df["embedding"].isnull().any():
            logger.info("  Calculando embeddings en lote (puede tardar la primera vez)...")
            textos = self.df["pregunta"].astype(str).tolist()
            embeddings = self.modelo.encode(
                textos,
                batch_size=AppConfig.BATCH_SIZE,
                convert_to_tensor=True,
                show_progress_bar=True,
            )
            # Guardar como lista de tensores para acceso rápido
            self.df["embedding"] = list(embeddings)
        else:
            self.df["embedding"] = self.df["embedding"].apply(
                lambda e: torch.tensor(e) if not isinstance(e, torch.Tensor) else e
            )

    # ─────────────────────────────────────────────────────────────
    # Búsqueda
    # ─────────────────────────────────────────────────────────────

    def buscar(self, pregunta: str) -> Optional[pd.Series]:
        """
        Busca la pregunta más similar en el banco.

        Estrategia dual:
          1. Compara el texto tal como fue ingresado.
          2. Lo traduce al inglés y vuelve a comparar.
          3. Devuelve el resultado con mayor similitud coseno.

        Returns:
            pd.Series con los campos de la fila más similar,
            incluido 'similaridad'. None si ocurre un error.
        """
        try:
            stack = torch.stack(self.df["embedding"].tolist())  # (N, D)

            # Comparación con texto original
            emb_orig = self.modelo.encode(pregunta, convert_to_tensor=True)
            sims_orig = util.pytorch_cos_sim(emb_orig, stack)[0]  # (N,)

            # Traducción y comparación
            traduccion = self._traducir(pregunta)
            emb_trad = self.modelo.encode(traduccion, convert_to_tensor=True)
            sims_trad = util.pytorch_cos_sim(emb_trad, stack)[0]

            # Elegir el mejor de los dos
            if sims_trad.max().item() > sims_orig.max().item():
                logger.info(f"Mejor resultado: traducción (sim={sims_trad.max().item():.2f})")
                idx = sims_trad.argmax().item()
                sim = sims_trad[idx].item()
            else:
                logger.info(f"Mejor resultado: original (sim={sims_orig.max().item():.2f})")
                idx = sims_orig.argmax().item()
                sim = sims_orig[idx].item()

            resultado = self.df.iloc[idx].copy()
            resultado["similaridad"] = sim

            self._liberar_memoria()
            return resultado

        except Exception as e:
            logger.error(f"Error en la búsqueda: {e}", exc_info=True)
            return None

    # ─────────────────────────────────────────────────────────────
    # Helpers privados
    # ─────────────────────────────────────────────────────────────

    def _traducir(self, texto: str, destino: str = "en") -> str:
        """Traduce el texto si no está ya en el idioma destino."""
        try:
            idioma = detect(texto)
            if idioma == destino:
                return texto
        except LangDetectException:
            pass  # Si no detecta, intenta traducir de todas formas
        try:
            return GoogleTranslator(source="auto", target=destino).translate(texto)
        except Exception as e:
            logger.warning(f"No se pudo traducir el texto: {e}")
            return texto

    @staticmethod
    def _liberar_memoria() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
