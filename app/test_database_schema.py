#!/usr/bin/env python3
"""
Script de test pour vérifier que le schéma de la base de données est correct
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Si c'est PostgreSQL, ajuster l'URL pour SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_database_schema():
    """Teste que le schéma de la base de données est correct"""
    db = SessionLocal()
    
    try:
        print("🔍 Test du schéma de la base de données...")
        
        # Vérifier que la table users existe
        if DATABASE_URL.startswith("postgresql://"):
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'users'
            """))
            table_exists = result.fetchone() is not None
        elif DATABASE_URL.startswith("sqlite://"):
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            table_exists = result.fetchone() is not None
        else:
            print("❌ Type de base de données non supporté")
            return False
        
        if not table_exists:
            print("❌ La table 'users' n'existe pas")
            return False
        
        print("✅ La table 'users' existe")
        
        # Vérifier les colonnes requises
        required_columns = [
            'id', 'username', 'email', 'hashed_password', 
            'user_type', 'selfie_path', 'selfie_data', 
            'is_active', 'created_at'
        ]
        
        if DATABASE_URL.startswith("postgresql://"):
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """))
            existing_columns = [row[0] for row in result.fetchall()]
        elif DATABASE_URL.startswith("sqlite://"):
            result = db.execute(text("PRAGMA table_info(users)"))
            existing_columns = [row[1] for row in result.fetchall()]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"❌ Colonnes manquantes: {missing_columns}")
            return False
        
        print("✅ Toutes les colonnes requises existent")
        
        # Test de requête simple
        try:
            result = db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.fetchone()[0]
            print(f"✅ Test de requête réussi - {count} utilisateurs dans la base")
        except Exception as e:
            print(f"❌ Erreur lors du test de requête: {e}")
            return False
        
        print("🎉 Tous les tests du schéma sont passés avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du schéma: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_database_schema()
    if success:
        print("✅ Le schéma de la base de données est correct")
        exit(0)
    else:
        print("❌ Le schéma de la base de données a des problèmes")
        exit(1) 