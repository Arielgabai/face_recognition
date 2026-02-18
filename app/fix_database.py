#!/usr/bin/env python3
"""
Script pour vérifier et corriger la structure de la base de données
"""

from sqlalchemy import text, inspect
from database import engine, get_db
from models import Base
import os

def check_and_fix_database():
    """Vérifie et corrige la structure de la base de données"""
    
    print("🔍 Vérification de la structure de la base de données...")
    
    # Créer un inspecteur pour examiner la base de données
    inspector = inspect(engine)
    
    # Vérifier si la table users existe
    if not inspector.has_table('users'):
        print("❌ La table 'users' n'existe pas. Création des tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables créées avec succès")
        return
    
    # Vérifier les colonnes de la table users
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    print(f"📋 Colonnes existantes dans 'users': {users_columns}")
    
    # Vérifier les colonnes manquantes
    missing_columns = []
    
    if 'selfie_data' not in users_columns:
        missing_columns.append('selfie_data')
    
    if 'photo_data' not in [col['name'] for col in inspector.get_columns('photos')]:
        missing_columns.append('photos.photo_data')
    
    if 'content_type' not in [col['name'] for col in inspector.get_columns('photos')]:
        missing_columns.append('photos.content_type')
    
    if missing_columns:
        print(f"⚠️  Colonnes manquantes détectées: {missing_columns}")
        print("🔧 Ajout des colonnes manquantes...")
        
        # Ajouter les colonnes manquantes
        with engine.connect() as conn:
            if 'selfie_data' in missing_columns:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN selfie_data BYTEA"))
                    print("✅ Colonne 'selfie_data' ajoutée à la table 'users'")
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'ajout de 'selfie_data': {e}")
            
            if 'photos.photo_data' in missing_columns:
                try:
                    conn.execute(text("ALTER TABLE photos ADD COLUMN photo_data BYTEA"))
                    print("✅ Colonne 'photo_data' ajoutée à la table 'photos'")
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'ajout de 'photo_data': {e}")
            
            if 'photos.content_type' in missing_columns:
                try:
                    conn.execute(text("ALTER TABLE photos ADD COLUMN content_type VARCHAR(50) DEFAULT 'image/jpeg'"))
                    print("✅ Colonne 'content_type' ajoutée à la table 'photos'")
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'ajout de 'content_type': {e}")
            
            conn.commit()
    else:
        print("✅ Toutes les colonnes nécessaires existent")
    
    # Ensure the photo_faces table exists (DB-driven Rekognition face tracking)
    if not inspector.has_table('photo_faces'):
        print("Creating 'photo_faces' table...")
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS photo_faces (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
                        face_id VARCHAR NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_photo_faces_event ON photo_faces (event_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_photo_faces_photo ON photo_faces (photo_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_photo_faces_face ON photo_faces (face_id)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_photo_faces_photo_face ON photo_faces (photo_id, face_id)"))
                conn.commit()
            print("Table 'photo_faces' created successfully")
        except Exception as e:
            print(f"Error creating 'photo_faces' table (may already exist): {e}")
    else:
        print("Table 'photo_faces' already exists")

    # Vérifier à nouveau après les modifications
    inspector = inspect(engine)
    final_users_columns = [col['name'] for col in inspector.get_columns('users')]
    final_photos_columns = [col['name'] for col in inspector.get_columns('photos')]
    
    print(f"Colonnes finales dans 'users': {final_users_columns}")
    print(f"Colonnes finales dans 'photos': {final_photos_columns}")
    
    print("Verification de la base de donnees terminee!")

if __name__ == "__main__":
    check_and_fix_database() 