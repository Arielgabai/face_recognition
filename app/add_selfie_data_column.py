#!/usr/bin/env python3
"""
Script pour ajouter la colonne selfie_data manquante à la table users
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

def add_selfie_data_column():
    """Ajoute la colonne selfie_data à la table users si elle n'existe pas"""
    db = SessionLocal()
    
    try:
        # Vérifier si la colonne existe déjà
        if DATABASE_URL.startswith("postgresql://"):
            # Pour PostgreSQL
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'selfie_data'
            """))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                print("🔧 Ajout de la colonne selfie_data à la table users...")
                db.execute(text("ALTER TABLE users ADD COLUMN selfie_data BYTEA"))
                db.commit()
                print("✅ Colonne selfie_data ajoutée avec succès")
            else:
                print("ℹ️  La colonne selfie_data existe déjà")
                
        elif DATABASE_URL.startswith("sqlite://"):
            # Pour SQLite
            result = db.execute(text("PRAGMA table_info(users)"))
            columns = result.fetchall()
            column_exists = any(col[1] == 'selfie_data' for col in columns)
            
            if not column_exists:
                print("🔧 Ajout de la colonne selfie_data à la table users...")
                db.execute(text("ALTER TABLE users ADD COLUMN selfie_data BLOB"))
                db.commit()
                print("✅ Colonne selfie_data ajoutée avec succès")
            else:
                print("ℹ️  La colonne selfie_data existe déjà")
        else:
            print("❌ Type de base de données non supporté")
            return
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'ajout de la colonne: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Ajout de la colonne selfie_data manquante...")
    add_selfie_data_column()
    print("✅ Script terminé !") 