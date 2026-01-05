#!/bin/bash

# Script rapide pour déployer la version avec diagnostic et voir les logs

set -e

VERSION="v87"
REGION="eu-west-3"
REGISTRY="801541932532.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_NAME="findme-prod"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

echo "=========================================="
echo "🚀 Déploiement Rapide Version de Diagnostic"
echo "=========================================="
echo ""

# 1. Build
echo "[1/4] Build de l'image..."
docker build -t ${IMAGE_NAME}:${VERSION} . || exit 1
echo "✅ Build réussi"
echo ""

# 2. Login ECR
echo "[2/4] Login AWS ECR..."
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${REGISTRY} || exit 1
echo "✅ Login ECR réussi"
echo ""

# 3. Tag & Push
echo "[3/4] Tag et push vers ECR..."
docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE}
docker push ${FULL_IMAGE} || exit 1
echo "✅ Push réussi"
echo ""

# 4. Update service
echo "[4/4] Mise à jour du service AWS..."
echo "⚠️  N'oubliez pas de mettre à jour update-image.json avec ${VERSION}"
echo ""
echo "Commandes pour mettre à jour :"
echo "  1. Éditer update-image.json ligne 6 avec : ${FULL_IMAGE}"
echo "  2. aws apprunner update-service --cli-input-json file://update-image.json --region ${REGION}"
echo ""
echo "Ou utilisez la console AWS App Runner : Deploy → Manual deployment"
echo ""

echo "=========================================="
echo "✅ Image prête et pushée"
echo "=========================================="
echo ""
echo "Prochaines étapes :"
echo "  1. Mettre à jour le service AWS (5-10 min)"
echo "  2. Tester : curl https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check"
echo "  3. Tester login et voir le message d'erreur détaillé"
echo ""

