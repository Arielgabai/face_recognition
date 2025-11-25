"""
Script pour ajouter la colonne show_in_general si elle n'existe pas.
Ce script s'exécute au démarrage de l'application.
"""
from sqlalchemy import text
from database import engine
import logging

logger = logging.getLogger(__name__)

def add_show_in_general_column():
    """Ajoute la colonne show_in_general à la table photos si elle n'existe pas déjà."""
    try:
        with engine.connect() as conn:
            # Vérifier si la colonne existe déjà
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='photos' AND column_name='show_in_general'
            """))
            
            if result.fetchone():
                logger.info("✓ Column show_in_general already exists")
                return True
            
            # Ajouter la colonne
            logger.info("Adding show_in_general column to photos table...")
            conn.execute(text("""
                ALTER TABLE photos 
                ADD COLUMN show_in_general BOOLEAN DEFAULT NULL
            """))
            conn.commit()
            
            logger.info("✓ Column show_in_general added successfully!")
            return True
            
    except Exception as e:
        logger.warning(f"Could not add show_in_general column (may already exist or DB unavailable): {e}")
        return False

