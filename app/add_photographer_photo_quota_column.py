"""
Migration: add users.photos_remaining column used to cap how many photos
a photographer can upload. Safe to run multiple times.

Strategy:
1. ALTER TABLE users ADD COLUMN photos_remaining INTEGER DEFAULT 0
   (ignored if the column already exists).
2. Ensure NOT NULL at the ORM level via the model default; in addition we
   backfill any NULL values to 0 so that legacy rows are consistent with
   the model contract.
"""
from database import engine
from sqlalchemy import text


def add_photographer_photo_quota_column():
    with engine.connect() as conn:
        # 1. Ajout de la colonne (idempotent)
        try:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN photos_remaining INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
            print("[Migration] Column users.photos_remaining added (NOT NULL DEFAULT 0)")
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if (
                "duplicate" in err
                or "already exists" in err
                or "duplicate column" in err
            ):
                print(
                    "[Migration] Column users.photos_remaining already exists, skipping"
                )
            else:
                # Certains dialectes refusent NOT NULL lors d'un ALTER (SQLite).
                # On retente sans la contrainte puis on backfillera.
                try:
                    conn.execute(
                        text("ALTER TABLE users ADD COLUMN photos_remaining INTEGER DEFAULT 0")
                    )
                    conn.commit()
                    print(
                        "[Migration] Column users.photos_remaining added (DEFAULT 0, nullable)"
                    )
                except Exception as e2:
                    conn.rollback()
                    err2 = str(e2).lower()
                    if (
                        "duplicate" in err2
                        or "already exists" in err2
                        or "duplicate column" in err2
                    ):
                        print(
                            "[Migration] Column users.photos_remaining already exists, skipping"
                        )
                    else:
                        print(
                            f"[Migration] Warning adding users.photos_remaining: {e2}"
                        )

        # 2. Backfill: s'assurer qu'aucune ligne n'a NULL
        try:
            conn.execute(
                text(
                    "UPDATE users SET photos_remaining = 0 WHERE photos_remaining IS NULL"
                )
            )
            conn.commit()
            print(
                "[Migration] Backfilled users.photos_remaining = 0 for legacy NULL rows"
            )
        except Exception as e:
            conn.rollback()
            print(
                f"[Migration] Warning during users.photos_remaining backfill: {e}"
            )


if __name__ == "__main__":
    add_photographer_photo_quota_column()
