"""
Script de test pour vérifier la contrainte unique par événement.
À exécuter APRÈS avoir appliqué la migration SQL.

Usage:
    python test_unique_per_event.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def test_database_constraints():
    """Vérifie que les contraintes unique par événement sont bien en place."""
    
    print("=" * 70)
    print("TEST : Contraintes Unique par Événement")
    print("=" * 70)
    print()
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Test 1: Vérifier que la colonne event_id existe
            print("[Test 1] Vérification de la colonne event_id...")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'event_id'
            """))
            row = result.fetchone()
            if row:
                print(f"✅ Colonne event_id existe : {row[1]}, nullable={row[2]}")
            else:
                print("❌ Colonne event_id n'existe PAS")
                print("   → Appliquez d'abord migration_unique_per_event.sql")
                return False
            print()
            
            # Test 2: Vérifier les contraintes unique composites
            print("[Test 2] Vérification des contraintes unique...")
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('users_email_event_unique', 'users_username_event_unique')
            """))
            rows = result.fetchall()
            
            if len(rows) >= 2:
                print(f"✅ {len(rows)} contraintes unique trouvées :")
                for row in rows:
                    print(f"   - {row[0]}")
            else:
                print(f"❌ Contraintes unique manquantes (trouvées: {len(rows)}/2)")
                print("   → Appliquez d'abord migration_unique_per_event.sql")
                return False
            print()
            
            # Test 3: Vérifier qu'il n'y a pas d'anciennes contraintes
            print("[Test 3] Vérification suppression anciennes contraintes...")
            result = conn.execute(text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'users'::regclass 
                AND contype = 'u'
                AND conname IN ('users_email_key', 'users_username_key')
            """))
            old_constraints = result.fetchall()
            
            if len(old_constraints) == 0:
                print("✅ Anciennes contraintes globales bien supprimées")
            else:
                print(f"⚠️  Anciennes contraintes encore présentes : {[c[0] for c in old_constraints]}")
                print("   Cela pourrait causer des conflits")
            print()
            
            # Test 4: Vérifier les données existantes
            print("[Test 4] Vérification des données existantes...")
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN event_id IS NULL THEN 1 END) as users_no_event,
                    COUNT(CASE WHEN event_id IS NOT NULL THEN 1 END) as users_with_event
                FROM users
            """))
            row = result.fetchone()
            print(f"✅ Utilisateurs en base :")
            print(f"   - Total : {row[0]}")
            print(f"   - Sans event_id (photographes/admins) : {row[1]}")
            print(f"   - Avec event_id : {row[2]}")
            print()
            
            # Test 5: Vérifier les doublons potentiels
            print("[Test 5] Vérification des doublons...")
            result = conn.execute(text("""
                SELECT email, event_id, COUNT(*) as count
                FROM users 
                GROUP BY email, event_id 
                HAVING COUNT(*) > 1
            """))
            duplicates = result.fetchall()
            
            if len(duplicates) == 0:
                print("✅ Aucun doublon (email, event_id)")
            else:
                print(f"❌ {len(duplicates)} doublon(s) détecté(s) :")
                for dup in duplicates:
                    print(f"   - {dup[0]}, event_id={dup[1]}, count={dup[2]}")
                print("   → Nettoyer manuellement avant de continuer")
                return False
            print()
            
        print("=" * 70)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 70)
        print()
        print("Prochaines étapes :")
        print("  1. Déployer le nouveau code (models.py + main.py)")
        print("  2. Redémarrer l'application")
        print("  3. Tester l'inscription avec le même email sur 2 événements différents")
        print()
        return True
        
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        print()
        print("Vérifiez :")
        print("  - DATABASE_URL correctement défini")
        print("  - Connexion à la base de données")
        print("  - Migration SQL appliquée")
        return False

if __name__ == "__main__":
    success = test_database_constraints()
    sys.exit(0 if success else 1)

