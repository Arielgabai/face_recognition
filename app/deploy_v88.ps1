# Script PowerShell pour déployer v88 sur AWS
# Usage: .\deploy_v88.ps1

$VERSION = "v88"
$REGION = "eu-west-3"
$REGISTRY = "801541932532.dkr.ecr.$REGION.amazonaws.com"
$IMAGE_NAME = "findme-prod"
$FULL_IMAGE = "$REGISTRY/${IMAGE_NAME}:$VERSION"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 DÉPLOIEMENT $VERSION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Docker
Write-Host "[1/5] Vérification Docker..." -ForegroundColor Yellow
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker non installé ou non accessible" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker disponible" -ForegroundColor Green
Write-Host ""

# Build
Write-Host "[2/5] Build de l'image (cela peut prendre 2-5 minutes)..." -ForegroundColor Yellow
docker build -t "${IMAGE_NAME}:$VERSION" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du build" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build réussi" -ForegroundColor Green
Write-Host ""

# Tag
Write-Host "[3/5] Tag de l'image..." -ForegroundColor Yellow
docker tag "${IMAGE_NAME}:$VERSION" $FULL_IMAGE
Write-Host "✅ Image taggée: $FULL_IMAGE" -ForegroundColor Green
Write-Host ""

# Login ECR
Write-Host "[4/5] Login AWS ECR..." -ForegroundColor Yellow
$LoginCommand = "aws ecr get-login-password --region $REGION"
$Password = Invoke-Expression $LoginCommand
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur login ECR (vérifier AWS credentials)" -ForegroundColor Red
    exit 1
}
$Password | docker login --username AWS --password-stdin $REGISTRY | Out-Null
Write-Host "✅ Login ECR réussi" -ForegroundColor Green
Write-Host ""

# Push
Write-Host "[5/5] Push vers ECR (cela peut prendre 2-5 minutes)..." -ForegroundColor Yellow
docker push $FULL_IMAGE
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du push" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Push réussi" -ForegroundColor Green
Write-Host ""

# Update service
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ IMAGE PRÊTE ET PUSHÉE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prochaine étape : Mettre à jour le service AWS" -ForegroundColor Yellow
Write-Host ""
Write-Host "Commande :" -ForegroundColor White
Write-Host "  cd ..\.." -ForegroundColor Gray
Write-Host "  aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region $REGION" -ForegroundColor Gray
Write-Host ""
Write-Host "Ou via console AWS :" -ForegroundColor White
Write-Host "  https://console.aws.amazon.com/apprunner/" -ForegroundColor Gray
Write-Host "  → findme-prod-v7 → Operations → Deploy → Manual deployment" -ForegroundColor Gray
Write-Host ""
Write-Host "⏱️  Attendre 5-10 minutes après le déploiement" -ForegroundColor Yellow
Write-Host ""
Write-Host "Tests après déploiement :" -ForegroundColor White
Write-Host "  1. Health check: https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check" -ForegroundColor Gray
Write-Host "  2. Login admin/photographe/user → Devrait fonctionner ✓" -ForegroundColor Gray
Write-Host ""

