"""
Migration pour créer la table delete_jobs.

Cette table stocke les jobs de suppression de photos asynchrones.

Usage:
    python add_delete_jobs_table.py
    
Ou automatiquement au démarrage de l'app via run_migrations().
"""

import os
import sys

# Ajouter le répertoire courant au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from database import engine, SessionLocal


def run_migration():
    """Crée la table delete_jobs si elle n'existe pas."""
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "delete_jobs" in existing_tables:
        print("[Migration][delete_jobs] Table already exists, skipping creation")
        return True
    
    print("[Migration][delete_jobs] Creating delete_jobs table...")
    
    # SQL compatible PostgreSQL et SQLite
    create_sql = """
    CREATE TABLE delete_jobs (
        id SERIAL PRIMARY KEY,
        job_id VARCHAR NOT NULL UNIQUE,
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        photo_ids_json TEXT NOT NULL,
        total_photos INTEGER NOT NULL DEFAULT 0,
        processed_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        errors_json TEXT,
        status VARCHAR NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        duration_seconds FLOAT
    )
    """
    
    # Version SQLite
    create_sql_sqlite = """
    CREATE TABLE delete_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id VARCHAR NOT NULL UNIQUE,
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        photo_ids_json TEXT NOT NULL,
        total_photos INTEGER NOT NULL DEFAULT 0,
        processed_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        errors_json TEXT,
        status VARCHAR NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        duration_seconds REAL
    )
    """
    
    with engine.connect() as conn:
        try:
            # Déterminer le type de base
            db_url = str(engine.url)
            is_sqlite = "sqlite" in db_url.lower()
            
            sql = create_sql_sqlite if is_sqlite else create_sql
            conn.execute(text(sql))
            conn.commit()
            print("[Migration][delete_jobs] ✓ Table created")
            
            # Créer les index
            indexes = [
                ("idx_delete_jobs_job_id", "job_id"),
                ("idx_delete_jobs_photographer", "photographer_id"),
                ("idx_delete_jobs_status", "status"),
                ("idx_delete_jobs_created", "created_at"),
            ]
            
            for idx_name, column in indexes:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON delete_jobs ({column})"))
                    conn.commit()
                    print(f"[Migration][delete_jobs] ✓ Index {idx_name} created")
                except Exception as e:
                    print(f"[Migration][delete_jobs] ⚠ Index {idx_name} failed (may already exist): {e}")
            
            return True
            
        except Exception as e:
            print(f"[Migration][delete_jobs] ✗ Failed: {e}")
            conn.rollback()
            return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
