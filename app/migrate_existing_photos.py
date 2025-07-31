#!/usr/bin/env python3
"""
Script pour migrer les photos existantes du système de fichiers vers la base de données
"""

import os
from sqlalchemy.orm import Session
from database import get_db
from models import Photo, User
from sqlalchemy import text

def migrate_existing_photos():
    """Migrer les photos existantes vers la base de données"""
    
    print("🔄 Migration des photos existantes vers la base de données...")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # 1. Trouver toutes les photos avec file_path mais sans photo_data
        photos_to_migrate = db.query(Photo).filter(
            Photo.file_path.isnot(None),
            Photo.photo_data.is_(None)
        ).all()
        
        print(f"📷 Photos à migrer: {len(photos_to_migrate)}")
        
        migrated_count = 0
        failed_count = 0
        
        for photo in photos_to_migrate:
            try:
                # Vérifier si le fichier existe
                if os.path.exists(photo.file_path):
                    # Lire le fichier
                    with open(photo.file_path, 'rb') as f:
                        photo_data = f.read()
                    
                    # Mettre à jour la photo dans la base de données
                    photo.photo_data = photo_data
                    photo.content_type = photo.content_type or 'image/jpeg'
                    
                    print(f"   ✅ Migré: {photo.filename} ({len(photo_data)} bytes)")
                    migrated_count += 1
                else:
                    print(f"   ❌ Fichier non trouvé: {photo.file_path}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur lors de la migration de {photo.filename}: {e}")
                failed_count += 1
        
        # Sauvegarder les changements
        db.commit()
        
        print(f"\n📊 Résumé de la migration:")
        print(f"   ✅ Photos migrées avec succès: {migrated_count}")
        print(f"   ❌ Échecs: {failed_count}")
        
        # 2. Vérifier les selfies des utilisateurs
        print(f"\n📸 Migration des selfies utilisateur...")
        
        users_with_selfie_path = db.query(User).filter(
            User.selfie_path.isnot(None),
            User.selfie_data.is_(None)
        ).all()
        
        selfie_migrated = 0
        selfie_failed = 0
        
        for user in users_with_selfie_path:
            try:
                if os.path.exists(user.selfie_path):
                    with open(user.selfie_path, 'rb') as f:
                        selfie_data = f.read()
                    
                    user.selfie_data = selfie_data
                    print(f"   ✅ Selfie migrée: {user.username}")
                    selfie_migrated += 1
                else:
                    print(f"   ❌ Selfie non trouvée: {user.selfie_path}")
                    selfie_failed += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur lors de la migration de la selfie de {user.username}: {e}")
                selfie_failed += 1
        
        # Sauvegarder les changements
        db.commit()
        
        print(f"\n📊 Résumé des selfies:")
        print(f"   ✅ Selfies migrées: {selfie_migrated}")
        print(f"   ❌ Échecs selfies: {selfie_failed}")
        
        # 3. Statistiques finales
        total_photos = db.query(Photo).count()
        photos_with_data = db.query(Photo).filter(Photo.photo_data.isnot(None)).count()
        users_with_selfie = db.query(User).filter(User.selfie_data.isnot(None)).count()
        
        print(f"\n📈 Statistiques finales:")
        print(f"   📷 Photos totales: {total_photos}")
        print(f"   📷 Photos avec données binaires: {photos_with_data}")
        print(f"   👤 Utilisateurs avec selfie: {users_with_selfie}")
        
        print(f"\n✅ Migration terminée!")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        db.rollback()
    finally:
        db.close()

def cleanup_old_files():
    """Nettoyer les anciens fichiers après migration (optionnel)"""
    
    print("\n🧹 Nettoyage des anciens fichiers...")
    print("⚠️  ATTENTION: Cette opération supprime les fichiers originaux!")
    
    response = input("Voulez-vous continuer? (y/N): ")
    if response.lower() != 'y':
        print("❌ Nettoyage annulé")
        return
    
    db = next(get_db())
    
    try:
        # Supprimer les fichiers photos
        photos = db.query(Photo).filter(
            Photo.file_path.isnot(None),
            Photo.photo_data.isnot(None)  # Seulement si migration réussie
        ).all()
        
        deleted_files = 0
        for photo in photos:
            try:
                if os.path.exists(photo.file_path):
                    os.remove(photo.file_path)
                    print(f"   🗑️  Supprimé: {photo.file_path}")
                    deleted_files += 1
            except Exception as e:
                print(f"   ❌ Erreur lors de la suppression de {photo.file_path}: {e}")
        
        # Supprimer les fichiers selfies
        users = db.query(User).filter(
            User.selfie_path.isnot(None),
            User.selfie_data.isnot(None)
        ).all()
        
        for user in users:
            try:
                if os.path.exists(user.selfie_path):
                    os.remove(user.selfie_path)
                    print(f"   🗑️  Supprimé selfie: {user.selfie_path}")
                    deleted_files += 1
            except Exception as e:
                print(f"   ❌ Erreur lors de la suppression de la selfie: {e}")
        
        print(f"\n✅ {deleted_files} fichiers supprimés")
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_existing_photos()
    
    # Optionnel: nettoyer les anciens fichiers
    # cleanup_old_files()  # Décommentez si vous voulez supprimer les anciens fichiers 