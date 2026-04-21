"""
Migration: add nullable events.email_featured_photo_id.

Safe to run multiple times on PostgreSQL and SQLite.
"""

from database import engine
from sqlalchemy import text


def add_event_email_featured_photo():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN email_featured_photo_id INTEGER"))
            conn.commit()
            print("[Migration] Column events.email_featured_photo_id added")
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err or "duplicate column" in err:
                print("[Migration] Column events.email_featured_photo_id already exists, skipping")
            else:
                print(f"[Migration] Warning adding events.email_featured_photo_id: {e}")


if __name__ == "__main__":
    add_event_email_featured_photo()
