"""
Migration: add nullable photographer profile fields to users.

Safe to run multiple times on PostgreSQL and SQLite.
"""

from database import engine
from sqlalchemy import text


def add_photographer_profile_fields():
    string_columns = [
        ("first_name", "VARCHAR"),
        ("last_name", "VARCHAR"),
        ("phone", "VARCHAR"),
        ("website", "VARCHAR"),
        ("logo_content_type", "VARCHAR"),
    ]

    binary_type = "BLOB" if "sqlite" in str(engine.url).lower() else "BYTEA"
    binary_columns = [("logo_data", binary_type)]

    with engine.connect() as conn:
        for col_name, col_type in string_columns + binary_columns:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[Migration] Column users.{col_name} added")
            except Exception as e:
                conn.rollback()
                err = str(e).lower()
                if (
                    "duplicate" in err
                    or "already exists" in err
                    or "duplicate column" in err
                ):
                    print(f"[Migration] Column users.{col_name} already exists, skipping")
                else:
                    print(f"[Migration] Warning adding users.{col_name}: {e}")


if __name__ == "__main__":
    add_photographer_profile_fields()
