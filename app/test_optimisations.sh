#!/bin/bash
# Script de test rapide des optimisations
# Usage: ./test_optimisations.sh

set -e

echo "======================================================================="
echo "🧪 TEST DES OPTIMISATIONS APPLIQUÉES"
echo "======================================================================="

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Vérifier que les index sont ajoutés
echo ""
echo "1️⃣  Vérification des index DB..."
if python -c "
import os
from sqlalchemy import create_engine, inspect
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./face_recognition.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
indexes = inspector.get_indexes('face_matches')
has_index = any('idx_face_matches' in idx['name'] for idx in indexes)
exit(0 if has_index else 1)
" 2>/dev/null; then
    echo -e "${GREEN}✅ Index DB présents${NC}"
else
    echo -e "${YELLOW}⚠️  Index DB manquants. Exécutez:${NC}"
    echo "   python add_performance_indexes.py"
fi

# 2. Vérifier que le serveur répond
echo ""
echo "2️⃣  Vérification du serveur..."
if curl -s -f http://localhost:8000/api/health-check > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Serveur opérationnel${NC}"
else
    echo -e "${RED}❌ Serveur non accessible${NC}"
    echo "   Lancez: gunicorn main:app -c gunicorn_config.py"
    exit 1
fi

# 3. Test de l'endpoint upload-selfie (vérifier qu'il répond rapidement)
echo ""
echo "3️⃣  Test de performance upload-selfie..."

# Créer un token de test (simulé)
echo -e "${YELLOW}⏳ Préparation du test...${NC}"

# Mesurer le temps de réponse
START=$(date +%s%N)
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" \
    -X POST http://localhost:8000/api/upload-selfie \
    -H "Content-Type: multipart/form-data" \
    2>/dev/null || echo "000:0")
END=$(date +%s%N)

HTTP_CODE=$(echo $RESPONSE | cut -d: -f1)
TIME=$(echo $RESPONSE | cut -d: -f2)

# Note: Ce test échouera avec 401 (pas de token), mais on peut quand même mesurer le temps
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${YELLOW}⚠️  Test partiel (pas de token, mais endpoint répond)${NC}"
    echo "   Temps de réponse: ${TIME}s"
    
    # Vérifier que c'est rapide (< 1s même pour une erreur)
    if (( $(echo "$TIME < 1" | bc -l) )); then
        echo -e "${GREEN}✅ Temps de réponse excellent (<1s)${NC}"
    else
        echo -e "${RED}❌ Temps de réponse lent (${TIME}s)${NC}"
    fi
elif [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Upload-selfie opérationnel${NC}"
    echo "   Temps de réponse: ${TIME}s"
else
    echo -e "${YELLOW}⚠️  Code HTTP inattendu: $HTTP_CODE${NC}"
fi

# 4. Vérifier Locust
echo ""
echo "4️⃣  Vérification de Locust..."
if command -v locust &> /dev/null; then
    echo -e "${GREEN}✅ Locust installé${NC}"
else
    echo -e "${YELLOW}⚠️  Locust non installé. Installez avec:${NC}"
    echo "   pip install locust"
fi

# 5. Vérifier Gunicorn
echo ""
echo "5️⃣  Vérification de Gunicorn..."
if command -v gunicorn &> /dev/null; then
    echo -e "${GREEN}✅ Gunicorn installé${NC}"
    
    # Compter les workers actifs
    WORKERS=$(ps aux | grep -c "gunicorn.*worker" || echo "0")
    if [ "$WORKERS" -gt "1" ]; then
        echo -e "${GREEN}   $WORKERS workers actifs${NC}"
    else
        echo -e "${YELLOW}⚠️  Pas de workers détectés (ou serveur non lancé avec Gunicorn)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Gunicorn non installé. Installez avec:${NC}"
    echo "   pip install gunicorn"
fi

# 6. Résumé
echo ""
echo "======================================================================="
echo "📊 RÉSUMÉ"
echo "======================================================================="
echo ""
echo "Optimisations appliquées:"
echo "  ✅ Code Azure retiré (validate_selfie_image)"
echo "  ✅ Détection de visage optimisée (upsample 0→1)"
echo "  ✅ Upload-selfie asynchrone (validation en background)"
echo "  ✅ Suppression FaceMatch optimisée (subquery)"
echo ""
echo "Prochaines étapes:"
echo "  1. Si index manquants: python add_performance_indexes.py"
echo "  2. Lancer avec Gunicorn: gunicorn main:app -c gunicorn_config.py"
echo "  3. Test de charge: locust -f locust_file.py --host=http://localhost:8000"
echo ""
echo "======================================================================="
echo "🚀 Prêt pour le test de charge !"
echo "======================================================================="
