#!/usr/bin/env python3
"""
Script de nettoyage pour corriger les problèmes de gestion des photos et événements.
Ce script :
1. Nettoie les photos orphelines (sans événement associé)
2. Corrige les associations utilisateur-événement
3. Vérifie l'intégrité des données
"""

import os
import sys
from sqlalchemy.orm import Session
from database import get_db, create_tables
from models import User, Photo, FaceMatch, Event, UserEvent, UserType

def cleanup_orphaned_photos():
    """Nettoie les photos qui n'ont pas d'événement associé"""
    db = next(get_db())
    try:
        # Trouver les photos sans événement
        orphaned_photos = db.query(Photo).filter(Photo.event_id.is_(None)).all()
        
        print(f"🔍 Trouvé {len(orphaned_photos)} photos orphelines")
        
        for photo in orphaned_photos:
            # Essayer de trouver l'événement du photographe
            if photo.photographer_id:
                event = db.query(Event).filter(Event.photographer_id == photo.photographer_id).first()
                if event:
                    photo.event_id = event.id
                    print(f"✅ Photo {photo.filename} associée à l'événement {event.name}")
                else:
                    # Supprimer la photo si aucun événement trouvé
                    print(f"🗑️  Suppression de la photo orpheline {photo.filename}")
                    # Supprimer les correspondances de visages
                    db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
                    # Supprimer le fichier physique
                    if photo.file_path and os.path.exists(photo.file_path):
                        os.remove(photo.file_path)
                    # Supprimer l'enregistrement
                    db.delete(photo)
        
        db.commit()
        print("✅ Nettoyage des photos orphelines terminé")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du nettoyage: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

def fix_user_event_associations():
    """Corrige les associations utilisateur-événement"""
    db = next(get_db())
    try:
        # Trouver les utilisateurs sans événement
        users_without_events = db.query(User).filter(
            User.user_type == UserType.USER
        ).all()
        
        print(f"🔍 Vérification de {len(users_without_events)} utilisateurs")
        
        for user in users_without_events:
            # Vérifier si l'utilisateur a déjà une association
            existing_association = db.query(UserEvent).filter(UserEvent.user_id == user.id).first()
            
            if not existing_association:
                # Trouver un événement par défaut (le premier disponible)
                default_event = db.query(Event).first()
                if default_event:
                    user_event = UserEvent(user_id=user.id, event_id=default_event.id)
                    db.add(user_event)
                    print(f"✅ Utilisateur {user.username} associé à l'événement {default_event.name}")
        
        db.commit()
        print("✅ Associations utilisateur-événement corrigées")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la correction des associations: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

def verify_data_integrity():
    """Vérifie l'intégrité des données"""
    db = next(get_db())
    try:
        # Vérifier les photos sans fichier physique
        photos_without_file = []
        photos = db.query(Photo).all()
        
        for photo in photos:
            if photo.file_path and not os.path.exists(photo.file_path):
                photos_without_file.append(photo)
        
        if photos_without_file:
            print(f"⚠️  {len(photos_without_file)} photos sans fichier physique:")
            for photo in photos_without_file:
                print(f"   - {photo.filename} (chemin: {photo.file_path})")
        else:
            print("✅ Toutes les photos ont leur fichier physique")
        
        # Vérifier les correspondances de visages orphelines
        orphaned_face_matches = db.query(FaceMatch).filter(
            ~FaceMatch.photo_id.in_(db.query(Photo.id))
        ).all()
        
        if orphaned_face_matches:
            print(f"⚠️  {len(orphaned_face_matches)} correspondances de visages orphelines")
            # Supprimer les correspondances orphelines
            db.query(FaceMatch).filter(
                ~FaceMatch.photo_id.in_(db.query(Photo.id))
            ).delete()
            db.commit()
            print("✅ Correspondances orphelines supprimées")
        else:
            print("✅ Aucune correspondance de visage orpheline")
        
        # Vérifier les utilisateurs sans selfie
        users_without_selfie = db.query(User).filter(
            User.user_type == UserType.USER,
            User.selfie_path.is_(None)
        ).all()
        
        print(f"ℹ️  {len(users_without_selfie)} utilisateurs sans selfie")
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

def main():
    """Fonction principale"""
    print("🧹 Début du nettoyage de la base de données...")
    
    # Créer les tables si nécessaire
    create_tables()
    
    # Nettoyer les photos orphelines
    cleanup_orphaned_photos()
    
    # Corriger les associations utilisateur-événement
    fix_user_event_associations()
    
    # Vérifier l'intégrité des données
    verify_data_integrity()
    
    print("✅ Nettoyage terminé avec succès!")

if __name__ == "__main__":
    main() 