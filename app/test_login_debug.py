"""
Script de diagnostic pour tester la connexion et identifier le problème 500
Usage: python test_login_debug.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def test_database_and_model():
    print("=" * 70)
    print("DIAGNOSTIC : Login Error 500")
    print("=" * 70)
    print()
    
    # Test 1: Connexion base de données
    print("[Test 1] Connexion à la base de données...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connexion OK : {version[:50]}...")
    except Exception as e:
        print(f"❌ Erreur connexion : {e}")
        return False
    print()
    
    # Test 2: Vérifier la structure de la table users
    print("[Test 2] Structure de la table users...")
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        col_names = [col['name'] for col in columns]
        
        if 'event_id' in col_names:
            print("✅ Colonne event_id présente")
        else:
            print("❌ Colonne event_id MANQUANTE")
            return False
            
        print(f"   Colonnes : {', '.join(col_names)}")
    except Exception as e:
        print(f"❌ Erreur inspection : {e}")
        return False
    print()
    
    # Test 3: Vérifier les contraintes
    print("[Test 3] Contraintes unique...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname LIKE '%unique%'
            """))
            constraints = result.fetchall()
            
            has_composite = False
            has_old_email = False
            has_old_username = False
            
            for name, definition in constraints:
                if 'email_event_unique' in name:
                    has_composite = True
                    print(f"✅ {name}")
                elif 'username_event_unique' in name:
                    print(f"✅ {name}")
                elif 'ix_users_email' in name:
                    has_old_email = True
                    print(f"⚠️  {name} (ANCIENNE CONTRAINTE - À SUPPRIMER)")
                elif 'ix_users_username' in name:
                    has_old_username = True
                    print(f"⚠️  {name} (ANCIENNE CONTRAINTE - À SUPPRIMER)")
            
            if has_old_email or has_old_username:
                print()
                print("❌ PROBLÈME : Anciennes contraintes toujours présentes!")
                print("   Exécutez : DROP INDEX IF EXISTS ix_users_email;")
                print("              DROP INDEX IF EXISTS ix_users_username;")
                return False
                
            if not has_composite:
                print("❌ Contraintes composites manquantes")
                return False
    except Exception as e:
        print(f"❌ Erreur vérification contraintes : {e}")
        return False
    print()
    
    # Test 4: Tester le modèle SQLAlchemy
    print("[Test 4] Test du modèle SQLAlchemy...")
    try:
        from models import User, Base
        from database import engine as app_engine
        
        # Vérifier que le modèle a event_id
        if hasattr(User, 'event_id'):
            print("✅ User.event_id existe dans le modèle Python")
        else:
            print("❌ User.event_id MANQUANT dans le modèle Python")
            return False
            
        # Vérifier les contraintes dans le modèle
        if hasattr(User, '__table_args__'):
            print("✅ Contraintes composites définies dans le modèle")
        else:
            print("⚠️  Pas de __table_args__ (peut être OK si migrations Alembic)")
    except Exception as e:
        print(f"❌ Erreur chargement modèle : {e}")
        return False
    print()
    
    # Test 5: Simuler une requête de login
    print("[Test 5] Simulation requête login...")
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Compter les utilisateurs
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.fetchone()[0]
            print(f"✅ {count} utilisateur(s) dans la base")
            
            # Vérifier un photographe
            result = conn.execute(text("""
                SELECT id, username, email, user_type, event_id 
                FROM users 
                WHERE user_type = 'photographer' 
                LIMIT 1
            """))
            photographer = result.fetchone()
            if photographer:
                print(f"✅ Photographe trouvé : {photographer[1]} (event_id={photographer[4]})")
            else:
                print("⚠️  Aucun photographe trouvé")
                
        session.close()
    except Exception as e:
        print(f"❌ Erreur requête : {e}")
        return False
    print()
    
    print("=" * 70)
    print("✅ TOUS LES TESTS PASSÉS")
    print("=" * 70)
    print()
    print("Si le login renvoie toujours une erreur 500 :")
    print("  1. Vérifier les logs AWS CloudWatch")
    print("  2. Chercher 'login' ou 'error' dans les logs")
    print("  3. L'erreur exacte vous dira ce qui bloque")
    print()
    print("Commandes utiles :")
    print("  - Logs AWS: aws logs tail /aws/apprunner/findme-prod-v7 --follow")
    print("  - Restart: aws apprunner update-service --service-arn ...")
    print()
    return True

if __name__ == "__main__":
    success = test_database_and_model()
    sys.exit(0 if success else 1)

