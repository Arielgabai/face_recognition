"""
Script pour ajouter la colonne is_indexed si elle n'existe pas.
Ce script s'exécute au démarrage de l'application.
"""
from sqlalchemy import text
from database import engine
import logging

logger = logging.getLogger(__name__)


def add_photo_indexed_column():
    """Ajoute la colonne is_indexed à la table photos si elle n'existe pas déjà."""
    try:
        with engine.connect() as conn:
            # Vérifier si la colonne existe déjà
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='photos' AND column_name='is_indexed'
            """))
            
            if result.fetchone():
                logger.info("✓ Column is_indexed already exists")
                return True
            
            # Ajouter la colonne avec valeur par défaut
            logger.info("Adding is_indexed column to photos table...")
            conn.execute(text("""
                ALTER TABLE photos 
                ADD COLUMN is_indexed BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            
            logger.info("✓ Column is_indexed added successfully!")
            return True
            
    except Exception as e:
        logger.warning(f"Could not add is_indexed column (may already exist or DB unavailable): {e}")
        return False
