# Script PowerShell pour convertir les fins de ligne de start.sh
# Exécuter depuis PowerShell : .\fix_line_endings.ps1

Write-Host "🔧 Conversion des fins de ligne de start.sh (CRLF → LF)..." -ForegroundColor Yellow

$filePath = "start.sh"

if (-Not (Test-Path $filePath)) {
    Write-Host "❌ Fichier start.sh non trouvé dans le répertoire courant" -ForegroundColor Red
    Write-Host "   Assurez-vous d'être dans face_recognition/app/" -ForegroundColor Red
    exit 1
}

# Lire le contenu et remplacer CRLF par LF
$content = Get-Content $filePath -Raw
$content = $content -replace "`r`n", "`n"

# Sauvegarder sans ajouter de nouvelle ligne à la fin
[System.IO.File]::WriteAllText($filePath, $content, [System.Text.Encoding]::UTF8)

Write-Host "✅ Conversion terminée avec succès!" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines étapes:" -ForegroundColor Cyan
Write-Host "  1. Commit le fichier corrigé : git add start.sh && git commit -m 'Fix line endings'" -ForegroundColor White
Write-Host "  2. Rebuild l'image Docker : docker build -t findme-prod:v8 ." -ForegroundColor White
Write-Host "  3. Déployer vers AWS" -ForegroundColor White

