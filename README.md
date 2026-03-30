# 🧠 Banco de Preguntas IA + OCR + Imágenes

Aplicación de escritorio en Python que permite buscar respuestas a preguntas de forma semántica, con soporte para entrada por texto, imagen o portapapeles (OCR).

---

## 📸 Demo

> La app detecta tu pregunta, permite pegar capturas en la caja, procesa OCR al buscar y muestra la coincidencia más cercana respetando el orden visual del HTML original.

---

## ✨ Características

- 🔍 **Búsqueda semántica** usando `sentence-transformers` (modelo `all-MiniLM-L6-v2`)
- 🌐 **Soporte multilingüe**: detecta el idioma de la pregunta y la traduce al inglés automáticamente para mejorar los resultados
- 📸 **OCR diferido**: pega una captura de pantalla o carga una imagen y procesa el OCR al momento de buscar
- 🖼️ **Imágenes de respuesta**: muestra imágenes asociadas a preguntas y explicaciones directamente en la UI
- 📄 **Banco desde HTML**: extrae preguntas, opciones, respuestas e imágenes directamente desde un archivo HTML de examen
- 🧩 **Render visual fiel**: reconstruye la pregunta usando `pregunta_html` para respetar el orden original de texto e imágenes
- ⚡ **Embeddings en lote**: calcula todos los vectores del banco al inicio para búsquedas rápidas en tiempo real

---

## 🗂️ Estructura del proyecto

```
banco_preguntas_app/
├── app.py               # Interfaz gráfica (tkinter) y punto de entrada
├── search_engine.py     # Motor de búsqueda semántica
├── config.py            # Configuración centralizada
├── requirements.txt     # Dependencias del proyecto
├── EXAM-AZ700.html      # Fuente principal de preguntas en HTML
├── ejemplo_banco.json   # Ejemplo del esquema interno reconstruido por el parser
├── .gitignore
└── README.md
```

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/banco-preguntas-ia.git
cd banco-preguntas-ia
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Instalar Tesseract OCR

| Sistema | Instrucción |
|---|---|
| **Windows** | Descargar desde [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) |
| **Ubuntu/Debian** | `sudo apt install tesseract-ocr tesseract-ocr-spa` |
| **macOS** | `brew install tesseract` |

> **Windows**: actualiza la ruta en `config.py` → `TESSERACT_CMD` si instalaste en una ubicación diferente.

### 4. Preparar el banco de preguntas

Coloca tu archivo HTML del examen en la raíz del proyecto. Por defecto la app leerá `EXAM-AZ700.html`.

---

## 📄 Fuente del banco (`EXAM-AZ700.html`)

La aplicación ya no depende directamente de `banco_preguntas.json`. Ahora parsea el HTML del examen y reconstruye internamente este esquema:

```json
[
  {
    "pregunta": "¿Cuál es la función principal de un router?",
    "pregunta_html": [
      { "tipo": "texto", "valor": "¿Cuál es la función principal de un router?" }
    ],
    "opciones": {
      "A": "Conectar dispositivos en una red local",
      "B": "Dirigir paquetes entre redes",
      "C": "Amplificar señales de red",
      "D": "Asignar direcciones IP"
    },
    "respuesta_correcta": "B",
    "respuesta_texto": "Dirigir paquetes entre redes",
    "explicacion": "Un router analiza las direcciones IP destino de los paquetes y los reenvía a través de la ruta más adecuada.",
    "imagen_respuesta": null
  }
]
```

Este esquema sigue siendo útil como referencia, pero ahora se genera a partir del HTML.

---

## 🖥️ Uso

```bash
python app.py
```

| Acción | Descripción |
|---|---|
| Escribir pregunta | Escribe o pega texto en la caja principal y pulsa **Buscar** |
| `Ctrl + V` con imagen | Si el portapapeles contiene una captura o imagen compatible, se inserta una vista previa en la caja |
| Botón **Cargar Imagen** | Abre un explorador para seleccionar una imagen local y la inserta como vista previa |
| Botón **Buscar** con imagen | Ejecuta OCR sobre la imagen pendiente y luego realiza la búsqueda semántica |
| Botón **Limpiar** | Borra la pregunta y el resultado actual |

> En Windows, la app maneja variantes comunes del pegado por teclado para que el portapapeles responda de forma consistente al usar `Ctrl + V`.

---

## ⚙️ Configuración (`config.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `TESSERACT_CMD` | Ruta al ejecutable de Tesseract | Auto (según SO) |
| `BANCO_HTML` | Ruta al archivo HTML del examen | `EXAM-AZ700.html` |
| `HTML_BASE_URL` | URL base para resolver imágenes relativas del HTML | `https://www.examtopics.com/` |
| `MODELO_NOMBRE` | Modelo de sentence-transformers | `all-MiniLM-L6-v2` |
| `SIMILARITY_THRESHOLD` | Umbral mínimo de similitud | `0.75` |
| `BATCH_SIZE` | Tamaño de lote para embeddings | `64` |

---

## 🧪 Dependencias principales

| Librería | Uso |
|---|---|
| `sentence-transformers` | Embeddings semánticos |
| `torch` | Backend de cálculo de tensores |
| `deep-translator` | Traducción automática |
| `langdetect` | Detección de idioma |
| `pytesseract` + `Pillow` | OCR e imágenes |
| `beautifulsoup4` | Parseo del examen HTML |
| `pandas` | Manejo del banco de datos |

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

---

## 📄 Licencia

MIT License — consulta el archivo [LICENSE](LICENSE) para más detalles.
