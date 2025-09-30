from sqlalchemy.orm import Session
from database import SessionLocal
from models import Photo, Event


def backfill_photographer_id() -> None:
    db: Session = SessionLocal()
    try:
        photos = db.query(Photo).filter(
            Photo.photographer_id.is_(None),
            Photo.event_id.isnot(None)
        ).all()
        updated = 0
        for p in photos:
            ev = db.query(Event).filter(Event.id == p.event_id).first()
            if ev and ev.photographer_id is not None:
                p.photographer_id = int(ev.photographer_id)
                updated += 1
        if updated:
            db.commit()
        print(f"Backfill terminé: {updated} photo(s) mises à jour.")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_photographer_id()


