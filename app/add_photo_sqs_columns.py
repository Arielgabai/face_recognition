"""
Script de migration pour ajouter les colonnes S3+SQS au modèle Photo.

Colonnes ajoutées:
    - s3_key: Clé S3 de l'image brute uploadée
    - processing_status: Statut de traitement (PENDING, PROCESSING, DONE, FAILED)
    - error_message: Message d'erreur en cas d'échec
    - updated_at: Timestamp de mise à jour du statut

Usage:
    python add_photo_sqs_columns.py

Ce script est idempotent: il peut être exécuté plusieurs fois sans erreur.
"""

import os
import sys

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from database import engine


def add_photo_sqs_columns():
    """Ajoute les colonnes S3+SQS à la table photos si elles n'existent pas."""
    
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('photos')]
    
    columns_to_add = [
        ("s3_key", "VARCHAR", "NULL"),
        ("processing_status", "VARCHAR", "'PENDING'"),
        ("error_message", "TEXT", "NULL"),
        ("updated_at", "TIMESTAMP", "NULL"),
    ]
    
    with engine.connect() as conn:
        for col_name, col_type, default in columns_to_add:
            if col_name not in existing_columns:
                try:
                    # Déterminer le dialecte SQL
                    dialect = engine.dialect.name
                    
                    if dialect == "sqlite":
                        sql = f"ALTER TABLE photos ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                    elif dialect == "postgresql":
                        if default == "NULL":
                            sql = f"ALTER TABLE photos ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        else:
                            sql = f"ALTER TABLE photos ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default}"
                    else:
                        # MySQL et autres
                        sql = f"ALTER TABLE photos ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                    
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"[Migration] Added column 'photos.{col_name}'")
                    
                except Exception as e:
                    # Ignorer si la colonne existe déjà
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"[Migration] Column 'photos.{col_name}' already exists")
                    else:
                        print(f"[Migration] Error adding column 'photos.{col_name}': {e}")
            else:
                print(f"[Migration] Column 'photos.{col_name}' already exists")
    
    # Créer un index sur processing_status si il n'existe pas
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            
            if dialect == "postgresql":
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_photos_processing_status ON photos (processing_status)"
                ))
            elif dialect == "sqlite":
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_photos_processing_status ON photos (processing_status)"
                ))
            else:
                # MySQL
                conn.execute(text(
                    "CREATE INDEX idx_photos_processing_status ON photos (processing_status)"
                ))
            
            conn.commit()
            print("[Migration] Created index 'idx_photos_processing_status'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("[Migration] Index 'idx_photos_processing_status' already exists")
        else:
            print(f"[Migration] Warning creating index: {e}")
    
    # Créer un index sur s3_key si il n'existe pas
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            
            if dialect == "postgresql":
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_photos_s3_key ON photos (s3_key)"
                ))
            elif dialect == "sqlite":
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_photos_s3_key ON photos (s3_key)"
                ))
            else:
                # MySQL
                conn.execute(text(
                    "CREATE INDEX idx_photos_s3_key ON photos (s3_key)"
                ))
            
            conn.commit()
            print("[Migration] Created index 'idx_photos_s3_key'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("[Migration] Index 'idx_photos_s3_key' already exists")
        else:
            print(f"[Migration] Warning creating index: {e}")
    
    print("[Migration] Photo S3+SQS columns migration completed")


if __name__ == "__main__":
    add_photo_sqs_columns()
