"""
Script pour ajouter la table password_reset_tokens si elle n'existe pas.
Ce script s'exécute au démarrage de l'application.
"""
from sqlalchemy import text
from database import engine
import logging

logger = logging.getLogger(__name__)

def add_password_reset_table():
    """Ajoute la table password_reset_tokens si elle n'existe pas déjà."""
    try:
        with engine.connect() as conn:
            # Vérifier si la table existe déjà
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='password_reset_tokens'
            """))
            
            if result.fetchone():
                logger.info("✓ Table password_reset_tokens already exists")
                return True
            
            # Créer la table
            logger.info("Creating password_reset_tokens table...")
            conn.execute(text("""
                CREATE TABLE password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token VARCHAR UNIQUE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    used_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Créer des index
            conn.execute(text("""
                CREATE INDEX ix_password_reset_tokens_token 
                ON password_reset_tokens(token)
            """))
            conn.execute(text("""
                CREATE INDEX ix_password_reset_tokens_user_id 
                ON password_reset_tokens(user_id)
            """))
            
            conn.commit()
            
            logger.info("✓ Table password_reset_tokens created successfully!")
            return True
            
    except Exception as e:
        logger.warning(f"Could not add password_reset_tokens table (may already exist or DB unavailable): {e}")
        return False

