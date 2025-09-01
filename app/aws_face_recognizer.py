import os
from typing import List, Dict, Optional, Set, Tuple

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from models import User, Photo, FaceMatch, Event, UserEvent
from photo_optimizer import PhotoOptimizer
from io import BytesIO as _BytesIO
from PIL import Image as _Image, ImageOps as _ImageOps


AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")  # Ireland (Rekognition supported, close to FR)
COLL_PREFIX = os.environ.get("AWS_REKOGNITION_COLLECTION_PREFIX", "event_")

# Recherche
AWS_SEARCH_MAXFACES = int(os.environ.get("AWS_REKOGNITION_SEARCH_MAXFACES", "10") or "10")
AWS_SEARCH_THRESHOLD = float(os.environ.get("AWS_REKOGNITION_FACE_THRESHOLD", "50") or "50")
AWS_SEARCH_QUALITY_FILTER = os.environ.get("AWS_REKOGNITION_SEARCH_QUALITY_FILTER", "AUTO").upper()  # AUTO|LOW|MEDIUM|HIGH|NONE

# Détection
AWS_DETECT_MIN_CONF = float(os.environ.get("AWS_REKOGNITION_DETECT_MIN_CONF", "70") or "70")

# Préparation image / crop
AWS_IMAGE_MAX_DIM = int(os.environ.get("AWS_REKOGNITION_IMAGE_MAX_DIM", "2048") or "2048")
AWS_CROP_PADDING = float(os.environ.get("AWS_REKOGNITION_CROP_PADDING", "0.2") or "0.2")  # 20% padding
AWS_MIN_CROP_SIDE = int(os.environ.get("AWS_REKOGNITION_MIN_CROP_SIDE", "36") or "36")


