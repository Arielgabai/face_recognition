"""
Migration: ensure a unique index exists on events.event_code.
Safe to run multiple times.

If duplicate event_code values already exist, the script aborts and prints
the offending codes instead of applying a risky change.
"""
from database import engine
from sqlalchemy import text


def add_event_code_unique_index():
    with engine.connect() as conn:
        duplicates = conn.execute(text("""
            SELECT event_code, COUNT(*) AS duplicate_count
            FROM events
            WHERE event_code IS NOT NULL
            GROUP BY event_code
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, event_code
            LIMIT 20
        """)).fetchall()

        if duplicates:
            print("[Migration] Duplicate event_code values detected, aborting unique index creation")
            for row in duplicates:
                print(f"  - event_code={row.event_code!r} count={row.duplicate_count}")
            raise SystemExit(1)

        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_events_event_code ON events (event_code)"
            ))
            conn.commit()
            print("[Migration] Unique index ix_events_event_code ensured on events.event_code")
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if "already exists" in err or "duplicate" in err:
                print("[Migration] Unique index ix_events_event_code already exists, skipping")
            else:
                raise


if __name__ == "__main__":
    add_event_code_unique_index()
