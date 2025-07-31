#!/usr/bin/env python3
"""
Script de test pour vérifier les endpoints de selfies
"""

import requests
import json
from io import BytesIO
from PIL import Image

# Configuration
BASE_URL = "https://facerecognition-d0r8.onrender.com"  # URL de production

def test_selfie_endpoints():
    """Test des endpoints de selfies"""
    print("🧪 Test des endpoints de selfies...")
    print("=" * 50)
    
    # Test 1: Endpoint /api/selfie/{user_id} (public)
    print("\n📸 Test de /api/selfie/{user_id} (public)...")
    try:
        response = requests.get(f"{BASE_URL}/api/selfie/1")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Endpoint fonctionne - selfie trouvée")
            print(f"   📊 Taille: {len(response.content)} bytes")
            print(f"   📋 Content-Type: {response.headers.get('content-type')}")
        elif response.status_code == 404:
            print("   ⚠️  Selfie non trouvée (utilisateur 1 n'a pas de selfie)")
        else:
            print(f"   ❌ Erreur inattendue: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")

    # Test 2: Endpoint /api/my-selfie (nécessite authentification)
    print("\n📸 Test de /api/my-selfie (nécessite authentification)...")
    try:
        response = requests.get(f"{BASE_URL}/api/my-selfie")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint protégé correctement (401 Unauthorized)")
        elif response.status_code == 404:
            print("   ⚠️  Utilisateur connecté n'a pas de selfie")
        else:
            print(f"   ⚠️  Status inattendu: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")

def test_selfie_upload():
    """Test de l'upload de selfie (nécessite authentification)"""
    print("\n📤 Test de l'upload de selfie...")
    print("   ⚠️  Ce test nécessite une authentification")
    print("   💡 Connectez-vous via l'interface web pour tester l'upload")

def check_database_connection():
    """Vérifier la connexion à la base de données"""
    print("\n🔍 Vérification de la connexion à la base de données...")
    try:
        # Test simple de l'API
        response = requests.get(f"{BASE_URL}/api")
        if response.status_code == 200:
            print("   ✅ API accessible")
        else:
            print(f"   ❌ API non accessible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Test des endpoints de selfies")
    print(f"🌐 URL de test: {BASE_URL}")
    
    check_database_connection()
    test_selfie_endpoints()
    test_selfie_upload()
    
    print("\n📝 Instructions pour résoudre les problèmes de selfies:")
    print("1. Connectez-vous à l'interface utilisateur")
    print("2. Allez dans la section 'Ma Selfie'")
    print("3. Uploadez une photo de votre visage")
    print("4. Vérifiez que la selfie s'affiche correctement")
    print("5. Si vous avez des erreurs, vérifiez les logs Render")

if __name__ == "__main__":
    main() 