"""
Banco de Preguntas IA + OCR + Imágenes
Aplicación de escritorio para búsqueda semántica de preguntas con soporte OCR.
"""

import gc
import base64
import io
import re
import sys
import logging
import struct
from urllib.parse import urljoin
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

import requests
import torch
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image, ImageTk, ImageGrab
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import pytesseract

from config import AppConfig
from search_engine import SearchEngine

if sys.platform == "win32":
    import win32clipboard

# =========================================
# 🪵 LOGGING
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# =========================================
# 🖼️ HELPERS DE IMAGEN
# =========================================
def mostrar_imagen(url: str, frame: tk.Frame, ancho_max: int = 550) -> None:
    """Descarga y muestra una imagen desde una URL dentro de un frame tkinter."""
    try:
        response = requests.get(url, headers=AppConfig.HEADERS, timeout=10)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        if img.width > ancho_max:
            ratio = ancho_max / img.width
            img = img.resize((ancho_max, int(img.height * ratio)), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        lbl = tk.Label(frame, image=img_tk, bg=AppConfig.BG_COLOR)
        lbl.image = img_tk  # evitar garbage collection
        lbl.pack(pady=5)
    except requests.HTTPError as e:
        tk.Label(frame, text=f"❌ Error HTTP: {e}", bg=AppConfig.BG_COLOR).pack()
    except Exception as e:
        logger.warning(f"Error cargando imagen desde {url}: {e}")
        tk.Label(frame, text=f"⚠️ No se pudo cargar la imagen.", bg=AppConfig.BG_COLOR).pack()


def extraer_texto_ocr(img: Image.Image) -> str:
    """Extrae texto de una imagen usando Tesseract OCR."""
    return pytesseract.image_to_string(img, lang="eng+spa")


def cargar_imagen_desde_origen(origen: str) -> Optional[Image.Image]:
    """Carga una imagen desde data URL o desde una URL remota."""
    if not origen:
        return None

    try:
        if origen.startswith("data:image/"):
            _, payload = origen.split(",", 1)
            with Image.open(io.BytesIO(base64.b64decode(payload))) as img:
                return img.copy()

        respuesta = requests.get(
            origen,
            headers=AppConfig.HEADERS,
            timeout=AppConfig.REQUEST_TIMEOUT,
        )
        respuesta.raise_for_status()
        with Image.open(io.BytesIO(respuesta.content)) as img:
            return img.copy()
    except Exception as e:
        logger.warning(f"No se pudo cargar imagen desde origen HTML: {e}")
        return None


def _dib_a_imagen(dib_data: bytes) -> Image.Image:
    """Convierte datos DIB/DIBV5 del portapapeles de Windows a una imagen PIL."""
    header_size = struct.unpack("<I", dib_data[:4])[0]
    bit_count = struct.unpack("<H", dib_data[14:16])[0]
    colors_used = struct.unpack("<I", dib_data[32:36])[0]

    palette_size = 0
    if bit_count <= 8:
        palette_entries = colors_used or (1 << bit_count)
        palette_size = palette_entries * 4

    pixel_offset = 14 + header_size + palette_size
    file_size = 14 + len(dib_data)
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, pixel_offset)

    with Image.open(io.BytesIO(file_header + dib_data)) as img:
        return img.copy()


