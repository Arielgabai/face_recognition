#!/usr/bin/env python3
"""
Script de migration pour convertir les photos du système de fichiers vers la base de données
"""

import os
import sys
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Photo, User
import io

def migrate_photos_to_database():
    """Migre toutes les photos du système de fichiers vers la base de données"""
    db = next(get_db())
    
    try:
        # Récupérer toutes les photos qui ont un file_path mais pas de photo_data
        photos = db.query(Photo).filter(
            Photo.file_path.isnot(None),
            Photo.photo_data.is_(None)
        ).all()
        
        print(f"📸 Migration de {len(photos)} photos vers la base de données...")
        
        migrated_count = 0
        for photo in photos:
            try:
                if photo.file_path and os.path.exists(photo.file_path):
                    # Lire le fichier
                    with open(photo.file_path, 'rb') as f:
                        photo_data = f.read()
                    
                    # Déterminer le type de contenu
                    content_type = get_content_type(photo.original_filename or photo.filename)
                    
                    # Mettre à jour la photo
                    photo.photo_data = photo_data
                    photo.content_type = content_type
                    
                    migrated_count += 1
                    print(f"✅ Migré: {photo.original_filename}")
                else:
                    print(f"⚠️  Fichier non trouvé: {photo.file_path}")
            except Exception as e:
                print(f"❌ Erreur lors de la migration de {photo.original_filename}: {e}")
        
        # Sauvegarder les changements
        db.commit()
        print(f"🎉 Migration terminée: {migrated_count} photos migrées")
        
        # Migrer aussi les selfies des utilisateurs
        migrate_selfies_to_database(db)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la migration: {e}")
    finally:
        db.close()

def migrate_selfies_to_database(db: Session):
    """Migre les selfies des utilisateurs vers la base de données"""
    try:
        # Récupérer tous les utilisateurs qui ont un selfie_path mais pas de selfie_data
        users = db.query(User).filter(
            User.selfie_path.isnot(None),
            User.selfie_data.is_(None)
        ).all()
        
        print(f"👤 Migration de {len(users)} selfies vers la base de données...")
        
        migrated_count = 0
        for user in users:
            try:
                if user.selfie_path and os.path.exists(user.selfie_path):
                    # Lire le fichier
                    with open(user.selfie_path, 'rb') as f:
                        selfie_data = f.read()
                    
                    # Mettre à jour l'utilisateur
                    user.selfie_data = selfie_data
                    
                    migrated_count += 1
                    print(f"✅ Selfie migré pour: {user.username}")
                else:
                    print(f"⚠️  Selfie non trouvé: {user.selfie_path}")
            except Exception as e:
                print(f"❌ Erreur lors de la migration du selfie de {user.username}: {e}")
        
        # Sauvegarder les changements
        db.commit()
        print(f"🎉 Migration des selfies terminée: {migrated_count} selfies migrées")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la migration des selfies: {e}")

def get_content_type(filename: str) -> str:
    """Détermine le type MIME d'un fichier basé sur son extension"""
    if not filename:
        return "image/jpeg"
    
    extension = os.path.splitext(filename)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    return content_types.get(extension, 'image/jpeg')

def cleanup_old_files():
    """Nettoie les anciens fichiers après migration (optionnel)"""
    db = next(get_db())
    
    try:
        # Récupérer toutes les photos qui ont été migrées
        photos = db.query(Photo).filter(
            Photo.photo_data.isnot(None),
            Photo.file_path.isnot(None)
        ).all()
        
        print(f"🧹 Nettoyage de {len(photos)} fichiers...")
        
        cleaned_count = 0
        for photo in photos:
            try:
                if photo.file_path and os.path.exists(photo.file_path):
                    os.remove(photo.file_path)
                    cleaned_count += 1
                    print(f"🗑️  Supprimé: {photo.file_path}")
            except Exception as e:
                print(f"❌ Erreur lors de la suppression de {photo.file_path}: {e}")
        
        print(f"🎉 Nettoyage terminé: {cleaned_count} fichiers supprimés")
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Début de la migration des photos vers la base de données...")
    
    # Migrer les photos
    migrate_photos_to_database()
    
    # Demander si on veut nettoyer les anciens fichiers
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        print("\n🧹 Nettoyage des anciens fichiers...")
        cleanup_old_files()
    
    print("✅ Migration terminée !") 