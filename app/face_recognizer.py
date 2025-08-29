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
import io
from PIL import Image
from photo_optimizer import PhotoOptimizer
from datetime import datetime, timedelta, timezone

class FaceRecognizer:
    def __init__(self, tolerance=0.7):
        self.tolerance = tolerance
        self.user_encodings = {}  # Cache des encodages des utilisateurs

    def load_user_encoding(self, user: User) -> Optional[np.ndarray]:
        """Charge l'encodage facial d'un utilisateur depuis son selfie"""
        if not user.selfie_data:
            return None
        
        try:
            # Convertir les données binaires en image
            image_data = io.BytesIO(user.selfie_data)
            image = face_recognition.load_image_file(image_data)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                return encodings[0]
        except Exception as e:
            print(f"Erreur lors du chargement de l'encodage pour {user.username}: {e}")
        return None

    def detect_faces(self, image_data: bytes) -> List[Tuple[int, int, int, int]]:
        """Détecte les visages dans une image et retourne leurs positions"""
        try:
            # Convertir les données binaires en image (PIL) et réduire pour limiter la RAM
            image_bytes = io.BytesIO(image_data)
            pil_img = Image.open(image_bytes)
            from PIL import ImageOps as _ImageOps
            pil_img = _ImageOps.exif_transpose(pil_img)
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")

            # Downscale agressif pour éviter l'OOM sur Render free (max 1280px)
            max_dim = 1280
            w, h = pil_img.size
            scale = min(1.0, max_dim / float(max(w, h)))
            if scale < 1.0:
                pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

            # Convertir en numpy array pour face_recognition
            np_img = np.array(pil_img)

            # Détecter les visages (modèle HOG, plus léger que CNN). Si aucun visage,
            # tenter un second passage avec upsample=1 (plus sensible) mais encore léger.
            face_locations = face_recognition.face_locations(np_img, model="hog", number_of_times_to_upsample=0)
            if not face_locations:
                face_locations = face_recognition.face_locations(np_img, model="hog", number_of_times_to_upsample=1)

            # Fallback OpenCV Haar cascade si rien détecté (environnement contraint)
            if not face_locations:
                try:
                    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
                    # Convertir (x, y, w, h) -> (top, right, bottom, left)
                    face_locations = [(int(y), int(x+w), int(y+h), int(x)) for (x, y, w, h) in rects]
                except Exception as _e:
                    pass
            
            return face_locations
            
        except Exception as e:
            print(f"Erreur lors de la détection de visages: {e}")
            return []

    def get_all_user_encodings(self, db: Session) -> Dict[int, np.ndarray]:
        """Récupère tous les encodages des utilisateurs qui ont un selfie"""
        encodings = {}
        users = db.query(User).filter(User.selfie_data.isnot(None)).all()
        
        for user in users:
            encoding = self.load_user_encoding(user)
            if encoding is not None:
                encodings[user.id] = encoding
        
        return encodings

    def process_photo(self, photo_data: bytes, db: Session) -> List[Dict]:
        """Traite une photo et retourne les correspondances trouvées.

        Accepte soit des données binaires d'image, soit un chemin de fichier (str).
        """
        if not photo_data:
            return []

        try:
            # Supporter le passage d'un chemin de fichier
            if isinstance(photo_data, (str, bytes)) and not isinstance(photo_data, (bytearray,)):
                if isinstance(photo_data, str) and os.path.exists(photo_data):
                    image = face_recognition.load_image_file(photo_data)
                else:
                    image_data = io.BytesIO(photo_data if isinstance(photo_data, (bytes, bytearray)) else bytes(photo_data))
                    image = face_recognition.load_image_file(image_data)
            else:
                image_data = io.BytesIO(photo_data)
                image = face_recognition.load_image_file(image_data)
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
            print(f"Erreur lors du traitement de la photo: {e}")
            return []

    def process_and_save_photo(self, photo_path: str, original_filename: str, 
                             photographer_id: Optional[int], db: Session) -> Photo:
        """Traite une photo, sauvegarde les correspondances et retourne l'objet Photo"""
        
        # Lire le fichier et le convertir en données binaires
        with open(photo_path, 'rb') as f:
            original_data = f.read()
        
        # Optimiser l'image avant sauvegarde
        optimization_result = PhotoOptimizer.optimize_image(
            image_data=original_data,
            photo_type='uploaded'
        )
        
        # Générer un nom de fichier unique (toujours JPG après optimisation)
        unique_filename = f"{uuid.uuid4()}.jpg"
        
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
        
        # Créer l'enregistrement Photo avec les données optimisées
        photo = Photo(
            filename=unique_filename,
            original_filename=original_filename,
            photo_data=optimization_result['compressed_data'],
            content_type=optimization_result['content_type'],
            photo_type="uploaded",
            photographer_id=photographer_id,
            event_id=event_id,
            original_size=optimization_result['original_size'],
            compressed_size=optimization_result['compressed_size'],
            compression_ratio=optimization_result['compression_ratio'],
            quality_level=optimization_result['quality_level'],
            retention_days=optimization_result['retention_days'],
            expires_at=optimization_result['expires_at']
        )
        print(f"📸 Photo créée: {original_filename} -> Event ID: {event_id}")
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        # Traiter la reconnaissance faciale avec les données optimisées
        matches = self.process_photo(optimization_result['compressed_data'], db)
        
        # Sauvegarder les correspondances
        for match in matches:
            face_match = FaceMatch(
                photo_id=photo.id,
                user_id=match['user_id'],
                confidence_score=match['confidence_score']
            )
            db.add(face_match)
        
        # NOUVEAU: Si associée à un événement, réinitialiser la date d'expiration 
        # de TOUTES les photos de cet événement pour qu'elles expirent en même temps
        if event_id:
            new_expiration = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Mettre à jour toutes les photos de l'événement
            db.query(Photo).filter(
                Photo.event_id == event_id,
                Photo.expires_at.isnot(None)
            ).update({
                Photo.expires_at: new_expiration
            }, synchronize_session=False)
            print(f"🔄 Toutes les photos de l'événement {event_id} ont été réinitialisées à expirer le {new_expiration}")
        
        # Un seul commit final
        db.commit()
        return photo

    def process_and_save_photo_for_event(self, photo_path: str, original_filename: str, 
                                       photographer_id: int, event_id: int, db: Session) -> Photo:
        """Traite une photo pour un événement spécifique, sauvegarde les correspondances et retourne l'objet Photo"""
        
        # Lire le fichier et le convertir en données binaires
        with open(photo_path, 'rb') as f:
            original_data = f.read()
        
        # Optimiser l'image avant sauvegarde
        optimization_result = PhotoOptimizer.optimize_image(
            image_data=original_data,
            photo_type='uploaded'
        )
        
        # Générer un nom de fichier unique (toujours JPG après optimisation)
        unique_filename = f"{uuid.uuid4()}.jpg"
        
        # Créer l'enregistrement Photo avec les données optimisées
        photo = Photo(
            filename=unique_filename,
            original_filename=original_filename,
            photo_data=optimization_result['compressed_data'],
            content_type=optimization_result['content_type'],
            photo_type="uploaded",
            photographer_id=photographer_id,
            event_id=event_id,
            original_size=optimization_result['original_size'],
            compressed_size=optimization_result['compressed_size'],
            compression_ratio=optimization_result['compression_ratio'],
            quality_level=optimization_result['quality_level'],
            retention_days=optimization_result['retention_days'],
            expires_at=optimization_result['expires_at']
        )
        print(f"📸 Photo créée pour événement {event_id}: {original_filename}")
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        # Traiter la reconnaissance faciale pour cet événement spécifique avec les données optimisées
        matches = self.process_photo_for_event(optimization_result['compressed_data'], event_id, db)
        
        # Sauvegarder les correspondances
        for match in matches:
            face_match = FaceMatch(
                photo_id=photo.id,
                user_id=match['user_id'],
                confidence_score=match['confidence_score']
            )
            db.add(face_match)
        
        # NOUVEAU: Réinitialiser la date d'expiration de TOUTES les photos de cet événement
        # pour qu'elles expirent toutes en même temps (1 mois à partir de maintenant)
        new_expiration = datetime.utcnow() + timedelta(days=30)
        
        # Mettre à jour toutes les photos de l'événement
        db.query(Photo).filter(
            Photo.event_id == event_id,
            Photo.expires_at.isnot(None)
        ).update({
            Photo.expires_at: new_expiration
        }, synchronize_session=False)
        
        # Un seul commit final pour toutes les opérations
        db.commit()
        print(f"🔄 Toutes les photos de l'événement {event_id} ont été réinitialisées à expirer le {new_expiration}")
        return photo

    def process_photo_for_event(self, photo_data: bytes, event_id: int, db: Session) -> List[Dict]:
        """Traite une photo et retourne les correspondances trouvées pour un événement spécifique.

        Accepte soit des données binaires d'image, soit un chemin de fichier (str).
        """
        if not photo_data:
            return []

        try:
            # Supporter le passage d'un chemin de fichier
            if isinstance(photo_data, str) and os.path.exists(photo_data):
                image = face_recognition.load_image_file(photo_data)
            else:
                image_data = io.BytesIO(photo_data if isinstance(photo_data, (bytes, bytearray)) else bytes(photo_data))
                image = face_recognition.load_image_file(image_data)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return []

            # Récupérer les utilisateurs inscrits à cet événement qui ont un selfie
            from models import UserEvent
            user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
            user_ids = [ue.user_id for ue in user_events]
            
            users_with_selfies = db.query(User).filter(
                User.id.in_(user_ids),
                User.selfie_data.isnot(None)
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
            print(f"Erreur lors du traitement de la photo: {e}")
            return []

    def _get_content_type(self, filename: str) -> str:
        """Détermine le type MIME d'un fichier basé sur son extension"""
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
        Après ajout ou modification d'un selfie, parcourt toutes les photos de l'événement de l'utilisateur,
        compare le visage du selfie à chaque visage détecté sur chaque photo,
        et ajoute les correspondances dans FaceMatch si un match est trouvé.
        """
        # Charger l'encodage du nouveau selfie
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
            if not photo.photo_data:
                continue
            try:
                image_data = io.BytesIO(photo.photo_data)
                image = face_recognition.load_image_file(image_data)
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
                print(f"Erreur lors du matching selfie sur photo {photo.id}: {e}")
        db.commit()
        return match_count

    def match_user_selfie_with_photos_event(self, user: User, event_id: int, db: Session):
        """
        Après ajout ou modification d'un selfie, parcourt toutes les photos d'un événement,
        compare le visage du selfie à chaque visage détecté sur chaque photo,
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
            if not photo.photo_data:
                continue
            try:
                image_data = io.BytesIO(photo.photo_data)
                image = face_recognition.load_image_file(image_data)
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
                print(f"Erreur lors du matching selfie sur photo {photo.id}: {e}")
        db.commit()
        return match_count
