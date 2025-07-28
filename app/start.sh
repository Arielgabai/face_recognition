#!/bin/bash

echo "🚀 Démarrage de l'application Face Recognition sur Render..."

# Test des importations Python
echo "📋 Test des importations Python..."
python test_imports.py

if [ $? -eq 0 ]; then
    echo "✅ Toutes les importations sont OK"
else
    echo "❌ Erreur dans les importations Python"
    echo "📊 Logs d'erreur détaillés :"
    python test_imports.py 2>&1
    exit 1
fi

# Appliquer le patch face_recognition_models si nécessaire
echo "🔧 Application du patch face_recognition_models..."
python fix_face_recognition_models.py

if [ $? -eq 0 ]; then
    echo "✅ Patch face_recognition_models appliqué avec succès"
else
    echo "⚠️  Patch face_recognition_models non appliqué (peut être normal)"
fi

# Créer les dossiers nécessaires
echo "📁 Création des dossiers nécessaires..."
mkdir -p static/uploads/selfies
mkdir -p static/uploads/photos

# Vérifier les variables d'environnement
echo "🔧 Configuration :"
echo "  - PORT: ${PORT:-8000}"
echo "  - DATABASE_URL: ${DATABASE_URL:-sqlite:///./face_recognition.db}"

# Démarrer l'application
echo "🌐 Démarrage du serveur sur le port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info 