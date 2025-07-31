#!/usr/bin/env python3
"""
Script de test pour vérifier les nouveaux endpoints de selfies et photos
"""

import requests
import json
from io import BytesIO
from PIL import Image

# Configuration
BASE_URL = "http://localhost:8000"  # Ajuster selon votre configuration

def test_selfie_endpoints():
    """Test des endpoints de selfies"""
    print("🧪 Test des endpoints de selfies...")
    
    # Test 1: Endpoint /api/selfie/{user_id}
    print("  📸 Test de /api/selfie/{user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/selfie/1")
        if response.status_code == 200:
            print("    ✅ Endpoint /api/selfie/{user_id} fonctionne")
            print(f"    📊 Taille de la réponse: {len(response.content)} bytes")
            print(f"    📋 Content-Type: {response.headers.get('content-type')}")
        else:
            print(f"    ❌ Erreur {response.status_code}: {response.text}")
    except Exception as e:
        print(f"    ❌ Erreur de connexion: {e}")

def test_photo_endpoints():
    """Test des endpoints de photos"""
    print("🧪 Test des endpoints de photos...")
    
    # Test 1: Endpoint /api/photo/{photo_id}
    print("  📷 Test de /api/photo/{photo_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/photo/1")
        if response.status_code == 200:
            print("    ✅ Endpoint /api/photo/{photo_id} fonctionne")
            print(f"    📊 Taille de la réponse: {len(response.content)} bytes")
            print(f"    📋 Content-Type: {response.headers.get('content-type')}")
        else:
            print(f"    ❌ Erreur {response.status_code}: {response.text}")
    except Exception as e:
        print(f"    ❌ Erreur de connexion: {e}")

def test_my_selfie_endpoint():
    """Test de l'endpoint /api/my-selfie"""
    print("🧪 Test de l'endpoint /api/my-selfie...")
    
    # Note: Cet endpoint nécessite une authentification
    print("  📸 Test de /api/my-selfie (nécessite authentification)...")
    try:
        response = requests.get(f"{BASE_URL}/api/my-selfie")
        if response.status_code == 401:
            print("    ✅ Endpoint protégé correctement (401 Unauthorized)")
        else:
            print(f"    ⚠️  Status inattendu {response.status_code}: {response.text}")
    except Exception as e:
        print(f"    ❌ Erreur de connexion: {e}")

def test_my_photos_endpoint():
    """Test de l'endpoint /api/my-photos"""
    print("🧪 Test de l'endpoint /api/my-photos...")
    
    # Note: Cet endpoint nécessite une authentification
    print("  📷 Test de /api/my-photos (nécessite authentification)...")
    try:
        response = requests.get(f"{BASE_URL}/api/my-photos")
        if response.status_code == 401:
            print("    ✅ Endpoint protégé correctement (401 Unauthorized)")
        else:
            print(f"    ⚠️  Status inattendu {response.status_code}: {response.text}")
    except Exception as e:
        print(f"    ❌ Erreur de connexion: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests des nouveaux endpoints...")
    print("=" * 50)
    
    test_selfie_endpoints()
    print()
    test_photo_endpoints()
    print()
    test_my_selfie_endpoint()
    print()
    test_my_photos_endpoint()
    print()
    
    print("✅ Tests terminés !")
    print("\n📝 Notes:")
    print("- Les endpoints /api/selfie/{user_id} et /api/photo/{photo_id} sont publics")
    print("- Les endpoints /api/my-selfie et /api/my-photos nécessitent une authentification")
    print("- Pour tester complètement, connectez-vous via l'interface web")

if __name__ == "__main__":
    main() 