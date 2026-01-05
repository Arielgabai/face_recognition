"""
Script de vérification post-migration
Exécute ce script AVANT de déployer pour vérifier que la migration SQL est complète

Usage:
    cd face_recognition/app
    python verify_migration_complete.py
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    print("   Définir avec : set DATABASE_URL=postgresql://...")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def verify():
    print("=" * 70)
    print("🔍 VÉRIFICATION POST-MIGRATION")
    print("=" * 70)
    print()
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Test 1: Connexion
        print("[1/5] Connexion à la base...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connexion OK")
        print()
        
        # Test 2: Colonne event_id
        print("[2/5] Vérification colonne event_id...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'event_id'
            """))
            row = result.fetchone()
            if row:
                print(f"✅ Colonne event_id existe (nullable={row[1]})")
            else:
                print("❌ Colonne event_id MANQUANTE !")
                print("   → Appliquer migration_unique_per_event.sql")
                return False
        print()
        
        # Test 3: Nouvelles contraintes composites
        print("[3/5] Vérification contraintes composites...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('users_email_event_unique', 'users_username_event_unique')
            """))
            constraints = [row[0] for row in result.fetchall()]
            
            if len(constraints) == 2:
                print(f"✅ Contraintes composites présentes : {constraints}")
            else:
                print(f"❌ Contraintes composites manquantes (trouvées: {len(constraints)}/2)")
                print("   → Réappliquer la partie CREATE UNIQUE INDEX de la migration")
                return False
        print()
        
        # Test 4: Anciennes contraintes supprimées
        print("[4/5] Vérification suppression anciennes contraintes...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('ix_users_email', 'ix_users_username')
            """))
            old_constraints = [row[0] for row in result.fetchall()]
            
            if len(old_constraints) == 0:
                print("✅ Anciennes contraintes globales bien supprimées")
            else:
                print(f"❌ Anciennes contraintes encore présentes : {old_constraints}")
                print("   → CRITIQUE: Ces contraintes empêchent la fonctionnalité")
                print("   → Exécuter: DROP INDEX IF EXISTS ix_users_email;")
                print("               DROP INDEX IF EXISTS ix_users_username;")
                return False
        print()
        
        # Test 5: Test d'insertion théorique
        print("[5/5] Test d'unicité par événement (simulation)...")
        with engine.connect() as conn:
            # Vérifier qu'on peut théoriquement avoir le même email pour 2 events
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT email) as unique_emails,
                    COUNT(DISTINCT (email, event_id)) as unique_email_event
                FROM users
                WHERE user_type = 'user'
            """))
            row = result.fetchone()
            print(f"✅ Utilisateurs : {row[0]} total, {row[1]} emails uniques")
            if row[0] > 0:
                if row[2] >= row[1]:
                    print(f"   Avec événements : {row[2]} combinaisons (email, event)")
                    print("   → Fonctionnalité multi-événements utilisable")
        print()
        
        print("=" * 70)
        print("✅ MIGRATION COMPLÈTE ET CORRECTE")
        print("=" * 70)
        print()
        print("La base de données est prête.")
        print("Si le login renvoie toujours 500 :")
        print("  → Le problème vient de l'application (code ou cache)")
        print("  → Redéployer complètement avec la version v87")
        print("  → Vérifier les logs AWS CloudWatch")
        print()
        return True
        
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv("../../.env.local")
    except:
        pass
    
    success = verify()
    sys.exit(0 if success else 1)