def obtener_imagen_portapapeles() -> Optional[Image.Image]:
    """Obtiene una imagen desde el portapapeles con fallback nativo para Windows."""
    try:
        contenido = ImageGrab.grabclipboard()
        if isinstance(contenido, Image.Image):
            return contenido
        if isinstance(contenido, list):
            for ruta in contenido:
                try:
                    with Image.open(ruta) as img:
                        return img.copy()
                except Exception:
                    continue
    except Exception as e:
        logger.info(f"Fallo ImageGrab en portapapeles, usando fallback: {e}")

    if sys.platform != "win32":
        return None

    try:
        win32clipboard.OpenClipboard()

        png_format = win32clipboard.RegisterClipboardFormat("PNG")
        if win32clipboard.IsClipboardFormatAvailable(png_format):
            data = win32clipboard.GetClipboardData(png_format)
            with Image.open(io.BytesIO(data)) as img:
                return img.copy()

        dibv5_format = getattr(win32clipboard, "CF_DIBV5", None)
        if dibv5_format and win32clipboard.IsClipboardFormatAvailable(dibv5_format):
            return _dib_a_imagen(win32clipboard.GetClipboardData(dibv5_format))

        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            return _dib_a_imagen(win32clipboard.GetClipboardData(win32clipboard.CF_DIB))

        html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
        if win32clipboard.IsClipboardFormatAvailable(html_format):
            html_data = win32clipboard.GetClipboardData(html_format)
            if isinstance(html_data, bytes):
                html = html_data.decode("utf-8", errors="ignore")
            else:
                html = str(html_data)
            imagen = _extraer_imagen_desde_html_portapapeles(html)
            if imagen is not None:
                return imagen
    except Exception as e:
        logger.warning(f"Error procesando imagen del portapapeles: {e}")
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    return None


