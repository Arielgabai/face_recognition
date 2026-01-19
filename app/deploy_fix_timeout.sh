#!/bin/bash
# ========================================
# DÉPLOIEMENT FIX TIMEOUT - AWS ECR + App Runner
# ========================================

set -e  # Arrêter en cas d'erreur

echo "🚀 Déploiement du fix timeout pour /api/register-with-event-code"
echo ""

# Configuration
AWS_REGION="eu-west-3"
ECR_REGISTRY="801541932532.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO="findme-prod"
IMAGE_TAG="v101"  # Incrémentez si v101 existe déjà
SERVICE_ARN="arn:aws:apprunner:eu-west-3:801541932532:service/findme-prod-v7/bc130b363f614b43b4d82dfd9699dff7"

echo "📋 Configuration:"
echo "  - Région AWS: ${AWS_REGION}"
echo "  - Registre ECR: ${ECR_REGISTRY}"
echo "  - Repository: ${ECR_REPO}"
echo "  - Tag: ${IMAGE_TAG}"
echo ""

# 1. Login Docker sur AWS ECR
echo "🔐 Connexion à AWS ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -ne 0 ]; then
    echo "❌ Échec de la connexion à ECR"
    exit 1
fi
echo "✅ Connecté à ECR"
echo ""

# 2. Build de l'image Docker
echo "🔨 Build de l'image Docker..."
docker build -t ${ECR_REPO}:${IMAGE_TAG} -f Dockerfile .

if [ $? -ne 0 ]; then
    echo "❌ Échec du build Docker"
    exit 1
fi
echo "✅ Image Docker buildée"
echo ""

# 3. Tag de l'image pour ECR
echo "🏷️  Tag de l'image pour ECR..."
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Échec du tag"
    exit 1
fi
echo "✅ Image taguée"
echo ""

# 4. Push vers ECR
echo "📤 Push vers ECR..."
docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Échec du push vers ECR"
    exit 1
fi
echo "✅ Image pushée vers ECR"
echo ""

# 5. Mise à jour du fichier update-image.json
echo "📝 Mise à jour de update-image.json..."
cat > update-image.json <<EOF
{
  "ServiceArn": "${SERVICE_ARN}",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}",
      "ImageRepositoryType": "ECR"
    }
  }
}
EOF
echo "✅ Fichier update-image.json mis à jour"
echo ""

# 6. Mise à jour de App Runner
echo "🔄 Déploiement sur AWS App Runner..."
aws apprunner update-service --cli-input-json file://update-image.json --region ${AWS_REGION}

if [ $? -ne 0 ]; then
    echo "❌ Échec de la mise à jour App Runner"
    exit 1
fi
echo "✅ Service App Runner mis à jour"
echo ""

# 7. Vérifier le statut du déploiement
echo "⏳ Attente du déploiement (peut prendre 5-10 minutes)..."
echo "Vérifiez le statut dans AWS Console:"
echo "https://eu-west-3.console.aws.amazon.com/apprunner/home?region=eu-west-3#/services"
echo ""

echo "🎉 Déploiement lancé avec succès !"
echo ""
echo "📊 Variables d'environnement à vérifier dans App Runner:"
echo "  GUNICORN_WORKERS=3"
echo "  MATCHING_THREAD_POOL_SIZE=10"
echo "  BCRYPT_ROUNDS=8"
echo "  DB_POOL_SIZE=10"
echo "  DB_MAX_OVERFLOW=20"
echo ""
echo "🧪 Après déploiement, testez avec:"
echo "  cd face_recognition/app"
echo "  locust -f locust_file.py --host=https://votre-app.onrender.com"
echo ""
echo "✅ DONE!"
