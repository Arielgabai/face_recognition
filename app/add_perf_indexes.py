"""
Script pour ajouter des index de performance si absents.
Ce script s'exécute au démarrage de l'application.
"""
from sqlalchemy import text
from database import engine
import logging

logger = logging.getLogger(__name__)


def add_perf_indexes() -> bool:
    """Ajoute des index SQL pour accélérer les requêtes critiques."""
    statements = [
        # Users: checks par événement (username/email)
        "CREATE INDEX IF NOT EXISTS idx_users_event_username ON users (event_id, username)",
        "CREATE INDEX IF NOT EXISTS idx_users_event_email ON users (event_id, email)",
        # Photos: filtres fréquents
        "CREATE INDEX IF NOT EXISTS idx_photos_user ON photos (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_photos_event ON photos (event_id)",
    ]

    try:
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
        logger.info("✓ Performance indexes ensured")
        return True
    except Exception as e:
        logger.warning(f"Could not add performance indexes (may already exist or DB unavailable): {e}")
        return False
