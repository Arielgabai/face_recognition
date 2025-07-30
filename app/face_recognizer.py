# Importer le patch en premier pour corriger face_recognition_models
import face_recognition_patch

import face_recognition
import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from models import User, Photo, FaceMatch
import uuid

class FaceRecognizer:
    def __init__(self, tolerance=0.7):
        self.tolerance = tolerance
        self.user_encodings = {}  # Cache des encodages des utilisateurs

    def load_user_encoding(self, user: User) -> Optional[np.ndarray]:
        """Charge l'encodage facial d'un utilisateur depuis sa selfie"""
        if not user.selfie_path or not os.path.exists(user.selfie_path):
            return None
        
        try:
            image = face_recognition.load_image_file(user.selfie_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                return encodings[0]
        except Exception as e:
            print(f"Erreur lors du chargement de l'encodage pour {user.username}: {e}")
        return None

    def get_all_user_encodings(self, db: Session) -> Dict[int, np.ndarray]:
        """Récupère tous les encodages des utilisateurs qui ont une selfie"""
        encodings = {}
        users = db.query(User).filter(User.selfie_path.isnot(None)).all()
        
        for user in users:
            encoding = self.load_user_encoding(user)
            if encoding is not None:
                encodings[user.id] = encoding
        
        return encodings

    def process_photo(self, photo_path: str, db: Session) -> List[Dict]:
        """Traite une photo et retourne les correspondances trouvées"""
        if not os.path.exists(photo_path):
            return []

        try:
            # Charger l'image
            image = face_recognition.load_image_file(photo_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return []

            # Récupérer tous les encodages des utilisateurs
            user_encodings = self.get_all_user_encodings(db)
            
            matches = []
            
            for face_encoding in face_encodings:
                # Comparer avec tous les utilisateurs
                for user_id, user_encoding in user_encodings.items():
                    # Calculer la distance
                    distance = face_recognition.face_distance([user_encoding], face_encoding)[0]
                    
                    # Convertir la distance en score de confiance (0-100)
                    confidence_score = max(0, int((1 - distance) * 100))
                    
                    # Vérifier si c'est une correspondance
                    if distance <= self.tolerance:
                        matches.append({
                            'user_id': user_id,
                            'confidence_score': confidence_score,
                            'distance': distance
                        })
            
            return matches
            
        except Exception as e:
            print(f"Erreur lors du traitement de {photo_path}: {e}")
            return []

    def process_and_save_photo(self, photo_path: str, original_filename: str, 
                             photographer_id: Optional[int], db: Session) -> Photo:
        """Traite une photo, sauvegarde les correspondances et retourne l'objet Photo"""
        
        # Générer un nom de fichier unique
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Créer le dossier de destination
        upload_dir = "static/uploads/photos"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Copier le fichier
        new_path = os.path.join(upload_dir, unique_filename)
        import shutil
        shutil.copy2(photo_path, new_path)
        
        # Trouver l'événement associé au photographe
        event_id = None
        if photographer_id:
            from models import Event
            event = db.query(Event).filter(Event.photographer_id == photographer_id).first()
            if event:
                event_id = event.id
                print(f"✅ Événement trouvé pour photographe {photographer_id}: {event.name} (ID: {event_id})")
            else:
                print(f"⚠️  Aucun événement trouvé pour photographe {photographer_id}")
        else:
            print("⚠️  Aucun photographe_id fourni")
        
        # Créer l'enregistrement Photo
        photo = Photo(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=new_path,
            photo_type="uploaded",
            photographer_id=photographer_id,
            event_id=event_id
        )
        print(f"📸 Photo créée: {original_filename} -> Event ID: {event_id}")
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        # Traiter la reconnaissance faciale
        matches = self.process_photo(new_path, db)
        
        # Sauvegarder les correspondances
        for match in matches:
            face_match = FaceMatch(
                photo_id=photo.id,
                user_id=match['user_id'],
                confidence_score=match['confidence_score']
            )
            db.add(face_match)
        
        db.commit()
        return photo

    def process_and_save_photo_for_event(self, photo_path: str, original_filename: str, 
                                       photographer_id: int, event_id: int, db: Session) -> Photo:
        """Traite une photo pour un événement spécifique, sauvegarde les correspondances et retourne l'objet Photo"""
        
        # Générer un nom de fichier unique
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Créer le dossier de destination
        upload_dir = "static/uploads/photos"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Copier le fichier
        new_path = os.path.join(upload_dir, unique_filename)
        import shutil
        shutil.copy2(photo_path, new_path)
        
        # Créer l'enregistrement Photo avec l'event_id spécifique
        photo = Photo(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=new_path,
            photo_type="uploaded",
            photographer_id=photographer_id,
            event_id=event_id
        )
        print(f"📸 Photo créée pour événement {event_id}: {original_filename}")
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        # Traiter la reconnaissance faciale pour cet événement spécifique
        matches = self.process_photo_for_event(new_path, event_id, db)
        
        # Sauvegarder les correspondances
        for match in matches:
            face_match = FaceMatch(
                photo_id=photo.id,
                user_id=match['user_id'],
                confidence_score=match['confidence_score']
            )
            db.add(face_match)
        
        db.commit()
        return photo

    def process_photo_for_event(self, photo_path: str, event_id: int, db: Session) -> List[Dict]:
        """Traite une photo et retourne les correspondances trouvées pour un événement spécifique"""
        if not os.path.exists(photo_path):
            return []

        try:
            # Charger l'image
            image = face_recognition.load_image_file(photo_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return []

            # Récupérer les utilisateurs inscrits à cet événement qui ont une selfie
            from models import UserEvent
            user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
            user_ids = [ue.user_id for ue in user_events]
            
            users_with_selfies = db.query(User).filter(
                User.id.in_(user_ids),
                User.selfie_path.isnot(None)
            ).all()
            
            # Charger les encodages des utilisateurs de cet événement
            user_encodings = {}
            for user in users_with_selfies:
                encoding = self.load_user_encoding(user)
                if encoding is not None:
                    user_encodings[user.id] = encoding
            
            matches = []
            
            for face_encoding in face_encodings:
                # Comparer avec tous les utilisateurs de l'événement
                for user_id, user_encoding in user_encodings.items():
                    # Calculer la distance
                    distance = face_recognition.face_distance([user_encoding], face_encoding)[0]
                    
                    # Convertir la distance en score de confiance (0-100)
                    confidence_score = max(0, int((1 - distance) * 100))
                    
                    # Vérifier si c'est une correspondance
                    if distance <= self.tolerance:
                        matches.append({
                            'user_id': user_id,
                            'confidence_score': confidence_score,
                            'distance': distance
                        })
            
            return matches
            
        except Exception as e:
            print(f"Erreur lors du traitement de {photo_path}: {e}")
            return []

    def get_user_photos_with_face(self, user_id: int, db: Session) -> List[Photo]:
        """Récupère toutes les photos où un utilisateur apparaît"""
        from sqlalchemy import and_
        
        # Récupérer les photos via les correspondances de visages
        photos = db.query(Photo).join(FaceMatch).filter(
            and_(
                FaceMatch.user_id == user_id,
                FaceMatch.photo_id == Photo.id
            )
        ).all()
        
        return photos

    def get_all_photos_for_user(self, user_id: int, db: Session) -> List[Photo]:
        """Récupère toutes les photos disponibles pour un utilisateur"""
        return db.query(Photo).filter(Photo.photo_type == "uploaded").all()

    def match_user_selfie_with_photos(self, user: User, db: Session):
        """
        Après ajout ou modification d'une selfie, parcourt toutes les photos de l'événement de l'utilisateur,
        compare le visage de la selfie à chaque visage détecté sur chaque photo,
        et ajoute les correspondances dans FaceMatch si un match est trouvé.
        """
        # Charger l'encodage de la nouvelle selfie
        user_encoding = self.load_user_encoding(user)
        if user_encoding is None:
            return 0

        # Trouver l'événement de l'utilisateur
        from models import UserEvent
        user_event = db.query(UserEvent).filter(UserEvent.user_id == user.id).first()
        if not user_event:
            return 0

        # Supprimer les anciens FaceMatch pour cet utilisateur sur cet événement
        from models import Photo
        photo_ids = [p.id for p in db.query(Photo).filter(Photo.event_id == user_event.event_id).all()]
        db.query(FaceMatch).filter(FaceMatch.user_id == user.id, FaceMatch.photo_id.in_(photo_ids)).delete(synchronize_session=False)
        db.commit()

        # Parcourir toutes les photos de l'événement
        photos = db.query(Photo).filter(Photo.event_id == user_event.event_id).all()
        match_count = 0
        for photo in photos:
            if not photo.file_path or not os.path.exists(photo.file_path):
                continue
            try:
                image = face_recognition.load_image_file(photo.file_path)
                face_locations = face_recognition.face_locations(image)
                face_encodings = face_recognition.face_encodings(image, face_locations)
                for face_encoding in face_encodings:
                    distance = face_recognition.face_distance([user_encoding], face_encoding)[0]
                    confidence_score = max(0, int((1 - distance) * 100))
                    if distance <= self.tolerance:
                        face_match = FaceMatch(
                            photo_id=photo.id,
                            user_id=user.id,
                            confidence_score=confidence_score
                        )
                        db.add(face_match)
                        match_count += 1
            except Exception as e:
                print(f"Erreur lors du matching selfie sur photo {photo.file_path}: {e}")
        db.commit()
        return match_count

    def match_user_selfie_with_photos_event(self, user: User, event_id: int, db: Session):
        """
        Après ajout ou modification d'une selfie, parcourt toutes les photos d'un événement,
        compare le visage de la selfie à chaque visage détecté sur chaque photo,
        et ajoute les correspondances dans FaceMatch si un match est trouvé.
        """
        user_encoding = self.load_user_encoding(user)
        if user_encoding is None:
            return 0
        # Supprimer les anciens FaceMatch pour cet utilisateur sur cet événement
        from models import Photo
        photo_ids = [p.id for p in db.query(Photo).filter(Photo.event_id == event_id).all()]
        db.query(FaceMatch).filter(FaceMatch.user_id == user.id, FaceMatch.photo_id.in_(photo_ids)).delete(synchronize_session=False)
        db.commit()
        # Parcourir toutes les photos de l'événement
        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        match_count = 0
        for photo in photos:
            if not photo.file_path or not os.path.exists(photo.file_path):
                continue
            try:
                image = face_recognition.load_image_file(photo.file_path)
                face_locations = face_recognition.face_locations(image)
                face_encodings = face_recognition.face_encodings(image, face_locations)
                for face_encoding in face_encodings:
                    distance = face_recognition.face_distance([user_encoding], face_encoding)[0]
                    confidence_score = max(0, int((1 - distance) * 100))
                    if distance <= self.tolerance:
                        face_match = FaceMatch(
                            photo_id=photo.id,
                            user_id=user.id,
                            confidence_score=confidence_score
                        )
                        db.add(face_match)
                        match_count += 1
            except Exception as e:
                print(f"Erreur lors du matching selfie sur photo {photo.file_path}: {e}")
        db.commit()
        return match_count
