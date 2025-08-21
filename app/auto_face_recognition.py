#!/usr/bin/env python3
"""
Script pour automatiser la reconnaissance faciale.
Ce script :
1. Relance la reconnaissance faciale pour toutes les photos d'un événement
2. Met à jour les correspondances quand un selfie est ajouté/modifié
3. Optimise les performances de reconnaissance
"""

import os
import sys
from sqlalchemy.orm import Session
from database import get_db, create_tables
from models import User, Photo, FaceMatch, Event, UserEvent, UserType
from recognizer_factory import get_face_recognizer

def update_face_recognition_for_event(event_id: int):
    """Met à jour la reconnaissance faciale pour un événement spécifique"""
    db = next(get_db())
    face_recognizer = get_face_recognizer()
    print(f"[FaceRecognition CLI] Provider actif: {type(face_recognizer).__name__}")
    
    try:
        # Récupérer l'événement
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print(f"❌ Événement {event_id} non trouvé")
            return
        
        print(f"🔄 Mise à jour de la reconnaissance faciale pour l'événement: {event.name}")
        
        # Récupérer tous les utilisateurs de l'événement avec selfie
        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        user_ids = [ue.user_id for ue in user_events]
        
        users_with_selfies = db.query(User).filter(
            User.id.in_(user_ids),
            User.selfie_path.isnot(None)
        ).all()
        
        print(f"👥 {len(users_with_selfies)} utilisateurs avec selfie trouvés")
        
        # Récupérer toutes les photos de l'événement
        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        print(f"📸 {len(photos)} photos trouvées")
        
        # Supprimer toutes les anciennes correspondances pour cet événement
        photo_ids = [p.id for p in photos]
        deleted_matches = db.query(FaceMatch).filter(
            FaceMatch.photo_id.in_(photo_ids)
        ).delete()
        print(f"🗑️  {deleted_matches} anciennes correspondances supprimées")
        
        # Traiter chaque photo
        total_matches = 0
        for photo in photos:
            # Choisir la source: chemin ou données binaires
            photo_input = None
            if photo.file_path and os.path.exists(photo.file_path):
                photo_input = photo.file_path
            elif getattr(photo, 'photo_data', None):
                photo_input = photo.photo_data
            else:
                print(f"⚠️  Photo {photo.filename} sans fichier ni données, ignorée")
                continue
            
            try:
                # Traiter la photo avec reconnaissance faciale pour cet événement
                matches = face_recognizer.process_photo_for_event(photo_input, event_id, db)
                
                # Sauvegarder les correspondances
                for match in matches:
                    face_match = FaceMatch(
                        photo_id=photo.id,
                        user_id=match['user_id'],
                        confidence_score=match['confidence_score']
                    )
                    db.add(face_match)
                    total_matches += 1
                
                print(f"✅ Photo {photo.filename}: {len(matches)} correspondances trouvées")
                
            except Exception as e:
                print(f"❌ Erreur lors du traitement de {photo.filename}: {e}")
        
        db.commit()
        print(f"✅ Reconnaissance faciale terminée: {total_matches} correspondances créées")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la mise à jour: {e}")

def update_face_recognition_for_user(user_id: int):
    """Met à jour la reconnaissance faciale pour un utilisateur spécifique"""
    db = next(get_db())
    face_recognizer = get_face_recognizer()
    
    try:
        # Récupérer l'utilisateur
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ Utilisateur {user_id} non trouvé")
            return
        
        if not user.selfie_path:
            print(f"⚠️  Utilisateur {user.username} n'a pas de selfie")
            return
        
        print(f"🔄 Mise à jour de la reconnaissance faciale pour l'utilisateur: {user.username}")
        
        # Récupérer tous les événements de l'utilisateur
        user_events = db.query(UserEvent).filter(UserEvent.user_id == user_id).all()
        
        total_matches = 0
        for user_event in user_events:
            event = db.query(Event).filter(Event.id == user_event.event_id).first()
            if event:
                print(f"📸 Traitement de l'événement: {event.name}")
                
                # Supprimer les anciennes correspondances pour cet utilisateur dans cet événement
                photo_ids = [p.id for p in db.query(Photo).filter(Photo.event_id == event.id).all()]
                deleted_matches = db.query(FaceMatch).filter(
                    FaceMatch.user_id == user_id,
                    FaceMatch.photo_id.in_(photo_ids)
                ).delete()
                
                # Relancer la reconnaissance pour cet événement
                matches = face_recognizer.match_user_selfie_with_photos_event(user, event.id, db)
                total_matches += matches
                
                print(f"✅ Événement {event.name}: {matches} correspondances trouvées")
        
        print(f"✅ Reconnaissance faciale terminée: {total_matches} correspondances totales")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la mise à jour: {e}")

def optimize_face_recognition():
    """Optimise les performances de reconnaissance faciale"""
    db = next(get_db())
    face_recognizer = get_face_recognizer()
    
    try:
        print("🚀 Optimisation de la reconnaissance faciale...")
        
        # Précharger tous les encodages des utilisateurs
        user_encodings = face_recognizer.get_all_user_encodings(db)
        print(f"📊 {len(user_encodings)} encodages d'utilisateurs préchargés")
        
        # Vérifier les photos sans correspondances
        photos_without_matches = db.query(Photo).outerjoin(FaceMatch).filter(
            FaceMatch.id.is_(None)
        ).all()
        
        print(f"🔍 {len(photos_without_matches)} photos sans correspondances trouvées")
        
        # Traiter les photos sans correspondances
        for photo in photos_without_matches:
            if photo.event_id:
                # Choisir la source: chemin ou données binaires
                photo_input = None
                if photo.file_path and os.path.exists(photo.file_path):
                    photo_input = photo.file_path
                elif getattr(photo, 'photo_data', None):
                    photo_input = photo.photo_data
                else:
                    print(f"⚠️  Photo {photo.filename} sans fichier ni données, ignorée")
                    continue
                try:
                    matches = face_recognizer.process_photo_for_event(photo_input, photo.event_id, db)
                    for match in matches:
                        face_match = FaceMatch(
                            photo_id=photo.id,
                            user_id=match['user_id'],
                            confidence_score=match['confidence_score']
                        )
                        db.add(face_match)
                    print(f"✅ Photo {photo.filename}: {len(matches)} correspondances ajoutées")
                except Exception as e:
                    print(f"❌ Erreur pour {photo.filename}: {e}")
        
        db.commit()
        print("✅ Optimisation terminée")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'optimisation: {e}")

def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python auto_face_recognition.py event <event_id>")
        print("  python auto_face_recognition.py user <user_id>")
        print("  python auto_face_recognition.py optimize")
        return
    
    command = sys.argv[1]
    
    # Créer les tables si nécessaire
    create_tables()
    
    if command == "event" and len(sys.argv) >= 3:
        event_id = int(sys.argv[2])
        update_face_recognition_for_event(event_id)
    elif command == "user" and len(sys.argv) >= 3:
        user_id = int(sys.argv[2])
        update_face_recognition_for_user(user_id)
    elif command == "optimize":
        optimize_face_recognition()
    else:
        print("❌ Commande invalide")

if __name__ == "__main__":
    main() 