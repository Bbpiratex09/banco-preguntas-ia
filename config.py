"""
config.py — Configuración centralizada de la aplicación.
Modifica este archivo para ajustar rutas, colores y parámetros globales.
"""

import sys
from pathlib import Path


class AppConfig:
    # ── Tesseract ────────────────────────────────────────────────
    # Windows: ruta al ejecutable de Tesseract-OCR
    # Linux/macOS: normalmente ya está en PATH, déjalo como "tesseract"
    TESSERACT_CMD: str = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if sys.platform == "win32"
        else "tesseract"
    )

    # ── Datos ────────────────────────────────────────────────────
    BANCO_JSON: Path = Path("banco_preguntas.json")

    # ── Modelo de embeddings ─────────────────────────────────────
    MODELO_NOMBRE: str = "all-MiniLM-L6-v2"

    # ── Búsqueda ─────────────────────────────────────────────────
    SIMILARITY_THRESHOLD: float = 0.75   # umbral mínimo de similitud
    BATCH_SIZE: int = 64                  # tamaño de lote para encode()

    # ── UI ───────────────────────────────────────────────────────
    BG_COLOR: str = "#f0f4f7"
    IMAGE_MAX_WIDTH: int = 550

    # ── HTTP ─────────────────────────────────────────────────────
    HEADERS: dict = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        "Referer": "https://www.examtopics.com/",
    }
    REQUEST_TIMEOUT: int = 10
