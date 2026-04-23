"""
Migration: add social auth columns and index to users table.
Safe to run multiple times.
"""
from database import engine
from sqlalchemy import text


def add_social_auth_columns():
    columns = [
        ("auth_provider", "VARCHAR"),
        ("auth_provider_subject", "VARCHAR"),
        ("auth_provider_email", "VARCHAR"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[Migration] Column users.{col_name} added")
            except Exception as e:
                conn.rollback()
                err = str(e).lower()
                if "duplicate" in err or "already exists" in err or "duplicate column" in err:
                    print(f"[Migration] Column users.{col_name} already exists, skipping")
                else:
                    print(f"[Migration] Warning adding users.{col_name}: {e}")

        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS users_provider_subject_event_unique "
                "ON users (auth_provider, auth_provider_subject, coalesce(event_id, -1)) "
                "WHERE auth_provider IS NOT NULL AND auth_provider_subject IS NOT NULL"
            ))
            conn.commit()
            print("[Migration] Index users_provider_subject_event_unique ensured")
        except Exception as e:
            conn.rollback()
            print(f"[Migration] Warning ensuring users_provider_subject_event_unique: {e}")


if __name__ == "__main__":
    add_social_auth_columns()
