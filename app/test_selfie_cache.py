#!/usr/bin/env python3
"""
Script de test pour vérifier le cache-busting des selfies
"""

import requests
import time

# Configuration
BASE_URL = "https://facerecognition-d0r8.onrender.com"

def test_selfie_cache_busting():
    """Test du cache-busting des selfies"""
    print("🧪 Test du cache-busting des selfies...")
    print("=" * 50)
    
    # Test 1: Vérifier que l'endpoint selfie fonctionne
    print("\n📸 Test de l'endpoint /api/selfie/{user_id}...")
    try:
        # Test sans paramètre de cache
        response1 = requests.get(f"{BASE_URL}/api/selfie/1")
        print(f"   Status sans cache-busting: {response1.status_code}")
        
        # Test avec paramètre de cache
        timestamp = int(time.time())
        response2 = requests.get(f"{BASE_URL}/api/selfie/1?t={timestamp}")
        print(f"   Status avec cache-busting: {response2.status_code}")
        
        if response1.status_code == response2.status_code:
            print("   ✅ Les deux requêtes retournent le même status")
        else:
            print("   ⚠️  Différence de status entre les requêtes")
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

def test_selfie_headers():
    """Test des headers de cache pour les selfies"""
    print("\n📋 Test des headers de cache...")
    try:
        timestamp = int(time.time())
        response = requests.get(f"{BASE_URL}/api/selfie/1?t={timestamp}")
        
        if response.status_code == 200:
            cache_control = response.headers.get('Cache-Control', 'Non défini')
            print(f"   Cache-Control: {cache_control}")
            
            if 'max-age' in cache_control:
                print("   ✅ Headers de cache configurés")
            else:
                print("   ⚠️  Headers de cache non configurés")
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

def test_multiple_requests():
    """Test de plusieurs requêtes avec cache-busting"""
    print("\n🔄 Test de plusieurs requêtes...")
    try:
        for i in range(3):
            timestamp = int(time.time())
            response = requests.get(f"{BASE_URL}/api/selfie/1?t={timestamp}")
            print(f"   Requête {i+1}: Status {response.status_code}")
            time.sleep(1)  # Attendre 1 seconde entre les requêtes
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Test du cache-busting des selfies")
    print(f"🌐 URL de test: {BASE_URL}")
    
    test_selfie_cache_busting()
    test_selfie_headers()
    test_multiple_requests()
    
    print("\n📝 Instructions pour tester manuellement:")
    print("1. Connectez-vous à l'interface utilisateur")
    print("2. Uploadez un nouveau selfie")
    print("3. Vérifiez que l'aperçu se met à jour immédiatement")
    print("4. Si l'aperçu ne se met pas à jour, rechargez la page")

if __name__ == "__main__":
    main() 