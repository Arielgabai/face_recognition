import os
from typing import List, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from models import User, Photo, FaceMatch, Event, UserEvent
from photo_optimizer import PhotoOptimizer


AWS_REGION = os.environ.get("AWS_REGION", "eu-west-3")  # Paris
COLL_PREFIX = os.environ.get("AWS_REKOGNITION_COLLECTION_PREFIX", "event_")


class AwsFaceRecognizer:
    """
    Provider basé sur AWS Rekognition Collections.
    - 1 collection par événement: f"{COLL_PREFIX}{event_id}"
    - Chaque utilisateur (selfie) est indexé avec l'ExternalImageId = user_id
    - Matching par SearchFacesByImage
    """

    def __init__(self):
        self.client = boto3.client("rekognition", region_name=AWS_REGION)

    def _collection_id(self, event_id: int) -> str:
        return f"{COLL_PREFIX}{event_id}"

    def ensure_collection(self, event_id: int):
        coll_id = self._collection_id(event_id)
        try:
            self.client.describe_collection(CollectionId=coll_id)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ResourceNotFoundException":
                self.client.create_collection(CollectionId=coll_id)
            else:
                raise

    def index_user_selfie(self, event_id: int, user: User):
        coll_id = self._collection_id(event_id)
        image_bytes = None
        if user.selfie_path and os.path.exists(user.selfie_path):
            with open(user.selfie_path, "rb") as f:
                image_bytes = f.read()
        elif user.selfie_data:
            image_bytes = user.selfie_data
        if not image_bytes:
            return
        try:
            self.client.index_faces(
                CollectionId=coll_id,
                Image={"Bytes": image_bytes},
                ExternalImageId=str(user.id),
                DetectionAttributes=[],
                MaxFaces=1,
                QualityFilter="AUTO",
            )
        except ClientError:
            pass

    def process_photo_for_event(self, photo_input, event_id: int, db: Session) -> List[Dict]:
        self.ensure_collection(event_id)

        # Indexer/mettre à jour les selfies des participants
        from sqlalchemy import or_  # local import
        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        user_ids = [ue.user_id for ue in user_events]
        users_with_selfies = db.query(User).filter(
            User.id.in_(user_ids),
            or_(User.selfie_path.isnot(None), User.selfie_data.isnot(None))
        ).all()
        for u in users_with_selfies:
            self.index_user_selfie(event_id, u)

        # Préparer l'image
        if isinstance(photo_input, str) and os.path.exists(photo_input):
            with open(photo_input, "rb") as f:
                image_bytes = f.read()
        elif isinstance(photo_input, (bytes, bytearray)):
            image_bytes = bytes(photo_input)
        else:
            return []

        # Recherche
        try:
            resp = self.client.search_faces_by_image(
                CollectionId=self._collection_id(event_id),
                Image={"Bytes": image_bytes},
                MaxFaces=5,
                FaceMatchThreshold=80.0,
            )
        except ClientError:
            return []

        results: List[Dict] = []
        for fm in resp.get("FaceMatches", [])[:5]:
            ext_id = fm.get("Face", {}).get("ExternalImageId")
            similarity = fm.get("Similarity", 0.0)  # 0-100
            try:
                user_id = int(ext_id) if ext_id is not None else None
            except Exception:
                user_id = None
            if user_id:
                results.append({
                    "user_id": user_id,
                    "confidence_score": int(round(float(similarity)))
                })
        return results

    def match_user_selfie_with_photos_event(self, user: User, event_id: int, db: Session) -> int:
        self.ensure_collection(event_id)
        self.index_user_selfie(event_id, user)

        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        count_matches = 0
        for p in photos:
            photo_input = p.file_path if (p.file_path and os.path.exists(p.file_path)) else p.photo_data
            if not photo_input:
                continue
            matches = self.process_photo_for_event(photo_input, event_id, db)
            for m in matches:
                if m.get("user_id") == user.id:
                    db.add(FaceMatch(photo_id=p.id, user_id=user.id, confidence_score=int(m.get("confidence_score", 0))))
                    count_matches += 1
        db.commit()
        return count_matches

    # Stubs / compat pour l'API
    def get_all_user_encodings(self, db: Session):
        return {}

    def get_user_photos_with_face(self, user_id: int, db: Session) -> List[Photo]:
        from sqlalchemy import and_
        return db.query(Photo).join(FaceMatch).filter(
            and_(FaceMatch.user_id == user_id, FaceMatch.photo_id == Photo.id)
        ).all()

    def get_all_photos_for_user(self, user_id: int, db: Session) -> List[Photo]:
        return db.query(Photo).filter(Photo.photo_type == "uploaded").all()

    def match_user_selfie_with_photos(self, user: User, db: Session):
        user_event = db.query(UserEvent).filter(UserEvent.user_id == user.id).first()
        if not user_event:
            return 0
        return self.match_user_selfie_with_photos_event(user, user_event.event_id, db)

    def process_and_save_photo(self, photo_path: str, original_filename: str,
                               photographer_id: Optional[int], db: Session) -> Photo:
        with open(photo_path, 'rb') as f:
            original_data = f.read()
        optimization_result = PhotoOptimizer.optimize_image(
            image_data=original_data,
            photo_type='uploaded'
        )
        import uuid as _uuid
        unique_filename = f"{_uuid.uuid4()}.jpg"
        event_id = None
        if photographer_id:
            event = db.query(Event).filter(Event.photographer_id == photographer_id).first()
            if event:
                event_id = event.id
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
        db.add(photo)
        db.commit()
        db.refresh(photo)
        if event_id:
            matches = self.process_photo_for_event(optimization_result['compressed_data'], event_id, db)
            for match in matches:
                db.add(FaceMatch(photo_id=photo.id, user_id=match['user_id'], confidence_score=int(match['confidence_score'])))
            db.commit()
        return photo

    def process_and_save_photo_for_event(self, photo_path: str, original_filename: str,
                                         photographer_id: int, event_id: int, db: Session) -> Photo:
        with open(photo_path, 'rb') as f:
            original_data = f.read()
        optimization_result = PhotoOptimizer.optimize_image(
            image_data=original_data,
            photo_type='uploaded'
        )
        import uuid as _uuid
        unique_filename = f"{_uuid.uuid4()}.jpg"
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
        db.add(photo)
        db.commit()
        db.refresh(photo)
        matches = self.process_photo_for_event(optimization_result['compressed_data'], event_id, db)
        for match in matches:
            db.add(FaceMatch(photo_id=photo.id, user_id=match['user_id'], confidence_score=int(match['confidence_score'])))
        db.commit()
        return photo


