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


# Calculer le nombre optimal de workers
# Formule: (2 x CPU) + 1
# AWS a 2 vCPU donc: (2 x 2) + 1 = 5 workers
WORKERS=${GUNICORN_WORKERS:-5}

# Démarrer l'application avec Gunicorn pour multi-workers
echo "🌐 Démarrage du serveur avec Gunicorn..."
echo "  - Workers: ${WORKERS}"
echo "  - Port: ${PORT:-10000}"
echo "  - Timeout: 120s"

exec gunicorn main:app \
  --workers ${WORKERS} \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-10000} \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
