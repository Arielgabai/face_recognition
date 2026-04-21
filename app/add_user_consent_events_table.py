"""
Migration pour créer la table user_consent_events.

Cette table stocke une preuve minimale des consentements juridiques et
biométriques donnés par les utilisateurs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from database import engine


def run_migration():
    """Crée la table user_consent_events si elle n'existe pas."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "user_consent_events" in existing_tables:
        print("[Migration][consents] Table already exists, skipping creation")
        return True

    print("[Migration][consents] Creating user_consent_events table...")

    create_sql = """
    CREATE TABLE user_consent_events (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        consent_type VARCHAR NOT NULL,
        accepted BOOLEAN NOT NULL DEFAULT TRUE,
        legal_version VARCHAR NOT NULL,
        ip_address VARCHAR,
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """

    create_sql_sqlite = """
    CREATE TABLE user_consent_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        consent_type VARCHAR NOT NULL,
        accepted BOOLEAN NOT NULL DEFAULT 1,
        legal_version VARCHAR NOT NULL,
        ip_address VARCHAR,
        user_agent TEXT,
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
            print("[Migration][consents] ✓ Table created")

            indexes = [
                ("idx_user_consent_user_id", "user_id"),
                ("idx_user_consent_type", "consent_type"),
                ("idx_user_consent_created", "created_at"),
                ("idx_user_consent_user_type_created", "user_id, consent_type, created_at"),
            ]

            for idx_name, columns in indexes:
                try:
                    conn.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} "
                            f"ON user_consent_events ({columns})"
                        )
                    )
                    conn.commit()
                    print(f"[Migration][consents] ✓ Index {idx_name} created")
                except Exception as e:
                    print(f"[Migration][consents] ⚠ Index {idx_name} failed (may already exist): {e}")

            return True
        except Exception as e:
            print(f"[Migration][consents] ✗ Failed: {e}")
            conn.rollback()
            return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
