"""
Script de test pour vérifier pourquoi les emails sont bloqués
Teste à la fois la BDD et l'API

Usage:
    python test_email_uniqueness.py
"""

import os
import sys
import requests
from sqlalchemy import create_engine, text

# Configuration
API_URL = "https://g62bncafk2.eu-west-3.awsapprunner.com"
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def test_database_constraints():
    """Test 1: Vérifier les contraintes en base de données"""
    print("=" * 70)
    print("[TEST 1] Contraintes Base de Données")
    print("=" * 70)
    print()
    
    if not DATABASE_URL:
        print("⚠️  DATABASE_URL non défini - test BDD ignoré")
        print("   (Défini avec : set DATABASE_URL=postgresql://...)")
        return None
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Vérifier les anciennes contraintes
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('ix_users_email', 'ix_users_username')
            """))
            old_constraints = [row[0] for row in result.fetchall()]
            
            if old_constraints:
                print(f"❌ PROBLÈME CRITIQUE : Anciennes contraintes présentes : {old_constraints}")
                print()
                print("SOLUTION :")
                print("  DROP INDEX IF EXISTS ix_users_email;")
                print("  DROP INDEX IF EXISTS ix_users_username;")
                print()
                return False
            else:
                print("✅ Anciennes contraintes unique globales supprimées")
            
            # Vérifier les nouvelles contraintes
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('users_email_event_unique', 'users_username_event_unique')
            """))
            new_constraints = [row[0] for row in result.fetchall()]
            
            if len(new_constraints) == 2:
                print(f"✅ Nouvelles contraintes composites présentes : {new_constraints}")
            else:
                print(f"❌ Contraintes composites manquantes (trouvées : {len(new_constraints)}/2)")
                return False
            
            print()
            return True
            
    except Exception as e:
        print(f"❌ Erreur connexion BDD : {e}")
        return None

def test_api_health():
    """Test 2: Vérifier l'état de l'API via health-check"""
    print("=" * 70)
    print("[TEST 2] État de l'API")
    print("=" * 70)
    print()
    
    try:
        url = f"{API_URL}/api/health-check"
        print(f"GET {url}")
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            status = data.get("status")
            print(f"Status API: {status}")
            
            # Vérifier les détails
            db_info = data.get("database", {})
            old_constraints = db_info.get("old_constraints_present", [])
            
            if old_constraints:
                print(f"❌ Anciennes contraintes détectées par l'API : {old_constraints}")
                return False
            else:
                print("✅ API ne détecte pas d'anciennes contraintes")
            
            if status == "healthy":
                print("✅ API en bonne santé")
                return True
            else:
                warnings = [w for w in data.get("warnings", []) if w]
                if warnings:
                    print(f"⚠️  Warnings : {warnings}")
                return False
        else:
            print(f"❌ Health check a échoué : {data}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur appel API : {e}")
        return None

def test_backend_code():
    """Test 3: Vérifier que le backend utilise bien la validation par événement"""
    print()
    print("=" * 70)
    print("[TEST 3] Validation Backend")
    print("=" * 70)
    print()
    
    print("Ce test nécessite de créer un compte de test.")
    print("Le message d'erreur nous dira si le code est à jour.")
    print()
    
    print("Test manuel à faire :")
    print("  1. Essayer de créer un compte avec un email déjà utilisé")
    print("  2. Observer le message d'erreur :")
    print()
    print("     ✅ Si : 'Email déjà utilisé pour cet événement'")
    print("        → Code backend à jour")
    print()
    print("     ❌ Si : 'Email déjà utilisé' (SANS 'pour cet événement')")
    print("        → Code backend PAS à jour, redéployer v88")
    print()
    
    return None

def main():
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     DIAGNOSTIC : Pourquoi l'Email Est-il Bloqué ?             ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # Test 1: BDD
    db_ok = test_database_constraints()
    
    # Test 2: API
    api_ok = test_api_health()
    
    # Test 3: Backend code
    backend_info = test_backend_code()
    
    # Résumé
    print()
    print("=" * 70)
    print("RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 70)
    print()
    
    if db_ok is False:
        print("🔴 PROBLÈME : Anciennes contraintes encore en BDD")
        print()
        print("SOLUTION IMMÉDIATE :")
        print("  Exécuter dans psql :")
        print("    DROP INDEX IF EXISTS ix_users_email;")
        print("    DROP INDEX IF EXISTS ix_users_username;")
        print()
        
    elif api_ok is False:
        print("🟡 PROBLÈME : API détecte des problèmes")
        print()
        print("SOLUTION :")
        print("  1. Vérifier les warnings du health-check")
        print("  2. Appliquer les corrections suggérées")
        print()
        
    elif db_ok and api_ok:
        print("✅ BDD et API en bon état")
        print()
        print("Le problème est probablement dans le code backend.")
        print()
        print("SOLUTION :")
        print("  1. Vérifier que v88 est bien déployé")
        print("  2. Tester le message d'erreur (voir Test 3 ci-dessus)")
        print("  3. Si ancien message → Redéployer v88")
        print()
    else:
        print("⚠️  Impossible de déterminer la cause exacte")
        print()
        print("ACTIONS :")
        print("  1. Vérifier DATABASE_URL pour test BDD")
        print("  2. Vérifier que l'API est accessible")
        print("  3. Exécuter les tests manuels dans CHECK_WHY_EMAIL_BLOCKED.md")
        print()
    
    print("=" * 70)
    print()

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv("../../.env.local")
    except:
        pass
    
    main()

