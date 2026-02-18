#!/bin/bash


echo "Demarrage de l'application Face Recognition..."

# Test des importations Python
echo "Test des importations Python..."
python test_imports.py

if [ $? -eq 0 ]; then
    echo "Toutes les importations sont OK"
else
    echo "Erreur dans les importations Python"
    python test_imports.py 2>&1
    exit 1
fi

# Appliquer le patch face_recognition_models
echo "Application du patch face_recognition_models..."
python -c "import face_recognition_patch"

if [ $? -eq 0 ]; then
    echo "Patch face_recognition_models applique avec succes"
else
    echo "Patch face_recognition_models non applique (peut etre normal)"
fi

# Créer les dossiers nécessaires
echo "Creation des dossiers necessaires..."
mkdir -p static/uploads/selfies
mkdir -p static/uploads/photos

# Vérifier et corriger la structure de la base de données
echo "Verification de la structure de la base de donnees..."
python fix_database.py

if [ $? -eq 0 ]; then
    echo "Structure de la base de donnees verifiee"
else
    echo "Erreur lors de la verification de la base de donnees"
fi

# Afficher la configuration (SANS secrets)
echo "Configuration :"
echo "  - PORT: ${PORT:-10000}"
if [ -n "$DATABASE_URL" ]; then
    echo "  - DATABASE_URL: (set)"
else
    echo "  - DATABASE_URL: (not set)"
fi
echo "  - GUNICORN_WORKERS: ${GUNICORN_WORKERS:-3}"
echo "  - GUNICORN_THREADS: ${GUNICORN_THREADS:-2}"
echo "  - GUNICORN_TIMEOUT: ${GUNICORN_TIMEOUT:-90}"
echo "  - MATCHING_THREAD_POOL_SIZE: ${MATCHING_THREAD_POOL_SIZE:-1}"

# Démarrer l'application avec Gunicorn
echo "Demarrage du serveur avec Gunicorn..."
echo "  - Configuration: gunicorn_config.py"

exec gunicorn main:app -c gunicorn_config.py