def _extraer_imagen_desde_html_portapapeles(html: str) -> Optional[Image.Image]:
    """Extrae una imagen desde un fragmento HTML del portapapeles."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.select("img[src]"):
        origen = tag.get("src", "").strip()
        if not origen:
            continue
        if origen.startswith("//"):
            origen = f"https:{origen}"
        elif origen.startswith("/"):
            origen = urljoin(AppConfig.HTML_BASE_URL, origen)

        imagen = cargar_imagen_desde_origen(origen)
        if imagen is not None:
            logger.info("Imagen recuperada desde HTML del portapapeles.")
            return imagen

    return None


def obtener_formatos_portapapeles() -> list[str]:
    """Devuelve los formatos disponibles actualmente en el portapapeles de Windows."""
    if sys.platform != "win32":
        return []

    formatos = []
    try:
        win32clipboard.OpenClipboard()
        current = 0
        while True:
            current = win32clipboard.EnumClipboardFormats(current)
            if not current:
                break
            try:
                nombre = win32clipboard.GetClipboardFormatName(current)
            except Exception:
                nombre = str(current)
            formatos.append(nombre)
    except Exception as e:
        logger.warning(f"No se pudieron enumerar los formatos del portapapeles: {e}")
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    return formatos


# =========================================
# 🖥️ CLASE PRINCIPAL DE LA APP
# =========================================
class BancoPreguntasApp:
    def __init__(self, root: tk.Tk, engine: SearchEngine):
        self.root = root
        self.engine = engine
        self.status_var = tk.StringVar(value="Motor listo. Esperando texto o imagen.")
        self.imagen_pendiente: Optional[Image.Image] = None
        self.imagen_preview_tk: Optional[ImageTk.PhotoImage] = None
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.root.title("Banco de Preguntas IA")
        self.root.geometry("950x850")
        self.root.config(bg=AppConfig.BG_COLOR)

    def _build_ui(self) -> None:
        header = tk.Frame(
            self.root,
            bg="#ffffff",
            highlightbackground="#d9e2ec",
            highlightthickness=1,
        )
        header.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            header,
            text="Banco de Preguntas IA",
            font=("Segoe UI Semibold", 18),
            bg="#ffffff",
            fg="#102a43",
        ).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            header,
            text="Busca por texto o procesa capturas desde archivo y portapapeles.",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#486581",
        ).pack(anchor="w", padx=18, pady=(0, 10))
        tk.Label(
            header,
            textvariable=self.status_var,
            font=("Segoe UI", 10, "bold"),
            bg="#e6f4ea",
            fg="#1b5e20",
            padx=10,
            pady=6,
        ).pack(anchor="w", padx=18, pady=(0, 14))

        # Caja de texto
        self.caja_texto = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            width=110,
            height=10,
            font=("Consolas", 11),
            relief="solid",
            borderwidth=1,
        )
        self.caja_texto.pack(fill="x", padx=12, pady=6)
        self.caja_texto.bind("<Control-v>", self._evento_pegar)

        # Botones
        frame_botones = tk.Frame(self.root, bg=AppConfig.BG_COLOR)
        frame_botones.pack(pady=10)
        botones = [
            ("🔍 Buscar", self._ejecutar_busqueda, "#0078d7"),
            ("🖼️ Cargar Imagen", self._cargar_imagen, "#33a02c"),
            ("🧹 Limpiar", self._limpiar, "#999999"),
        ]
        for i, (texto, cmd, color) in enumerate(botones):
            tk.Button(
                frame_botones, text=texto, command=cmd,
                bg=color, fg="white", font=("Segoe UI", 11, "bold"), width=16,
                relief="flat", padx=6, pady=8, cursor="hand2"
            ).grid(row=0, column=i, padx=10)

        # Canvas con scroll
        self.canvas = tk.Canvas(self.root, bg=AppConfig.BG_COLOR, highlightthickness=0)
        scroll_y = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.frame_resultado = tk.Frame(self.canvas, bg="#ffffff")

        self.frame_resultado.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame_resultado, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll_y.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        scroll_y.pack(side="right", fill="y")

        # Scroll universal del ratón
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

    # =========================================
    # 🔍 BÚSQUEDA
    # =========================================
    def _ejecutar_busqueda(self) -> None:
        texto = self.caja_texto.get("1.0", tk.END).strip()
        if not texto and self.imagen_pendiente is None:
            messagebox.showwarning("Atención", "Pega o escribe una pregunta antes de buscar.")
            self._actualizar_estado("Escribe o pega una pregunta antes de buscar.", error=True)
            return

        if self.imagen_pendiente is not None:
            try:
                texto_ocr = extraer_texto_ocr(self.imagen_pendiente).strip()
            except Exception as e:
                messagebox.showerror("Error OCR", f"No se pudo procesar la imagen:\n{e}")
                self._actualizar_estado("No se pudo procesar la imagen pegada.", error=True)
                return

            if not texto_ocr:
                messagebox.showwarning("OCR", "No se detectó texto en la imagen.")
                self._actualizar_estado("La imagen pegada no devolvió texto reconocible.", error=True)
                return

            texto = f"{texto}\n{texto_ocr}".strip() if texto else texto_ocr
            self.caja_texto.delete("1.0", tk.END)
            self.caja_texto.insert(tk.END, texto)
            self._actualizar_estado("Imagen procesada y convertida a texto para la búsqueda.", error=False)
            self.imagen_pendiente = None
            self.imagen_preview_tk = None

        mejor = self.engine.buscar(texto)
        if mejor is None:
            messagebox.showerror("Error", "No se pudo completar la búsqueda.")
            self._actualizar_estado("La búsqueda falló. Revisa el texto procesado.", error=True)
            return

        self._mostrar_resultado(mejor)
        self._actualizar_estado(
            f"Coincidencia encontrada con similaridad {mejor['similaridad']:.2f}.",
            error=False,
        )

    def _mostrar_resultado(self, mejor: pd.Series) -> None:
        for widget in self.frame_resultado.winfo_children():
            widget.destroy()

        def label(text, **kwargs):
            tk.Label(
                self.frame_resultado, text=text,
                bg="#ffffff", wraplength=800, justify="left",
                **kwargs
            ).pack(anchor="w")

        label(
            f"✅ Coincidencia ({mejor['similaridad']:.2f})",
            font=("Segoe UI", 12, "bold"), fg="#006400"
        )
        label(f"\n{mejor['pregunta']}", font=("Segoe UI", 11))

        # Imagen de pregunta
        if isinstance(mejor.get("pregunta_html"), list):
            for item in mejor["pregunta_html"]:
                if item.get("tipo") == "imagen":
                    mostrar_imagen(item["url"], self.frame_resultado)

        # Opciones
        if isinstance(mejor.get("opciones"), dict) and mejor["opciones"]:
            label("\nOpciones:", font=("Segoe UI", 11, "bold"), fg="#003366")
            for letra, texto_op in mejor["opciones"].items():
                color = "#006400" if letra == mejor.get("respuesta_correcta") else "#000000"
                label(f"{letra}) {texto_op}", font=("Consolas", 10), fg=color)

        # Respuesta correcta
        label(
            f"\nRespuesta correcta: {mejor.get('respuesta_correcta')} → {mejor.get('respuesta_texto', '')}",
            font=("Segoe UI", 11, "bold"), fg="#d32f2f"
        )

        # Imagen de respuesta
        if mejor.get("imagen_respuesta"):
            mostrar_imagen(mejor["imagen_respuesta"], self.frame_resultado)

        # Explicación
        label(
            f"\n📘 Explicación:\n{mejor.get('explicacion', '—')}",
            font=("Segoe UI", 10)
        )

    # =========================================
    # 📋 OCR Y PORTAPAPELES
    # =========================================
    def _cargar_imagen(self) -> None:
        ruta = filedialog.askopenfilename(
            filetypes=[("Imágenes", "*.jpg *.png *.jpeg *.bmp")]
        )
        if not ruta:
            return
        try:
            img = Image.open(ruta)
            self._insertar_imagen_en_caja(img.copy(), "Imagen cargada. Se procesará al buscar.")
        except Exception as e:
            messagebox.showerror("Error OCR", f"No se pudo procesar la imagen:\n{e}")
            self._actualizar_estado("No se pudo abrir la imagen seleccionada.", error=True)

    def _insertar_imagen_en_caja(self, img: Image.Image, estado: str) -> None:
        preview = img.copy()
        preview.thumbnail((760, 260), Image.LANCZOS)
        self.imagen_preview_tk = ImageTk.PhotoImage(preview)
        self.imagen_pendiente = img.copy()

        self.caja_texto.delete("1.0", tk.END)
        self.caja_texto.image_create(tk.END, image=self.imagen_preview_tk)
        self.caja_texto.insert(tk.END, "\n")
        self._actualizar_estado(estado, error=False)

    def _pegar_texto_normal(self) -> None:
        try:
            texto = self.root.clipboard_get()
            if texto:
                self.caja_texto.insert(tk.INSERT, texto)
        except tk.TclError:
            pass

    def _evento_pegar(self, event=None):
        try:
            img = obtener_imagen_portapapeles()
            if isinstance(img, Image.Image):
                self._insertar_imagen_en_caja(
                    img,
                    "Imagen pegada en la caja. Se procesará al buscar.",
                )
                return "break"
        except Exception as e:
            logger.warning(f"Error procesando portapapeles: {e}")

        self.root.after(100, self._pegar_texto_normal)
        return "break"

    def _limpiar(self) -> None:
        self.caja_texto.delete("1.0", tk.END)
        self.imagen_pendiente = None
        self.imagen_preview_tk = None
        for widget in self.frame_resultado.winfo_children():
            widget.destroy()
        self._actualizar_estado("Interfaz limpia. Esperando nueva entrada.", error=False)

    def _on_mousewheel(self, event) -> None:
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def _actualizar_estado(self, mensaje: str, error: bool = False) -> None:
        self.status_var.set(mensaje)


# =========================================
# 🚀 ENTRY POINT
# =========================================
def main():
    logger.info("Iniciando Banco de Preguntas IA...")
    engine = SearchEngine()
    root = tk.Tk()
    app = BancoPreguntasApp(root, engine)
    root.mainloop()


if __name__ == "__main__":
    main()
