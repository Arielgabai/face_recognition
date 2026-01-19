# ========================================
# DÉPLOIEMENT FIX TIMEOUT - AWS ECR + App Runner
# PowerShell Script pour Windows
# ========================================

$ErrorActionPreference = "Stop"

Write-Host "🚀 Déploiement du fix timeout pour /api/register-with-event-code" -ForegroundColor Green
Write-Host ""

# Configuration
$AWS_REGION = "eu-west-3"
$ECR_REGISTRY = "801541932532.dkr.ecr.$AWS_REGION.amazonaws.com"
$ECR_REPO = "findme-prod"
$IMAGE_TAG = "v101"  # Incrémentez si v101 existe déjà
$SERVICE_ARN = "arn:aws:apprunner:eu-west-3:801541932532:service/findme-prod-v7/bc130b363f614b43b4d82dfd9699dff7"

Write-Host "📋 Configuration:" -ForegroundColor Cyan
Write-Host "  - Région AWS: $AWS_REGION"
Write-Host "  - Registre ECR: $ECR_REGISTRY"
Write-Host "  - Repository: $ECR_REPO"
Write-Host "  - Tag: $IMAGE_TAG"
Write-Host ""

try {
    # 1. Login Docker sur AWS ECR
    Write-Host "🔐 Connexion à AWS ECR..." -ForegroundColor Yellow
    $loginPassword = aws ecr get-login-password --region $AWS_REGION
    $loginPassword | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de la connexion à ECR"
    }
    Write-Host "✅ Connecté à ECR" -ForegroundColor Green
    Write-Host ""

    # 2. Build de l'image Docker
    Write-Host "🔨 Build de l'image Docker..." -ForegroundColor Yellow
    docker build -t "${ECR_REPO}:${IMAGE_TAG}" -f Dockerfile .
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du build Docker"
    }
    Write-Host "✅ Image Docker buildée" -ForegroundColor Green
    Write-Host ""

    # 3. Tag de l'image pour ECR
    Write-Host "🏷️  Tag de l'image pour ECR..." -ForegroundColor Yellow
    docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du tag"
    }
    Write-Host "✅ Image taguée" -ForegroundColor Green
    Write-Host ""

    # 4. Push vers ECR
    Write-Host "📤 Push vers ECR..." -ForegroundColor Yellow
    docker push "${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du push vers ECR"
    }
    Write-Host "✅ Image pushée vers ECR" -ForegroundColor Green
    Write-Host ""

    # 5. Mise à jour du fichier update-image.json (déjà fait manuellement)
    Write-Host "📝 Fichier update-image.json déjà mis à jour" -ForegroundColor Green
    Write-Host ""

    # 6. Mise à jour de App Runner
    Write-Host "🔄 Déploiement sur AWS App Runner..." -ForegroundColor Yellow
    aws apprunner update-service --cli-input-json file://update-image.json --region $AWS_REGION
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de la mise à jour App Runner"
    }
    Write-Host "✅ Service App Runner mis à jour" -ForegroundColor Green
    Write-Host ""

    # 7. Vérifier le statut du déploiement
    Write-Host "⏳ Attente du déploiement (peut prendre 5-10 minutes)..." -ForegroundColor Cyan
    Write-Host "Vérifiez le statut dans AWS Console:"
    Write-Host "https://eu-west-3.console.aws.amazon.com/apprunner/home?region=eu-west-3#/services" -ForegroundColor Blue
    Write-Host ""

    Write-Host "🎉 Déploiement lancé avec succès !" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Variables d'environnement à vérifier dans App Runner:" -ForegroundColor Cyan
    Write-Host "  GUNICORN_WORKERS=3"
    Write-Host "  MATCHING_THREAD_POOL_SIZE=10"
    Write-Host "  BCRYPT_ROUNDS=8"
    Write-Host "  DB_POOL_SIZE=10"
    Write-Host "  DB_MAX_OVERFLOW=20"
    Write-Host ""
    Write-Host "🧪 Après déploiement, testez avec:" -ForegroundColor Cyan
    Write-Host "  cd face_recognition/app"
    Write-Host "  locust -f locust_file.py --host=https://votre-app.onrender.com"
    Write-Host ""
    Write-Host "✅ DONE!" -ForegroundColor Green

} catch {
    Write-Host "❌ Erreur: $_" -ForegroundColor Red
    exit 1
}
