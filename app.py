"""
Banco de Preguntas IA + OCR + Imágenes
Aplicación de escritorio para búsqueda semántica de preguntas con soporte OCR.
"""

import gc
import io
import re
import sys
import logging
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

import requests
import torch
import pandas as pd
from PIL import Image, ImageTk, ImageGrab
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import pytesseract

from config import AppConfig
from search_engine import SearchEngine

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


# =========================================
# 🖥️ CLASE PRINCIPAL DE LA APP
# =========================================
class BancoPreguntasApp:
    def __init__(self, root: tk.Tk, engine: SearchEngine):
        self.root = root
        self.engine = engine
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.root.title("🧠 Banco de Preguntas IA + OCR + Imágenes")
        self.root.geometry("950x850")
        self.root.config(bg=AppConfig.BG_COLOR)

    def _build_ui(self) -> None:
        # Título
        tk.Label(
            self.root,
            text="📘 Banco de Preguntas con OCR, Texto e Imágenes",
            font=("Segoe UI", 16, "bold"),
            bg=AppConfig.BG_COLOR,
            fg="#003366",
        ).pack(pady=10)

        # Caja de texto
        self.caja_texto = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, width=110, height=10, font=("Consolas", 11)
        )
        self.caja_texto.pack(padx=10, pady=5)
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
                bg=color, fg="white", font=("Segoe UI", 11, "bold"), width=15
            ).grid(row=0, column=i, padx=10)

        # Canvas con scroll
        self.canvas = tk.Canvas(self.root, bg=AppConfig.BG_COLOR, highlightthickness=0)
        scroll_y = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.frame_resultado = tk.Frame(self.canvas, bg=AppConfig.BG_COLOR)

        self.frame_resultado.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame_resultado, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll_y.set)

        self.canvas.pack(side="left", fill="both", expand=True)
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
        if not texto:
            messagebox.showwarning("Atención", "Pega o escribe una pregunta antes de buscar.")
            return

        mejor = self.engine.buscar(texto)
        if mejor is None:
            messagebox.showerror("Error", "No se pudo completar la búsqueda.")
            return

        self._mostrar_resultado(mejor)

    def _mostrar_resultado(self, mejor: pd.Series) -> None:
        for widget in self.frame_resultado.winfo_children():
            widget.destroy()

        def label(text, **kwargs):
            tk.Label(
                self.frame_resultado, text=text,
                bg=AppConfig.BG_COLOR, wraplength=800, justify="left",
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
            texto = extraer_texto_ocr(img)
            if texto.strip():
                self.caja_texto.delete("1.0", tk.END)
                self.caja_texto.insert(tk.END, texto.strip())
            else:
                messagebox.showwarning("OCR", "No se detectó texto en la imagen.")
        except Exception as e:
            messagebox.showerror("Error OCR", f"No se pudo procesar la imagen:\n{e}")

    def _pegar_texto_normal(self) -> None:
        try:
            texto = self.root.clipboard_get()
            if texto:
                self.caja_texto.insert(tk.INSERT, texto)
        except tk.TclError:
            pass

    def _evento_pegar(self, event=None):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                texto = extraer_texto_ocr(img)
                if texto.strip():
                    self.caja_texto.delete("1.0", tk.END)
                    self.caja_texto.insert(tk.END, texto.strip())
                    messagebox.showinfo("OCR exitoso", "📸 Texto extraído de la imagen.")
                    return "break"
        except Exception as e:
            logger.warning(f"Error procesando portapapeles: {e}")

        self.root.after(100, self._pegar_texto_normal)
        return "break"

    def _limpiar(self) -> None:
        self.caja_texto.delete("1.0", tk.END)
        for widget in self.frame_resultado.winfo_children():
            widget.destroy()

    def _on_mousewheel(self, event) -> None:
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")


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
