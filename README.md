# 🧠 Banco de Preguntas IA + OCR + Imágenes

Aplicación de escritorio en Python que permite buscar respuestas a preguntas de forma semántica, con soporte para entrada por texto, imagen o portapapeles (OCR).

---

## 📸 Demo

> La app detecta tu pregunta —ya sea escrita o pegada como imagen— y encuentra la coincidencia más cercana en tu banco de preguntas JSON, mostrando la respuesta correcta, opciones e implicación.

---

## ✨ Características

- 🔍 **Búsqueda semántica** usando `sentence-transformers` (modelo `all-MiniLM-L6-v2`)
- 🌐 **Soporte multilingüe**: detecta el idioma de la pregunta y la traduce al inglés automáticamente para mejorar los resultados
- 📸 **OCR integrado**: pega una captura de pantalla o carga una imagen, y extrae el texto automáticamente con Tesseract
- 🖼️ **Imágenes de respuesta**: muestra imágenes asociadas a preguntas y explicaciones directamente en la UI
- ⚡ **Embeddings en lote**: calcula todos los vectores del banco al inicio para búsquedas rápidas en tiempo real

---

## 🗂️ Estructura del proyecto

```
banco_preguntas_app/
├── app.py               # Interfaz gráfica (tkinter) y punto de entrada
├── search_engine.py     # Motor de búsqueda semántica
├── config.py            # Configuración centralizada
├── requirements.txt     # Dependencias del proyecto
├── ejemplo_banco.json   # Ejemplo del formato esperado para el banco
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

Coloca tu archivo `banco_preguntas.json` en la raíz del proyecto. Consulta `ejemplo_banco.json` para ver el formato esperado.

---

## 📄 Formato del banco de preguntas (`banco_preguntas.json`)

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

---

## 🖥️ Uso

```bash
python app.py
```

| Acción | Descripción |
|---|---|
| Escribir pregunta | Escribe o pega texto en la caja principal y pulsa **Buscar** |
| `Ctrl + V` con imagen | Si el portapapeles contiene una captura, OCR extrae el texto automáticamente |
| Botón **Cargar Imagen** | Abre un explorador para seleccionar una imagen local |
| Botón **Limpiar** | Borra la pregunta y el resultado actual |

---

## ⚙️ Configuración (`config.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `TESSERACT_CMD` | Ruta al ejecutable de Tesseract | Auto (según SO) |
| `BANCO_JSON` | Ruta al archivo JSON del banco | `banco_preguntas.json` |
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
| `pandas` | Manejo del banco de datos |

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

---

## 📄 Licencia

MIT License — consulta el archivo [LICENSE](LICENSE) para más detalles.
