@echo off
echo ================================================
echo  🚀 Subiendo proyecto a GitHub...
echo ================================================

cd /d "C:\Users\lbendezu\PROYECTO\BANCO"

echo 📁 Inicializando repositorio git...
git init

echo 📄 Agregando archivos...
git add .

echo 💾 Creando commit inicial...
git commit -m "feat: banco de preguntas IA con OCR y búsqueda semántica"

echo ☁️  Creando repositorio y subiendo a GitHub...
gh repo create banco-preguntas-ia --public --source=. --push

echo ================================================
echo  ✅ ¡Listo! Tu proyecto ya está en GitHub.
echo ================================================
pause
