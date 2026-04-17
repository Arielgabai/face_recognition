"""
Migration pour créer la table photographer_photo_quota_logs.

Cette table stocke un historique minimal des ajouts manuels de quota photo
effectués par un administrateur sur un photographe.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from database import engine


def run_migration():
    """Crée la table photographer_photo_quota_logs si elle n'existe pas."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "photographer_photo_quota_logs" in existing_tables:
        print("[Migration][quota_logs] Table already exists, skipping creation")
        return True

    print("[Migration][quota_logs] Creating photographer_photo_quota_logs table...")

    create_sql = """
    CREATE TABLE photographer_photo_quota_logs (
        id SERIAL PRIMARY KEY,
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        admin_user_id INTEGER REFERENCES users(id),
        added_amount INTEGER NOT NULL,
        photos_remaining_before INTEGER NOT NULL,
        photos_remaining_after INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """

    create_sql_sqlite = """
    CREATE TABLE photographer_photo_quota_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        photographer_id INTEGER NOT NULL REFERENCES users(id),
        admin_user_id INTEGER REFERENCES users(id),
        added_amount INTEGER NOT NULL,
        photos_remaining_before INTEGER NOT NULL,
        photos_remaining_after INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

    with engine.connect() as conn:
        try:
            db_url = str(engine.url)
            is_sqlite = "sqlite" in db_url.lower()
            sql = create_sql_sqlite if is_sqlite else create_sql
            conn.execute(text(sql))
            conn.commit()
            print("[Migration][quota_logs] ✓ Table created")

            indexes = [
                ("idx_quota_logs_photographer", "photographer_id"),
                ("idx_quota_logs_admin", "admin_user_id"),
                ("idx_quota_logs_created", "created_at"),
            ]

            for idx_name, column in indexes:
                try:
                    conn.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON photographer_photo_quota_logs ({column})"
                        )
                    )
                    conn.commit()
                    print(f"[Migration][quota_logs] ✓ Index {idx_name} created")
                except Exception as e:
                    print(f"[Migration][quota_logs] ⚠ Index {idx_name} failed (may already exist): {e}")

            return True
        except Exception as e:
            print(f"[Migration][quota_logs] ✗ Failed: {e}")
            conn.rollback()
            return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
