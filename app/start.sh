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

# Corriger le schéma de la base de données si nécessaire
echo "🔧 Vérification du schéma de la base de données..."
python fix_database_schema.py

if [ $? -eq 0 ]; then
    echo "✅ Schéma de la base de données vérifié/corrigé"
else
    echo "⚠️  Erreur lors de la vérification du schéma (peut être normal)"
fi

# Tester le schéma de la base de données
echo "🧪 Test du schéma de la base de données..."
python test_database_schema.py

if [ $? -eq 0 ]; then
    echo "✅ Schéma de la base de données testé avec succès"
else
    echo "❌ Problème avec le schéma de la base de données"
    echo "📊 Logs d'erreur détaillés :"
    python test_database_schema.py 2>&1
    exit 1
fi

# Vérifier les variables d'environnement
echo "🔧 Configuration :"
echo "  - PORT: ${PORT:-8000}"
echo "  - DATABASE_URL: ${DATABASE_URL:-sqlite:///./face_recognition.db}"

# Démarrer l'application
echo "🌐 Démarrage du serveur sur le port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info 