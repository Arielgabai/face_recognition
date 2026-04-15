"""
Migration pour créer la table photographer_upload_batches
et ajouter la colonne photos.upload_batch_id.

Usage:
    python add_photographer_upload_batches_table.py

Ce script est idempotent: il peut être exécuté plusieurs fois sans erreur.
"""

import os
import sys

# Ajouter le répertoire courant au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from database import engine


def _create_batches_table() -> bool:
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "photographer_upload_batches" in existing_tables:
        print("[Migration][upload_batches] Table already exists, skipping creation")
        return True

    print("[Migration][upload_batches] Creating photographer_upload_batches table...")

    create_sql_postgres = """
    CREATE TABLE photographer_upload_batches (
        id SERIAL PRIMARY KEY,
        upload_batch_id VARCHAR NOT NULL UNIQUE,
        event_id INTEGER NOT NULL REFERENCES events(id),
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        total_photos INTEGER NOT NULL DEFAULT 0,
        processed_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        status VARCHAR NOT NULL DEFAULT 'PENDING',
        email_sent_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE
    )
    """

    create_sql_sqlite = """
    CREATE TABLE photographer_upload_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_batch_id VARCHAR NOT NULL UNIQUE,
        event_id INTEGER NOT NULL REFERENCES events(id),
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        total_photos INTEGER NOT NULL DEFAULT 0,
        processed_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        status VARCHAR NOT NULL DEFAULT 'PENDING',
        email_sent_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )
    """

    with engine.connect() as conn:
        try:
            is_sqlite = "sqlite" in str(engine.url).lower()
            sql = create_sql_sqlite if is_sqlite else create_sql_postgres
            conn.execute(text(sql))
            conn.commit()
            print("[Migration][upload_batches] ✓ Table created")

            indexes = [
                ("idx_upload_batches_upload_batch_id", "upload_batch_id"),
                ("idx_upload_batches_event", "event_id"),
                ("idx_upload_batches_photographer", "photographer_id"),
                ("idx_upload_batches_status", "status"),
                ("idx_upload_batches_created", "created_at"),
            ]

            for idx_name, column in indexes:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON photographer_upload_batches ({column})"))
                    conn.commit()
                    print(f"[Migration][upload_batches] ✓ Index {idx_name} created")
                except Exception as e:
                    print(f"[Migration][upload_batches] ⚠ Index {idx_name} failed (may already exist): {e}")

            return True
        except Exception as e:
            print(f"[Migration][upload_batches] ✗ Failed: {e}")
            conn.rollback()
            return False


def _add_photo_upload_batch_column() -> bool:
    inspector = inspect(engine)
    existing_columns = [col["name"] for col in inspector.get_columns("photos")]

    if "upload_batch_id" in existing_columns:
        print("[Migration][upload_batches] Column photos.upload_batch_id already exists")
        return True

    print("[Migration][upload_batches] Adding column photos.upload_batch_id...")

    with engine.connect() as conn:
        try:
            dialect = engine.dialect.name

            if dialect == "postgresql":
                sql = "ALTER TABLE photos ADD COLUMN IF NOT EXISTS upload_batch_id VARCHAR"
            else:
                sql = "ALTER TABLE photos ADD COLUMN upload_batch_id VARCHAR"

            conn.execute(text(sql))
            conn.commit()
            print("[Migration][upload_batches] ✓ Column photos.upload_batch_id added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Migration][upload_batches] Column photos.upload_batch_id already exists")
            else:
                print(f"[Migration][upload_batches] ✗ Failed to add photos.upload_batch_id: {e}")
                conn.rollback()
                return False

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_photos_upload_batch_id ON photos (upload_batch_id)"))
            conn.commit()
            print("[Migration][upload_batches] ✓ Index idx_photos_upload_batch_id created")
        except Exception as e:
            print(f"[Migration][upload_batches] ⚠ Index idx_photos_upload_batch_id failed (may already exist): {e}")

    return True


def run_migration():
    ok_table = _create_batches_table()
    ok_column = _add_photo_upload_batch_column()
    success = ok_table and ok_column
    if success:
        print("[Migration][upload_batches] Migration completed successfully")
    else:
        print("[Migration][upload_batches] Migration completed with errors")
    return success


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
