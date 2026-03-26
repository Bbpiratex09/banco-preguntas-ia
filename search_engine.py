"""
search_engine.py — Motor de búsqueda semántica.

Responsabilidades:
  - Cargar el banco de preguntas desde HTML.
  - Precalcular embeddings en lote (más rápido que uno por uno).
  - Buscar la pregunta más similar comparando texto original y traducido.
"""

import gc
import logging
from typing import Optional
from urllib.parse import urljoin

import torch
import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException

import pytesseract
from config import AppConfig

logger = logging.getLogger(__name__)


class SearchEngine:
    """Motor de búsqueda semántica sobre un banco de preguntas HTML."""

    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = AppConfig.TESSERACT_CMD

        logger.info("Cargando modelo de embeddings...")
        self.modelo = SentenceTransformer(AppConfig.MODELO_NOMBRE)

        logger.info("Cargando banco de preguntas...")
        self.df = self._cargar_banco()

        logger.info("Preparando embeddings...")
        self._preparar_embeddings()
        logger.info("Motor listo.")

    # ─────────────────────────────────────────────────────────────
    # Inicialización
    # ─────────────────────────────────────────────────────────────

    def _cargar_banco(self) -> pd.DataFrame:
        path = AppConfig.BANCO_HTML
        if not path.exists():
            raise FileNotFoundError(
                f"No se encontró '{path}'. "
                "Asegúrate de que el archivo HTML esté en el mismo directorio que app.py."
            )
        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        registros = []

        for card in soup.select(".exam-question-card"):
            registro = self._parsear_card(card)
            if registro is not None:
                registros.append(registro)

        if not registros:
            raise ValueError("No se encontraron preguntas válidas en el archivo HTML.")

        return pd.DataFrame(registros)

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

    def _parsear_card(self, card: Tag) -> Optional[dict]:
        header = card.select_one(".card-header")
        body = card.select_one(".question-body")
        if header is None or body is None:
            return None

        numero = self._extraer_numero_pregunta(header.get_text(" ", strip=True))
        tema_tag = header.select_one(".question-title-topic")
        pregunta_tag = next(
            (
                p for p in body.select("p.card-text")
                if "question-answer" not in (p.get("class") or [])
            ),
            None,
        )
        respuesta_tag = body.select_one("p.question-answer")

        pregunta_html = self._extraer_bloques_pregunta(pregunta_tag)
        pregunta_texto = " ".join(
            bloque["contenido"]
            for bloque in pregunta_html
            if bloque["tipo"] == "texto" and bloque["contenido"]
        ).strip()

        opciones = self._extraer_opciones(body)
        respuesta_correcta, respuesta_texto, imagen_respuesta = self._extraer_respuesta(
            respuesta_tag, opciones
        )
        explicacion = self._extraer_explicacion(respuesta_tag)

        return {
            "id": f"q{numero}" if numero is not None else body.get("data-id"),
            "numero": numero,
            "tema": tema_tag.get_text(" ", strip=True) if tema_tag else None,
            "pregunta": pregunta_texto,
            "pregunta_html": pregunta_html,
            "opciones": opciones,
            "respuesta_correcta": respuesta_correcta,
            "respuesta_texto": respuesta_texto,
            "imagen_respuesta": imagen_respuesta,
            "explicacion": explicacion,
        }

    @staticmethod
    def _extraer_numero_pregunta(texto_header: str) -> Optional[int]:
        try:
            return int(texto_header.split("#", 1)[1].split()[0])
        except Exception:
            return None

    def _extraer_bloques_pregunta(self, pregunta_tag: Optional[Tag]) -> list[dict]:
        if pregunta_tag is None:
            return []

        bloques: list[dict] = []
        for child in pregunta_tag.children:
            if isinstance(child, NavigableString):
                texto = self._normalizar_texto(str(child))
                if texto:
                    bloques.append({"tipo": "texto", "contenido": texto})
                continue

            if not isinstance(child, Tag):
                continue

            if child.name == "img":
                src = child.get("src")
                if src:
                    bloques.append(
                        {"tipo": "imagen", "url": self._normalizar_url(src)}
                    )
                continue

            if child.name == "br":
                continue

            texto = self._normalizar_texto(child.get_text(" ", strip=True))
            if texto:
                bloques.append({"tipo": "texto", "contenido": texto})

        return bloques

    def _extraer_opciones(self, body: Tag) -> dict:
        opciones = {}
        for item in body.select(".question-choices-container li.multi-choice-item"):
            letra_tag = item.select_one(".multi-choice-letter")
            if letra_tag is None:
                continue

            letra = (letra_tag.get("data-choice-letter") or letra_tag.get_text()).strip(" .")

            badge = item.select_one(".most-voted-answer-badge")
            if badge is not None:
                badge.extract()

            letra_tag.extract()
            texto = self._normalizar_texto(item.get_text(" ", strip=True))
            opciones[letra] = texto

        return opciones

    def _extraer_respuesta(
        self, respuesta_tag: Optional[Tag], opciones: dict
    ) -> tuple[Optional[str], str, Optional[str]]:
        if respuesta_tag is None:
            return None, "", None

        correct_answer = respuesta_tag.select_one(".correct-answer")
        if correct_answer is None:
            return None, "", None

        img = correct_answer.select_one("img")
        if img is not None and img.get("src"):
            url = self._normalizar_url(img["src"])
            return "[Imagen]", "[Imagen]", url

        respuesta_correcta = self._normalizar_texto(correct_answer.get_text(" ", strip=True))
        respuesta_texto = self._resolver_texto_respuesta(respuesta_correcta, opciones)
        return respuesta_correcta or None, respuesta_texto, None

    @staticmethod
    def _resolver_texto_respuesta(respuesta_correcta: str, opciones: dict) -> str:
        if not respuesta_correcta:
            return ""
        if respuesta_correcta in opciones:
            return opciones[respuesta_correcta]

        partes = [opciones[letra] for letra in respuesta_correcta if letra in opciones]
        return ", ".join(partes) if partes else respuesta_correcta

    def _extraer_explicacion(self, respuesta_tag: Optional[Tag]) -> Optional[str]:
        if respuesta_tag is None:
            return None

        descripcion = respuesta_tag.select_one(".answer-description")
        if descripcion is None:
            return None

        texto = self._normalizar_texto(descripcion.get_text(" ", strip=True))
        return texto or None

    def _normalizar_url(self, url: str) -> str:
        return urljoin(AppConfig.HTML_BASE_URL, url)

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        return " ".join(texto.replace("\xa0", " ").split())
