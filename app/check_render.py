#!/usr/bin/env python3
"""
Script de vérification pour le déploiement Render
"""

import os
import sys

def check_files():
    """Vérifie que tous les fichiers requis sont présents"""
    required_files = [
        'Dockerfile',
        'requirements.txt',
        'start.sh',
        'main.py',
        'face_recognizer.py',
        'models.py',
        'database.py',
        'auth.py',
        'schemas.py',
        'test_imports.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Fichiers manquants : {missing_files}")
        return False
    else:
        print("✅ Tous les fichiers requis sont présents")
        return True

def check_requirements():
    """Vérifie le fichier requirements.txt"""
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_packages = [
            'numpy==1.24.3',
            'opencv-python-headless==4.8.1.78',
            'face-recognition-models==0.1.3',
            'Pillow==10.0.1',
            'fastapi',
            'uvicorn'
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in content:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Packages manquants dans requirements.txt : {missing_packages}")
            return False
        else:
            print("✅ requirements.txt contient tous les packages requis")
            return True
    except FileNotFoundError:
        print("❌ requirements.txt non trouvé")
        return False

def check_dockerfile():
    """Vérifie le Dockerfile"""
    try:
        with open('Dockerfile', 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_elements = [
            'FROM python:3.11-slim-bookworm',
            'EXPOSE 8000',
            'CMD ["./start.sh"]',
            'Pillow==10.0.1',
            'face-recognition-models==0.1.3'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Éléments manquants dans Dockerfile : {missing_elements}")
            return False
        else:
            print("✅ Dockerfile est correctement configuré")
            return True
    except FileNotFoundError:
        print("❌ Dockerfile non trouvé")
        return False

def check_start_script():
    """Vérifie le script de démarrage"""
    try:
        with open('start.sh', 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_elements = [
            'test_imports.py',
            'uvicorn main:app',
            '${PORT:-8000}'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Éléments manquants dans start.sh : {missing_elements}")
            return False
        else:
            print("✅ start.sh est correctement configuré")
            return True
    except FileNotFoundError:
        print("❌ start.sh non trouvé")
        return False

def main():
    """Vérification complète pour Render"""
    print("🔍 Vérification pour le déploiement Render...\n")
    
    checks = [
        ("Fichiers requis", check_files),
        ("requirements.txt", check_requirements),
        ("Dockerfile", check_dockerfile),
        ("Script de démarrage", check_start_script)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"📋 Vérification : {name}")
        if not check_func():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 Toutes les vérifications sont passées !")
        print("✅ Votre application est prête pour le déploiement sur Render")
        print("\n📝 Prochaines étapes :")
        print("1. Pousser le code vers Git")
        print("2. Connecter le repository à Render")
        print("3. Configurer les variables d'environnement")
        print("4. Déployer !")
    else:
        print("❌ Certaines vérifications ont échoué")
        print("🔧 Veuillez corriger les problèmes avant de déployer")
        sys.exit(1)

if __name__ == "__main__":
    main() 