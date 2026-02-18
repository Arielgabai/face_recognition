"""
Migration: Add selfie_status, selfie_error, selfie_content_type columns to users table.
Safe to run multiple times (uses IF NOT EXISTS pattern).
"""
from database import engine
from sqlalchemy import text


def add_selfie_status_columns():
    columns = [
        ("selfie_status", "VARCHAR"),
        ("selfie_error", "VARCHAR"),
        ("selfie_content_type", "VARCHAR"),
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

        # Backfill: set selfie_status for existing users who have selfie data
        try:
            conn.execute(text("""
                UPDATE users SET selfie_status = 'valid'
                WHERE (selfie_data IS NOT NULL OR selfie_path IS NOT NULL)
                  AND selfie_status IS NULL
            """))
            conn.commit()
            print("[Migration] Backfilled selfie_status='valid' for existing users with selfie data")
        except Exception as e:
            conn.rollback()
            print(f"[Migration] Warning during backfill: {e}")


if __name__ == "__main__":
    add_selfie_status_columns()
