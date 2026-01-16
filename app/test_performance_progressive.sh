#!/bin/bash
# Script de test de charge progressif pour valider les optimisations
# Usage: ./test_performance_progressive.sh

set -e

echo "======================================================================="
echo "🧪 TEST DE PERFORMANCE PROGRESSIF"
echo "======================================================================="

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vérifier que locust est installé
if ! command -v locust &> /dev/null; then
    echo -e "${RED}❌ Locust n'est pas installé${NC}"
    echo "Installation : pip install locust"
    exit 1
fi

# Vérifier que le serveur tourne
if ! curl -s http://localhost:8000/api/health-check > /dev/null 2>&1; then
    echo -e "${RED}❌ Le serveur ne répond pas sur http://localhost:8000${NC}"
    echo "Démarrez le serveur d'abord :"
    echo "  gunicorn main:app -c gunicorn_config.py"
    exit 1
fi

echo -e "${GREEN}✅ Serveur opérationnel${NC}"
echo ""

# Test 1 : Baseline avec 5 users
echo "======================================================================="
echo "📊 TEST 1/4 : Baseline (5 users, 1/s)"
echo "======================================================================="
locust -f locust_file.py \
    --host=http://localhost:8000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=1m \
    --headless \
    --html=results_5users.html \
    --csv=results_5users

echo ""
echo -e "${YELLOW}⏸️  Pause 10s...${NC}"
sleep 10

# Test 2 : 10 users
echo "======================================================================="
echo "📊 TEST 2/4 : Charge modérée (10 users, 2/s)"
echo "======================================================================="
locust -f locust_file.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=2m \
    --headless \
    --html=results_10users.html \
    --csv=results_10users

echo ""
echo -e "${YELLOW}⏸️  Pause 15s...${NC}"
sleep 15

# Test 3 : 20 users
echo "======================================================================="
echo "📊 TEST 3/4 : Charge élevée (20 users, 3/s)"
echo "======================================================================="
locust -f locust_file.py \
    --host=http://localhost:8000 \
    --users=20 \
    --spawn-rate=3 \
    --run-time=3m \
    --headless \
    --html=results_20users.html \
    --csv=results_20users

echo ""
echo -e "${YELLOW}⏸️  Pause 20s...${NC}"
sleep 20

# Test 4 : 30 users (objectif)
echo "======================================================================="
echo "📊 TEST 4/4 : Charge maximale (30 users, 5/s)"
echo "======================================================================="
locust -f locust_file.py \
    --host=http://localhost:8000 \
    --users=30 \
    --spawn-rate=5 \
    --run-time=5m \
    --headless \
    --html=results_30users.html \
    --csv=results_30users

echo ""
echo "======================================================================="
echo "✅ TESTS TERMINÉS"
echo "======================================================================="
echo ""
echo "📊 Résultats disponibles :"
echo "  - results_5users.html   : Baseline"
echo "  - results_10users.html  : Charge modérée"
echo "  - results_20users.html  : Charge élevée"
echo "  - results_30users.html  : Charge maximale"
echo ""
echo "📈 Fichiers CSV générés pour analyse :"
echo "  - results_*_stats.csv"
echo "  - results_*_failures.csv"
echo ""

# Analyse rapide du dernier test
if [ -f "results_30users_stats.csv" ]; then
    echo "======================================================================="
    echo "📊 RÉSUMÉ DU TEST À 30 USERS"
    echo "======================================================================="
    
    # Extraire les statistiques clés
    echo ""
    echo "Temps de réponse moyens :"
    tail -n +2 results_30users_stats.csv | awk -F',' '{printf "  %-35s : %6s ms\n", $2, $5}'
    
    echo ""
    echo "Taux d'échec :"
    tail -n +2 results_30users_stats.csv | awk -F',' '{
        if ($5 != "Average Response Time") {
            failures = $4;
            total = $3;
            if (total > 0) {
                rate = (failures / total) * 100;
                printf "  %-35s : %6.2f%%\n", $2, rate;
            }
        }
    }'
    
    echo ""
    echo "======================================================================="
    
    # Vérifier si les objectifs sont atteints
    avg_upload=$(tail -n +2 results_30users_stats.csv | grep "upload-selfie" | awk -F',' '{print $5}')
    if [ -n "$avg_upload" ] && [ "$avg_upload" -lt 5000 ]; then
        echo -e "${GREEN}🎉 OBJECTIF ATTEINT : upload-selfie < 5s${NC}"
    else
        echo -e "${YELLOW}⚠️  upload-selfie encore lent ($avg_upload ms)${NC}"
        echo "   Optimisations supplémentaires nécessaires"
    fi
fi

echo ""
echo "🚀 Prochaines étapes :"
echo "  1. Analyser les rapports HTML"
echo "  2. Identifier les endpoints encore lents"
echo "  3. Appliquer des optimisations ciblées"
echo ""
