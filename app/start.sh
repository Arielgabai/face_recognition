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

# Appliquer le patch face_recognition_models
echo "🔧 Application du patch face_recognition_models..."
python -c "import face_recognition_patch"

if [ $? -eq 0 ]; then
    echo "✅ Patch face_recognition_models appliqué avec succès"
else
    echo "⚠️  Patch face_recognition_models non appliqué (peut être normal)"
fi

# Créer les dossiers nécessaires
echo "📁 Création des dossiers nécessaires..."
mkdir -p static/uploads/selfies
mkdir -p static/uploads/photos

# Vérifier et corriger la structure de la base de données
echo "🔍 Vérification de la structure de la base de données..."
python fix_database.py

if [ $? -eq 0 ]; then
    echo "✅ Structure de la base de données vérifiée"
else
    echo "⚠️  Erreur lors de la vérification de la base de données"
fi

# Vérifier les variables d'environnement
echo "🔧 Configuration :"
echo "  - PORT: ${PORT:-10000}"
echo "  - DATABASE_URL: ${DATABASE_URL:-sqlite:///./face_recognition.db}"


# Démarrer l'application
echo "🌐 Démarrage du serveur sur le port ${PORT:-10000}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info 
