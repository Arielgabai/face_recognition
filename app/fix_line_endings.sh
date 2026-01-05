#!/bin/bash

# Script pour convertir les fins de ligne de start.sh
# Exécuter depuis Git Bash/WSL : ./fix_line_endings.sh

echo "🔧 Conversion des fins de ligne de start.sh (CRLF → LF)..."

if [ ! -f "start.sh" ]; then
    echo "❌ Fichier start.sh non trouvé dans le répertoire courant"
    echo "   Assurez-vous d'être dans face_recognition/app/"
    exit 1
fi

# Convertir CRLF en LF
sed -i 's/\r$//' start.sh

# Rendre exécutable
chmod +x start.sh

echo "✅ Conversion terminée avec succès!"
echo ""
echo "Prochaines étapes:"
echo "  1. Commit le fichier corrigé : git add start.sh && git commit -m 'Fix line endings'"
echo "  2. Rebuild l'image Docker : docker build -t findme-prod:v8 ."
echo "  3. Déployer vers AWS"

