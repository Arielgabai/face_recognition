#!/bin/bash

# Script de déploiement v88 sur AWS
# Usage: ./deploy_v88.sh

set -e

VERSION="v88"
REGION="eu-west-3"
REGISTRY="801541932532.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_NAME="findme-prod"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

echo "========================================"
echo "🚀 DÉPLOIEMENT ${VERSION}"
echo "========================================"
echo ""

# Vérifier Docker
echo "[1/5] Vérification Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non installé"
    exit 1
fi
echo "✅ Docker disponible"
echo ""

# Build
echo "[2/5] Build de l'image (2-5 minutes)..."
docker build -t ${IMAGE_NAME}:${VERSION} .
echo "✅ Build réussi"
echo ""

# Tag
echo "[3/5] Tag de l'image..."
docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE}
echo "✅ Image taggée: ${FULL_IMAGE}"
echo ""

# Login ECR
echo "[4/5] Login AWS ECR..."
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${REGISTRY}
echo "✅ Login ECR réussi"
echo ""

# Push
echo "[5/5] Push vers ECR (2-5 minutes)..."
docker push ${FULL_IMAGE}
echo "✅ Push réussi"
echo ""

# Résumé
echo "========================================"
echo "✅ IMAGE PRÊTE ET PUSHÉE"
echo "========================================"
echo ""
echo "Prochaine étape : Mettre à jour le service AWS"
echo ""
echo "Commande :"
echo "  cd ../.."
echo "  aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region ${REGION}"
echo ""
echo "Ou via console AWS :"
echo "  https://console.aws.amazon.com/apprunner/"
echo "  → findme-prod-v7 → Operations → Deploy → Manual deployment"
echo ""
echo "⏱️  Attendre 5-10 minutes après le déploiement"
echo ""
echo "Tests après déploiement :"
echo "  1. Health check: https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check"
echo "  2. Login admin/photographe/user → Devrait fonctionner ✓"
echo ""

