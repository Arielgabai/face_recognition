# ========================================
# Script de démarrage du Local Watcher
# ========================================
# Ce script surveille les dossiers locaux et uploade automatiquement
# les nouvelles photos vers l'API selon les watchers configurés dans l'admin.

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  LOCAL WATCHER - Démarrage" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Configuration (à adapter selon ton environnement)
$env:API_BASE_URL = "https://facerecognition-d0r8.onrender.com"
$env:MACHINE_LABEL = "ADMIN-PC-P1"

# Authentification admin (utilise USERNAME/PASSWORD)
# ⚠️ Remplace par tes vrais identifiants admin
$env:PHOTOGRAPHER_USERNAME = "admin"
$env:PHOTOGRAPHER_PASSWORD = "ton_mot_de_passe_admin"

# Alternative: Token (si tu préfères utiliser un token)
# $env:PHOTOGRAPHER_TOKEN = "ton_token_ici"

# Options de filtrage (optionnelles, décommenter pour personnaliser)
# $env:MIN_WIDTH = "800"
# $env:MIN_HEIGHT = "600"
# $env:MIN_SHARPNESS = "100.0"
# $env:SIMILARITY_THRESHOLD = "6"
# $env:FACE_SCORE_MIN = "0.45"

# Options de debug (optionnelles)
# $env:WATCHER_DEBUG = "1"
# $env:WATCHER_DEBUG_DIR = "C:\watcher_reports"

# Dossiers de rejet (optionnels - chemins relatifs ou absolus)
# $env:REJECTED_DUPLICATE_DIR = "rejected_duplicate"
# $env:REJECTED_LOW_QUALITY_DIR = "rejected_low_quality"
# $env:REJECTED_LOW_FACE_QUALITY_DIR = "rejected_low_face_quality"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  API: $env:API_BASE_URL" -ForegroundColor Gray
Write-Host "  Machine: $env:MACHINE_LABEL" -ForegroundColor Gray
Write-Host "  User: $env:PHOTOGRAPHER_USERNAME" -ForegroundColor Gray
Write-Host "`n"

Write-Host "Démarrage du watcher..." -ForegroundColor Green
Write-Host "(Appuyez sur Ctrl+C pour arrêter)`n" -ForegroundColor Gray

# Lancer le watcher
python local_watcher.py

# Si le script se termine
Write-Host "`nWatcher arrêté." -ForegroundColor Yellow