class AwsFaceRecognizer:
    """
    Provider basé sur AWS Rekognition Collections.
    - 1 collection par événement: f"{COLL_PREFIX}{event_id}"
    - Chaque utilisateur (selfie) est indexé avec l'ExternalImageId = user_id
    - Matching par SearchFacesByImage
    """

    def __init__(self):
        self.client = boto3.client("rekognition", region_name=AWS_REGION)
        print(f"[FaceRecognition][AWS] Using region: {AWS_REGION}")
        # Cache simple en mémoire pour éviter de réindexer à chaque photo
        self._indexed_events: Set[int] = set()

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

        # Charger les octets du selfie depuis le chemin ou la base de données
        image_bytes: Optional[bytes] = None
        if getattr(user, "selfie_path", None) and os.path.exists(user.selfie_path):
            try:
                with open(user.selfie_path, "rb") as f:
                    image_bytes = f.read()
            except Exception:
                image_bytes = None
        elif getattr(user, "selfie_data", None):
            try:
                image_bytes = bytes(user.selfie_data)
            except Exception:
                image_bytes = None

        if not image_bytes:
            # Rien à indexer si aucun selfie n'est disponible
            return

        # Supprimer d'abord d'anciennes faces de cet utilisateur pour éviter des résidus de visages obsolètes
        try:
            next_token = None
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                faces = self.client.list_faces(**kwargs)
                for f in faces.get('Faces', []):
                    if f.get('ExternalImageId') == str(user.id):
                        try:
                            self.client.delete_faces(CollectionId=coll_id, FaceIds=[f.get('FaceId')])
                        except ClientError:
                            pass
                next_token = faces.get("NextToken")
                if not next_token:
                    break
        except ClientError:
            # On ignore les erreurs de suppression pour ne pas bloquer l'indexation
            pass

        # Indexer le selfie de l'utilisateur dans la collection de l'événement
        try:
            self.client.index_faces(
                CollectionId=coll_id,
                Image={"Bytes": image_bytes},
                ExternalImageId=str(user.id),
                DetectionAttributes=[],
                QualityFilter="AUTO",
                MaxFaces=1,
            )
        except ClientError:
            # Si l'indexation échoue, on laisse la fonction silencieuse pour ne pas interrompre le flux
            pass

    def ensure_event_users_indexed(self, event_id: int, db: Session):
        """
        Indexe les selfies des utilisateurs d'un événement une seule fois par processus.
        Évite les appels IndexFaces répétés lors du traitement de chaque photo.
        """
        if event_id in self._indexed_events:
            return
        from sqlalchemy import or_  # local import
        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        user_ids = [ue.user_id for ue in user_events]
        # Restreindre aux utilisateurs existants et ayant un selfie
        users_with_selfies = db.query(User).filter(
            User.id.in_(user_ids),
            or_(User.selfie_path.isnot(None), User.selfie_data.isnot(None))
        ).all()
        for u in users_with_selfies:
            self.index_user_selfie(event_id, u)

        # Nettoyer la collection des visages orphelins (ExternalImageId ne correspondant plus aux users de l'événement)
        try:
            allowed_external_ids = set(str(uid) for uid in user_ids)
            coll_id = self._collection_id(event_id)
            next_token = None
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                faces = self.client.list_faces(**kwargs)
                stale_face_ids = []
                for f in faces.get('Faces', []) or []:
                    ext = f.get('ExternalImageId')
                    face_id = f.get('FaceId')
                    if ext is None or ext not in allowed_external_ids:
                        if face_id:
                            stale_face_ids.append(face_id)
                if stale_face_ids:
                    try:
                        self.client.delete_faces(CollectionId=coll_id, FaceIds=stale_face_ids)
                    except ClientError:
                        pass
                next_token = faces.get("NextToken")
                if not next_token:
                    break
        except ClientError:
            pass

        self._indexed_events.add(event_id)

    def _get_allowed_event_user_ids(self, event_id: int, db: Session) -> set[int]:
        """Renvoie l'ensemble des user_id associés à l'événement et existant dans la table users."""
        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        event_user_ids = {ue.user_id for ue in user_events}
        if not event_user_ids:
            return set()
        existing_ids = {row[0] for row in db.query(User.id).filter(User.id.in_(list(event_user_ids))).all()}
        return existing_ids

    # ---------- Helpers image ----------
    def _prepare_image_bytes(self, photo_input) -> Optional[bytes]:
        """Charge une image (path/bytes) et retourne des bytes JPEG normalisés (EXIF transposé).

        Limite la dimension max à AWS_IMAGE_MAX_DIM pour rester dans les limites de payload.
        """
        try:
            if isinstance(photo_input, str) and os.path.exists(photo_input):
                with open(photo_input, "rb") as f:
                    raw = f.read()
            elif isinstance(photo_input, (bytes, bytearray)):
                raw = bytes(photo_input)
            else:
                return None

            im = _Image.open(_BytesIO(raw))
            im = _ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            # Downscale si nécessaire (ne pas agrandir)
            w, h = im.size
            max_dim = AWS_IMAGE_MAX_DIM
            scale = min(1.0, float(max_dim) / float(max(w, h)))
            if scale < 1.0:
                im = im.resize((int(w * scale), int(h * scale)), _Image.Resampling.LANCZOS)
            out = _BytesIO()
            im.save(out, format="JPEG", quality=92, optimize=True, progressive=False)
            return out.getvalue()
        except Exception:
            # Fallback brut si échec PIL
            try:
                return bytes(photo_input) if isinstance(photo_input, (bytes, bytearray)) else None
            except Exception:
                return None

    def _detect_faces_boxes(self, image_bytes: bytes) -> List[Dict]:
        """Appelle Rekognition DetectFaces et renvoie les FaceDetails filtrés par confiance."""
        try:
            resp = self.client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["DEFAULT"])
            faces = resp.get("FaceDetails", []) or []
            faces = [f for f in faces if float(f.get("Confidence", 0.0)) >= AWS_DETECT_MIN_CONF]
            return faces
        except ClientError as e:
            print(f"❌ AWS DetectFaces error: {e}")
            return []

    def _crop_face_regions(self, image_bytes: bytes, boxes: List[Dict]) -> List[bytes]:
        """Recadre l'image selon les BoundingBox Rekognition.

        BoundingBox fields are normalized [0,1]: Left, Top, Width, Height
        """
        crops: List[bytes] = []
        try:
            im = _Image.open(_BytesIO(image_bytes))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            W, H = im.size
            for f in boxes:
                bb = f.get("BoundingBox") or {}
                left = float(bb.get("Left", 0.0))
                top = float(bb.get("Top", 0.0))
                width = float(bb.get("Width", 0.0))
                height = float(bb.get("Height", 0.0))
                x1 = int(max(0, left * W))
                y1 = int(max(0, top * H))
                x2 = int(min(W, (left + width) * W))
                y2 = int(min(H, (top + height) * H))
                # Padding
                pad = int(max(x2 - x1, y2 - y1) * AWS_CROP_PADDING)
                x1p = max(0, x1 - pad)
                y1p = max(0, y1 - pad)
                x2p = min(W, x2 + pad)
                y2p = min(H, y2 + pad)
                if (x2p - x1p) < AWS_MIN_CROP_SIDE or (y2p - y1p) < AWS_MIN_CROP_SIDE:
                    continue
                try:
                    crop = im.crop((x1p, y1p, x2p, y2p))
                    out = _BytesIO()
                    crop.save(out, format="JPEG", quality=92, optimize=True)
                    crops.append(out.getvalue())
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️  Crop error: {e}")
        return crops

    def process_photo_for_event(self, photo_input, event_id: int, db: Session) -> List[Dict]:
        """Multi-visages: DetectFaces -> crops -> SearchFacesByImage pour chaque visage.

        Retourne une liste dédupliquée par user_id avec le meilleur score par photo.
        """
        self.ensure_collection(event_id)
        self.ensure_event_users_indexed(event_id, db)

        # Normaliser et sécuriser l'image
        image_bytes = self._prepare_image_bytes(photo_input)
        if not image_bytes:
            return []

        # 1) Détecter tous les visages
        faces = self._detect_faces_boxes(image_bytes)
        print(f"[AWS] DetectFaces: {len(faces)} faces (min_conf={AWS_DETECT_MIN_CONF})")

        # 2) Si aucun visage, fallback: un seul SearchFacesByImage sur l'image entière (comportement historique)
        # Préparer le filtre d'IDs valides pour cet événement
        allowed_user_ids: set[int] = self._get_allowed_event_user_ids(event_id, db)

        if not faces:
            try:
                resp = self.client.search_faces_by_image(
                    CollectionId=self._collection_id(event_id),
                    Image={"Bytes": image_bytes},
                    MaxFaces=AWS_SEARCH_MAXFACES,
                    FaceMatchThreshold=AWS_SEARCH_THRESHOLD,
                    QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                )
            except ClientError as e:
                print(f"❌ Erreur AWS Rekognition (fallback search): {e}")
                return []
            user_best: Dict[int, float] = {}
            for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                ext_id = fm.get("Face", {}).get("ExternalImageId")
                similarity = float(fm.get("Similarity", 0.0))
                try:
                    user_id = int(ext_id) if ext_id is not None else None
                except Exception:
                    user_id = None
                if user_id is None or user_id not in allowed_user_ids:
                    continue
                if (user_id not in user_best) or (similarity > user_best[user_id]):
                    user_best[user_id] = similarity
            return [{"user_id": uid, "confidence_score": int(round(sim))} for uid, sim in user_best.items()]

        # 3) Recadrer et rechercher pour chaque visage détecté
        crops = self._crop_face_regions(image_bytes, faces)
        print(f"[AWS] Crops to search: {len(crops)}")

        user_best: Dict[int, float] = {}
        for i, crop_bytes in enumerate(crops):
            try:
                resp = self.client.search_faces_by_image(
                    CollectionId=self._collection_id(event_id),
                    Image={"Bytes": crop_bytes},
                    MaxFaces=AWS_SEARCH_MAXFACES,
                    FaceMatchThreshold=AWS_SEARCH_THRESHOLD,
                    QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                )
            except ClientError as e:
                print(f"❌ Erreur AWS SearchFacesByImage (crop #{i}): {e}")
                continue
            for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                ext_id = fm.get("Face", {}).get("ExternalImageId")
                similarity = float(fm.get("Similarity", 0.0))
                try:
                    user_id = int(ext_id) if ext_id is not None else None
                except Exception:
                    user_id = None
                if user_id is None or user_id not in allowed_user_ids:
                    continue
                if (user_id not in user_best) or (similarity > user_best[user_id]):
                    user_best[user_id] = similarity

        results: List[Dict] = [{"user_id": uid, "confidence_score": int(round(sim))} for uid, sim in user_best.items()]
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
            allowed_ids = self._get_allowed_event_user_ids(event_id, db)
            for match in matches:
                uid = int(match.get('user_id')) if match.get('user_id') is not None else None
                if uid in allowed_ids:
                    db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(match['confidence_score'])))
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
        # Filtrer par utilisateurs existants de l'événement pour éviter les FK errors
        allowed_ids = self._get_allowed_event_user_ids(event_id, db)
        for match in matches:
            uid = int(match.get('user_id')) if match.get('user_id') is not None else None
            if uid in allowed_ids:
                db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(match['confidence_score'])))
        db.commit()
        return photo


