import os
import time
from typing import List, Dict, Optional

import requests
from sqlalchemy.orm import Session

from models import User, Photo, FaceMatch, Event, UserEvent
from photo_optimizer import PhotoOptimizer


AZURE_FACE_ENDPOINT = os.environ.get("AZURE_FACE_ENDPOINT", "").rstrip("/")
AZURE_FACE_KEY = os.environ.get("AZURE_FACE_KEY", "")
PERSON_GROUP_PREFIX = os.environ.get("PERSON_GROUP_PREFIX", "event_")


class AzureFaceError(Exception):
    pass


class AzureFaceRecognizer:
    """
    Implémentation basée sur Azure Face API, compatible avec l'interface utilisée par l'app.

    - 1 person group = 1 événement (id stable: f"{PERSON_GROUP_PREFIX}{event_id}")
    - chaque User (avec selfie_path) => 1 Person (userData = user_id)
    - Identification: Detect (faceIds) -> Identify (candidats) -> mapping vers user_id
    """

    def __init__(self):
        self.endpoint = AZURE_FACE_ENDPOINT
        self.key = AZURE_FACE_KEY
        self.headers_json = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/json",
        }
        self.headers_bin = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream",
        }
        if not self.endpoint or not self.key:
            raise AzureFaceError("AZURE_FACE_ENDPOINT et AZURE_FACE_KEY sont requis.")

    # ---------- Helpers HTTP ----------
    def _req(self, method: str, path: str, **kwargs):
        url = f"{self.endpoint}{path}"
        r = requests.request(method, url, timeout=30, **kwargs)
        if r.status_code == 429:
            time.sleep(1.0)
            r = requests.request(method, url, timeout=30, **kwargs)
        if not r.ok:
            try:
                info = r.json()
            except Exception:
                info = r.text
            raise AzureFaceError(f"HTTP {r.status_code} {path}: {info}")
        return r

    # ---------- Person Group ----------
    def _group_id(self, event_id: int) -> str:
        return f"{PERSON_GROUP_PREFIX}{event_id}"

    def ensure_person_group(self, event_id: int, event_name: str):
        gid = self._group_id(event_id)
        r = requests.get(
            f"{self.endpoint}/face/v1.0/persongroups/{gid}",
            headers={"Ocp-Apim-Subscription-Key": self.key},
            timeout=15,
        )
        if r.status_code == 404:
            body = {"name": (event_name or gid)[:128], "userData": str(event_id)}
            self._req("PUT", f"/face/v1.0/persongroups/{gid}", headers=self.headers_json, json=body)
        elif not r.ok:
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            raise AzureFaceError(f"Impossible de vérifier le person group: {msg}")

    def train_group_and_wait(self, event_id: int):
        gid = self._group_id(event_id)
        self._req("POST", f"/face/v1.0/persongroups/{gid}/train", headers=self.headers_json)
        for _ in range(30):
            r = self._req("GET", f"/face/v1.0/persongroups/{gid}/training", headers=self.headers_json)
            st = r.json().get("status")
            if st == "succeeded":
                return
            if st == "failed":
                raise AzureFaceError("Entraînement du person group échoué.")
            time.sleep(1.0)
        raise AzureFaceError("Timeout d'entraînement du person group.")

    # ---------- Persons ----------
    def list_persons(self, event_id: int) -> List[Dict]:
        gid = self._group_id(event_id)
        r = self._req("GET", f"/face/v1.0/persongroups/{gid}/persons", headers=self.headers_json)
        return r.json()

    def get_or_create_person(self, event_id: int, user: User) -> str:
        persons = self.list_persons(event_id)
        for p in persons:
            if str(p.get("userData")) == str(user.id):
                return p["personId"]
        gid = self._group_id(event_id)
        body = {"name": (getattr(user, "username", None) or f"user_{user.id}")[:128], "userData": str(user.id)}
        r = self._req("POST", f"/face/v1.0/persongroups/{gid}/persons", headers=self.headers_json, json=body)
        return r.json()["personId"]

    def add_face_to_person_from_path(self, event_id: int, person_id: str, image_path: str):
        if not image_path or not os.path.exists(image_path):
            raise AzureFaceError(f"Selfie introuvable: {image_path}")
        gid = self._group_id(event_id)
        with open(image_path, "rb") as f:
            self._req(
                "POST",
                f"/face/v1.0/persongroups/{gid}/persons/{person_id}/persistedFaces",
                headers=self.headers_bin,
                data=f.read(),
            )

    def add_face_to_person_from_bytes(self, event_id: int, person_id: str, image_bytes: bytes):
        gid = self._group_id(event_id)
        self._req(
            "POST",
            f"/face/v1.0/persongroups/{gid}/persons/{person_id}/persistedFaces",
            headers=self.headers_bin,
            data=image_bytes,
        )

    # ---------- Detect & Identify ----------
    def detect_faces_from_path(self, image_path: str) -> List[str]:
        if not os.path.exists(image_path):
            raise AzureFaceError(f"Fichier image introuvable: {image_path}")
        with open(image_path, "rb") as f:
            r = self._req(
                "POST",
                "/face/v1.0/detect?returnFaceId=true&recognitionModel=recognition_04&detectionModel=detection_03",
                headers=self.headers_bin,
                data=f.read(),
            )
        faces = r.json()
        return [f.get("faceId") for f in faces if f.get("faceId")]

    def detect_faces_from_bytes(self, image_bytes: bytes) -> List[str]:
        r = self._req(
            "POST",
            "/face/v1.0/detect?returnFaceId=true&recognitionModel=recognition_04&detectionModel=detection_03",
            headers=self.headers_bin,
            data=image_bytes,
        )
        faces = r.json()
        return [f.get("faceId") for f in faces if f.get("faceId")]

    def identify(self, event_id: int, face_ids: List[str], max_candidates: int = 1,
                 confidence_threshold: Optional[float] = None) -> List[Dict]:
        if not face_ids:
            return []
        body = {
            "personGroupId": self._group_id(event_id),
            "faceIds": face_ids,
            "maxNumOfCandidatesReturned": max_candidates,
        }
        if confidence_threshold is not None:
            body["confidenceThreshold"] = confidence_threshold
        r = self._req("POST", "/face/v1.0/identify", headers=self.headers_json, json=body)
        return r.json()

    # ---------- API compatible app ----------
    def process_photo_for_event(self, photo_input, event_id: int, db: Session) -> List[Dict]:
        """Accepte un chemin de fichier ou des bytes. Retourne [{user_id, confidence_score}]."""
        event = db.query(Event).filter(Event.id == event_id).first()
        self.ensure_person_group(event_id, event.name if event else f"event_{event_id}")

        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        user_ids = [ue.user_id for ue in user_events]
        users_with_selfies = db.query(User).filter(
            User.id.in_(user_ids),
            User.selfie_path.isnot(None)
        ).all()

        person_map: Dict[str, int] = {}
        existing_persons = {str(p.get("userData")): p for p in self.list_persons(event_id)}
        for u in users_with_selfies:
            if str(u.id) in existing_persons:
                person_id = existing_persons[str(u.id)]["personId"]
            else:
                person_id = self.get_or_create_person(event_id, u)
            try:
                if u.selfie_path and os.path.exists(u.selfie_path):
                    self.add_face_to_person_from_path(event_id, person_id, u.selfie_path)
                elif u.selfie_data:
                    self.add_face_to_person_from_bytes(event_id, person_id, u.selfie_data)
            except AzureFaceError:
                pass
            person_map[person_id] = u.id

        try:
            self.train_group_and_wait(event_id)
        except AzureFaceError:
            pass

        if isinstance(photo_input, (bytes, bytearray)):
            face_ids = self.detect_faces_from_bytes(bytes(photo_input))
        elif isinstance(photo_input, str) and os.path.exists(photo_input):
            face_ids = self.detect_faces_from_path(photo_input)
        else:
            return []

        if not face_ids:
            return []

        results = self.identify(event_id, face_ids, max_candidates=1)
        matches: List[Dict] = []
        for res in results:
            candidates = res.get("candidates", [])
            if not candidates:
                continue
            cand = candidates[0]
            person_id = cand.get("personId")
            conf = float(cand.get("confidence", 0.0))
            user_id = person_map.get(person_id)
            if user_id:
                matches.append({"user_id": user_id, "confidence_score": int(round(conf * 100))})
        return matches

    def match_user_selfie_with_photos_event(self, user: User, event_id: int, db: Session) -> int:
        event = db.query(Event).filter(Event.id == event_id).first()
        self.ensure_person_group(event_id, event.name if event else f"event_{event_id}")

        person_id = self.get_or_create_person(event_id, user)
        try:
            if user.selfie_path and os.path.exists(user.selfie_path):
                self.add_face_to_person_from_path(event_id, person_id, user.selfie_path)
            elif user.selfie_data:
                self.add_face_to_person_from_bytes(event_id, person_id, user.selfie_data)
        except AzureFaceError:
            pass

        try:
            self.train_group_and_wait(event_id)
        except AzureFaceError:
            pass

        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        count_matches = 0
        for p in photos:
            photo_input = p.file_path if (p.file_path and os.path.exists(p.file_path)) else p.photo_data
            if not photo_input:
                continue
            if isinstance(photo_input, (bytes, bytearray)):
                face_ids = self.detect_faces_from_bytes(bytes(photo_input))
            else:
                face_ids = self.detect_faces_from_path(photo_input)
            if not face_ids:
                continue
            res = self.identify(event_id, face_ids, max_candidates=1)
            for r in res:
                cand = (r.get("candidates") or [None])[0]
                if not cand:
                    continue
                if cand.get("personId") == person_id:
                    conf = float(cand.get("confidence", 0.0))
                    db.add(FaceMatch(photo_id=p.id, user_id=user.id, confidence_score=int(round(conf * 100))))
                    count_matches += 1
        db.commit()
        return count_matches

    # Stubs/compat
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

    # Création + reconnaissance, calqué sur l'implémentation locale
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
                face_match = FaceMatch(
                    photo_id=photo.id,
                    user_id=match['user_id'],
                    confidence_score=int(match['confidence_score'])
                )
                db.add(face_match)
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
            face_match = FaceMatch(
                photo_id=photo.id,
                user_id=match['user_id'],
                confidence_score=int(match['confidence_score'])
            )
            db.add(face_match)
        db.commit()
        return photo


