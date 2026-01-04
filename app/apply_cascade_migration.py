"""
Script de migration pour ajouter ON DELETE CASCADE à la contrainte password_reset_tokens -> users

Usage:
    python apply_cascade_migration.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

def apply_migration():
    """Applique la migration pour ajouter CASCADE à la foreign key"""
    engine = create_engine(DATABASE_URL)
    
    print("🔧 Application de la migration pour password_reset_tokens...")
    
    try:
        with engine.connect() as conn:
            # Étape 1: Supprimer l'ancienne contrainte
            print("   ↳ Suppression de l'ancienne contrainte...")
            conn.execute(text("""
                ALTER TABLE password_reset_tokens 
                DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey
            """))
            conn.commit()
            
            # Étape 2: Recréer avec CASCADE
            print("   ↳ Recréation avec ON DELETE CASCADE...")
            conn.execute(text("""
                ALTER TABLE password_reset_tokens 
                ADD CONSTRAINT password_reset_tokens_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES users(id) 
                ON DELETE CASCADE
            """))
            conn.commit()
            
            # Vérification
            print("   ↳ Vérification de la contrainte...")
            result = conn.execute(text("""
                SELECT 
                    tc.constraint_name,
                    rc.delete_rule
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.referential_constraints rc 
                    ON tc.constraint_name = rc.constraint_name
                WHERE tc.table_name = 'password_reset_tokens'
                    AND tc.constraint_type = 'FOREIGN KEY'
            """))
            
            for row in result:
                constraint_name, delete_rule = row
                print(f"   ✓ Contrainte: {constraint_name}, Règle de suppression: {delete_rule}")
            
            print("\n✅ Migration appliquée avec succès!")
            print("   Les tokens de réinitialisation seront maintenant supprimés automatiquement")
            print("   lors de la suppression d'un utilisateur.\n")
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        print("   Vérifiez que la base de données est accessible et que vous avez les permissions nécessaires.\n")
        raise

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  MIGRATION: Ajout de CASCADE pour password_reset_tokens")
    print("="*70 + "\n")
    
    apply_migration()

