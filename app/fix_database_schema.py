#!/usr/bin/env python3
"""
Script pour corriger le schéma de la base de données en ajoutant les colonnes manquantes
"""

import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Si c'est PostgreSQL, ajuster l'URL pour SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_table_columns(table_name: str, db) -> list:
    """Récupère la liste des colonnes d'une table"""
    if DATABASE_URL.startswith("postgresql://"):
        result = db.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """))
        return [row[0] for row in result.fetchall()]
    elif DATABASE_URL.startswith("sqlite://"):
        result = db.execute(text(f"PRAGMA table_info({table_name})"))
        return [row[1] for row in result.fetchall()]
    return []

def add_column_if_missing(table_name: str, column_name: str, column_type: str, db):
    """Ajoute une colonne si elle n'existe pas"""
    existing_columns = get_table_columns(table_name, db)
    
    if column_name not in existing_columns:
        print(f"🔧 Ajout de la colonne {column_name} à la table {table_name}...")
        
        if DATABASE_URL.startswith("postgresql://"):
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        elif DATABASE_URL.startswith("sqlite://"):
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        
        db.commit()
        print(f"✅ Colonne {column_name} ajoutée avec succès")
    else:
        print(f"ℹ️  La colonne {column_name} existe déjà dans {table_name}")

def fix_database_schema():
    """Corrige le schéma de la base de données en ajoutant les colonnes manquantes"""
    db = SessionLocal()
    
    try:
        print("🔧 Vérification et correction du schéma de la base de données...")
        
        # Colonnes manquantes dans la table users
        missing_columns = [
            ("users", "selfie_data", "BYTEA" if DATABASE_URL.startswith("postgresql://") else "BLOB"),
        ]
        
        # Colonnes manquantes dans la table photos
        missing_columns.extend([
            ("photos", "photo_data", "BYTEA" if DATABASE_URL.startswith("postgresql://") else "BLOB"),
            ("photos", "content_type", "VARCHAR(255)" if DATABASE_URL.startswith("postgresql://") else "TEXT"),
        ])
        
        for table_name, column_name, column_type in missing_columns:
            add_column_if_missing(table_name, column_name, column_type, db)
        
        print("✅ Schéma de la base de données corrigé avec succès")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la correction du schéma: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Correction du schéma de la base de données...")
    fix_database_schema()
    print("✅ Script terminé !") 