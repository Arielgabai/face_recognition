#!/usr/bin/env python3
"""
Script de test pour vérifier que les URLs invalides retournent une erreur 404
"""

import requests
import json

# Configuration
BASE_URL = "https://facerecognition-d0r8.onrender.com"  # URL de production

def test_invalid_urls():
    """Test des URLs invalides"""
    print("🧪 Test des URLs invalides...")
    print("=" * 50)
    
    # URLs invalides à tester
    invalid_urls = [
        "/admin/photographer",
        "/invalid-page",
        "/nonexistent",
        "/admin/invalid",
        "/photographer/invalid",
        "/api/invalid-endpoint",
        "/static/invalid-file",
        "/random/path/here"
    ]
    
    # URLs valides pour comparaison
    valid_urls = [
        "/",
        "/admin",
        "/photographer", 
        "/register"
    ]
    
    print("\n📋 Test des URLs valides (doivent retourner 200):")
    for url in valid_urls:
        try:
            response = requests.get(f"{BASE_URL}{url}")
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {url}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url}: Erreur de connexion - {e}")
    
    print("\n📋 Test des URLs invalides (doivent retourner 404):")
    for url in invalid_urls:
        try:
            response = requests.get(f"{BASE_URL}{url}")
            status = "✅" if response.status_code == 404 else "❌"
            print(f"   {status} {url}: {response.status_code}")
            
            # Afficher le détail de l'erreur si c'est une 404
            if response.status_code == 404:
                try:
                    error_detail = response.json()
                    print(f"      Detail: {error_detail.get('detail', 'N/A')}")
                except:
                    print(f"      Detail: {response.text[:100]}...")
            elif response.status_code == 200:
                print(f"      ⚠️  Redirection vers la page principale (non désiré)")
                
        except Exception as e:
            print(f"   ❌ {url}: Erreur de connexion - {e}")

def test_api_endpoints():
    """Test des endpoints API invalides"""
    print("\n🧪 Test des endpoints API invalides...")
    print("=" * 50)
    
    invalid_api_urls = [
        "/api/invalid",
        "/api/admin/invalid",
        "/api/photographer/invalid",
        "/api/user/invalid",
        "/api/nonexistent"
    ]
    
    for url in invalid_api_urls:
        try:
            response = requests.get(f"{BASE_URL}{url}")
            status = "✅" if response.status_code == 404 else "❌"
            print(f"   {status} {url}: {response.status_code}")
            
            if response.status_code == 404:
                try:
                    error_detail = response.json()
                    print(f"      Detail: {error_detail.get('detail', 'N/A')}")
                except:
                    print(f"      Detail: {response.text[:100]}...")
                    
        except Exception as e:
            print(f"   ❌ {url}: Erreur de connexion - {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests des URLs invalides...")
    print("=" * 60)
    
    test_invalid_urls()
    test_api_endpoints()
    
    print("\n✅ Tests terminés !")
    print("\n📝 Résumé:")
    print("- Les URLs valides doivent retourner 200")
    print("- Les URLs invalides doivent retourner 404")
    print("- Les endpoints API invalides doivent retourner 404")
    print("- Plus de redirection automatique vers la page principale")

if __name__ == "__main__":
    main() 