#!/bin/bash

echo "🚀 Démarrage de l'application Face Recognition..."

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

# Vérifier si Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Arrêter les conteneurs existants
echo "🛑 Arrêt des conteneurs existants..."
docker-compose down

# Construire et démarrer les conteneurs
echo "🔨 Construction et démarrage des conteneurs..."
docker-compose up --build -d

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 30

# Vérifier le statut des conteneurs
echo "📊 Statut des conteneurs :"
docker-compose ps

echo ""
echo "✅ Application démarrée avec succès !"
echo ""
echo "🌐 Accès à l'application :"
echo "   - Frontend : http://localhost:8000"
echo "   - API Documentation : http://localhost:8000/docs"
echo ""
echo "📝 Pour voir les logs :"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Pour arrêter l'application :"
echo "   docker-compose down" 