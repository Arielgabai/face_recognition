"""
Script pour ajouter des index de performance si absents.
Ce script s'exécute au démarrage de l'application.

Indexes critiques pour supporter:
- 200+ utilisateurs simultanés
- 1000+ photos par événement
- Pagination cursor-based sans timeout
"""
from sqlalchemy import text
from database import engine
import logging

logger = logging.getLogger(__name__)


def add_perf_indexes() -> bool:
    """Ajoute des index SQL pour accélérer les requêtes critiques."""
    statements = [
        # === USERS ===
        # Checks par événement (username/email)
        "CREATE INDEX IF NOT EXISTS idx_users_event_username ON users (event_id, username)",
        "CREATE INDEX IF NOT EXISTS idx_users_event_email ON users (event_id, email)",
        
        # === PHOTOS ===
        # Filtres fréquents de base
        "CREATE INDEX IF NOT EXISTS idx_photos_user ON photos (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_photos_event ON photos (event_id)",
        
        # === PAGINATION HAUTE PERFORMANCE (NOUVEAU) ===
        # Index composite pour /api/user/events/{event_id}/all-photos avec show_in_general
        # Couvre: WHERE event_id = ? AND show_in_general = TRUE ORDER BY uploaded_at DESC, id DESC
        "CREATE INDEX IF NOT EXISTS idx_photos_event_general_pagination ON photos (event_id, show_in_general, uploaded_at DESC, id DESC)",
        
        # Index pour la pagination cursor-based sans filtre show_in_general
        # Couvre: WHERE event_id = ? ORDER BY uploaded_at DESC, id DESC
        "CREATE INDEX IF NOT EXISTS idx_photos_event_pagination ON photos (event_id, uploaded_at DESC, id DESC)",
        
        # === FACE_MATCHES ===
        # Index pour le calcul has_face_match (photo_id -> user_id)
        # Couvre: WHERE photo_id IN (...) AND user_id = ?
        "CREATE INDEX IF NOT EXISTS idx_face_matches_photo_user ON face_matches (photo_id, user_id)",
        
        # Index inverse pour la recherche par user (user_id -> photo_id)
        # Couvre: WHERE user_id = ? (pour /api/user/events/{event_id}/photos)
        "CREATE INDEX IF NOT EXISTS idx_face_matches_user_photo ON face_matches (user_id, photo_id)",
    ]

    try:
        with engine.connect() as conn:
            created = 0
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    created += 1
                except Exception as e:
                    # Index peut déjà exister, ignorer silencieusement
                    if "already exists" not in str(e).lower():
                        logger.debug(f"Index creation skipped: {e}")
            conn.commit()
        logger.info(f"✓ Performance indexes ensured ({created} statements executed)")
        print(f"[Startup] ✓ Performance indexes ensured ({created} statements)")
        return True
    except Exception as e:
        logger.warning(f"Could not add performance indexes (may already exist or DB unavailable): {e}")
        return False
