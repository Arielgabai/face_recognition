#!/bin/bash

# ============================================================================
# Script de Déploiement - Multi-Workers Fix
# ============================================================================
# Ce script automatise le déploiement des changements de performance
# ============================================================================

set -e  # Arrêt en cas d'erreur

echo "============================================================================"
echo "🚀 DÉPLOIEMENT DES OPTIMISATIONS MULTI-WORKERS"
echo "============================================================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables
REGION="eu-west-3"
REGISTRY="801541932532.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_NAME="findme-prod"
NEW_VERSION="v8"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${NEW_VERSION}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  - Registry: ${REGISTRY}"
echo "  - Image: ${IMAGE_NAME}"
echo "  - Version: ${NEW_VERSION}"
echo "  - Region: ${REGION}"
echo ""

# Étape 1: Vérification des prérequis
echo -e "${YELLOW}[1/6] Vérification des prérequis...${NC}"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker n'est pas installé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installé${NC}"

# Vérifier AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI n'est pas installé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI installé${NC}"

# Vérifier les credentials AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ Credentials AWS non configurés${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Credentials AWS configurés${NC}"

echo ""

# Étape 2: Login ECR
echo -e "${YELLOW}[2/6] Login AWS ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${REGISTRY}
echo -e "${GREEN}✓ Login ECR réussi${NC}"
echo ""

# Étape 3: Build de l'image Docker
echo -e "${YELLOW}[3/6] Build de l'image Docker...${NC}"
echo "  - Ceci peut prendre 5-10 minutes..."
docker build -t ${IMAGE_NAME}:${NEW_VERSION} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build réussi${NC}"
else
    echo -e "${RED}✗ Erreur lors du build${NC}"
    exit 1
fi
echo ""

# Étape 4: Tag de l'image
echo -e "${YELLOW}[4/6] Tag de l'image...${NC}"
docker tag ${IMAGE_NAME}:${NEW_VERSION} ${FULL_IMAGE_NAME}
echo -e "${GREEN}✓ Image taggée: ${FULL_IMAGE_NAME}${NC}"
echo ""

# Étape 5: Push vers ECR
echo -e "${YELLOW}[5/6] Push vers AWS ECR...${NC}"
echo "  - Ceci peut prendre quelques minutes..."
docker push ${FULL_IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Push réussi${NC}"
else
    echo -e "${RED}✗ Erreur lors du push${NC}"
    exit 1
fi
echo ""

# Étape 6: Mise à jour du service AWS App Runner
echo -e "${YELLOW}[6/6] Mise à jour du service AWS App Runner...${NC}"

# Vérifier que service.json existe
if [ ! -f "../../service.json" ]; then
    echo -e "${RED}✗ Fichier service.json non trouvé${NC}"
    exit 1
fi

# Mettre à jour l'ImageIdentifier dans service.json
echo "  - Mise à jour de service.json avec la nouvelle version..."
sed -i.bak "s|\"ImageIdentifier\": \".*\"|\"ImageIdentifier\": \"${FULL_IMAGE_NAME}\"|" ../../service.json

# Déployer
echo "  - Déploiement sur AWS App Runner..."
aws apprunner update-service \
  --cli-input-json file://../../service.json \
  --region ${REGION}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Service mis à jour avec succès${NC}"
else
    echo -e "${RED}✗ Erreur lors de la mise à jour du service${NC}"
    exit 1
fi
echo ""

# Résumé
echo "============================================================================"
echo -e "${GREEN}✅ DÉPLOIEMENT TERMINÉ${NC}"
echo "============================================================================"
echo ""
echo "Prochaines étapes:"
echo "  1. Attendre 5-10 minutes que le déploiement soit complet"
echo "  2. Vérifier les logs dans AWS CloudWatch"
echo "  3. Rechercher '6 processus gunicorn' dans les logs"
echo "  4. Tester avec 30+ utilisateurs simultanés"
echo ""
echo "Commandes utiles:"
echo "  - Logs: aws apprunner list-operations --service-arn <arn> --region ${REGION}"
echo "  - Status: aws apprunner describe-service --service-arn <arn> --region ${REGION}"
echo ""
echo "Documentation complète: FIX_PERFORMANCE_MULTI_WORKERS.md"
echo ""

