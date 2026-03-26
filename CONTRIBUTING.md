# 🤝 Cómo contribuir

¡Gracias por tu interés en mejorar este proyecto! Aquí te explicamos cómo hacerlo.

---

## 🔄 Flujo de trabajo

1. **Haz un fork** del repositorio
2. **Crea una rama** descriptiva:
   ```bash
   git checkout -b feat/mejora-ocr
   # o
   git checkout -b fix/error-traduccion
   ```
3. **Haz tus cambios** siguiendo las guías de estilo
4. **Ejecuta las pruebas** antes de subir
5. **Abre un Pull Request** contra `main` con una descripción clara

---

## 📐 Guía de estilo

- Seguimos [PEP 8](https://peps.python.org/pep-0008/)
- Usa **type hints** en todas las funciones nuevas
- Añade **docstrings** a clases y métodos públicos
- Mantén las funciones pequeñas y con una sola responsabilidad
- Configura tu editor para usar **4 espacios** (sin tabs)

Puedes formatear automáticamente con:
```bash
pip install black isort
black .
isort .
```

---

## 🐛 Reportar un bug

Abre un [Issue](../../issues/new) con:
- Descripción del problema
- Pasos para reproducirlo
- Sistema operativo y versión de Python
- Mensaje de error completo (si aplica)

---

## 💡 Proponer una mejora

Abre un [Issue](../../issues/new) con la etiqueta `enhancement` y describe:
- Qué problema resuelve tu propuesta
- Cómo lo implementarías

---

## 📦 Agregar una dependencia

Si tu contribución necesita una librería nueva:
1. Agrégala a `requirements.txt` con la versión mínima (`>=`)
2. Justifica por qué es necesaria en el PR

---

## ✅ Checklist del Pull Request

Antes de abrir tu PR, verifica:

- [ ] El código sigue PEP 8
- [ ] Las funciones nuevas tienen type hints y docstring
- [ ] No se incluyen archivos de datos (`*.json`, modelos, logs)
- [ ] `requirements.txt` está actualizado si agregaste dependencias
- [ ] El README está actualizado si cambiaste el comportamiento

---

¡Gracias por contribuir! 🚀
