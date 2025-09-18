import os
import time
from typing import List, Dict, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from models import User, Photo, FaceMatch, Event, UserEvent
from aws_metrics import aws_metrics
from photo_optimizer import PhotoOptimizer
from io import BytesIO as _BytesIO
from PIL import Image as _Image, ImageOps as _ImageOps


AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")  # Ireland (Rekognition supported, close to FR)
COLL_PREFIX = os.environ.get("AWS_REKOGNITION_COLLECTION_PREFIX", "event_")

# Recherche
AWS_SEARCH_MAXFACES = int(os.environ.get("AWS_REKOGNITION_SEARCH_MAXFACES", "10") or "10")
# Spécifique recherche depuis selfie: besoin de récupérer potentiellement des dizaines/centaines de visages
AWS_SELFIE_SEARCH_MAXFACES = int(os.environ.get("AWS_REKOGNITION_SELFIE_SEARCH_MAXFACES", "500") or "500")
AWS_SEARCH_THRESHOLD = float(os.environ.get("AWS_REKOGNITION_FACE_THRESHOLD", "50") or "50")
AWS_SEARCH_QUALITY_FILTER = os.environ.get("AWS_REKOGNITION_SEARCH_QUALITY_FILTER", "AUTO").upper()  # AUTO|LOW|MEDIUM|HIGH|NONE

# Détection
AWS_DETECT_MIN_CONF = float(os.environ.get("AWS_REKOGNITION_DETECT_MIN_CONF", "70") or "70")

# Préparation image / crop
AWS_IMAGE_MAX_DIM = int(os.environ.get("AWS_REKOGNITION_IMAGE_MAX_DIM", "3072") or "3072")
AWS_CROP_PADDING = float(os.environ.get("AWS_REKOGNITION_CROP_PADDING", "0.3") or "0.3")  # 30% padding
AWS_MIN_CROP_SIDE = int(os.environ.get("AWS_REKOGNITION_MIN_CROP_SIDE", "36") or "36")
# Dimension minimale de sortie pour un crop visage (on upsample si nécessaire)
AWS_MIN_OUTPUT_CROP_SIDE = int(os.environ.get("AWS_REKOGNITION_MIN_OUTPUT_CROP_SIDE", "448") or "448")
# Seuil d'aire relative (Width*Height) sous lequel on tente une détection upscalée
AWS_TINY_FACE_AREA_THRESHOLD = float(os.environ.get("AWS_REKOGNITION_TINY_FACE_AREA", "0.015") or "0.015")

# Parallélisation bornée (bornes codées simplement; pas d'arrière-plan)
MAX_PARALLEL_PER_REQUEST = 4
AWS_MAX_RETRIES = 2
AWS_BACKOFF_BASE_SEC = 0.2


class AwsFaceRecognizer:
    """
    Provider basé sur AWS Rekognition Collections.
    - 1 collection par événement: f"{COLL_PREFIX}{event_id}"
    - Chaque utilisateur (selfie) est indexé avec ExternalImageId = "user:{user_id}"
    - Chaque visage de photo est indexé avec ExternalImageId = "photo:{photo_id}"
    - Matching inversé: 
      * lors d'une modif selfie: SearchFacesByImage(selfie) => ExternalImageId "photo:{photo_id}" => FaceMatch
      * lors d'un upload photo: IndexFaces(photo) => FaceId => SearchFaces(FaceId) => ExternalImageId "user:{user_id}" => FaceMatch
    """

    def __init__(self):
        self.client = boto3.client("rekognition", region_name=AWS_REGION)
        print(f"[FaceRecognition][AWS] Using region: {AWS_REGION}")
        # Cache simple en mémoire pour éviter de réindexer à chaque photo
        self._indexed_events: Set[int] = set()
        self._photos_indexed_events: Set[int] = set()
        # Cache FaceId par (event_id, user_id) pour accélérer les recherches
        self._user_faceid_cache: Dict[Tuple[int, int], str] = {}
        # Seuil Rekognition (0-100) configurable à chaud
        try:
            self.search_threshold: float = float(os.environ.get("AWS_REKOGNITION_FACE_THRESHOLD", str(AWS_SEARCH_THRESHOLD)) or AWS_SEARCH_THRESHOLD)
        except Exception:
            self.search_threshold = AWS_SEARCH_THRESHOLD

    def _collection_id(self, event_id: int) -> str:
        return f"{COLL_PREFIX}{event_id}"

    def ensure_collection(self, event_id: int):
        coll_id = self._collection_id(event_id)
        try:
            aws_metrics.inc('DescribeCollection')
            self.client.describe_collection(CollectionId=coll_id)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ResourceNotFoundException":
                aws_metrics.inc('CreateCollection')
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
                aws_metrics.inc('ListFaces')
                faces = self.client.list_faces(**kwargs)
                for f in faces.get('Faces', []):
                    # Ancien schéma (str(user.id)) et nouveau (user:{id})
                    ext = f.get('ExternalImageId')
                    if ext == str(user.id) or ext == f"user:{user.id}":
                        try:
                            aws_metrics.inc('DeleteFaces')
                            self.client.delete_faces(CollectionId=coll_id, FaceIds=[f.get('FaceId')])
                        except ClientError:
                            pass
                next_token = faces.get("NextToken")
                if not next_token:
                    break
        except ClientError:
            # On ignore les erreurs de suppression pour ne pas bloquer l'indexation
            pass

        # Préparer l'image (EXIF, RGB, dimension) et recadrer le meilleur visage
        prepared = self._prepare_image_bytes(image_bytes)
        if not prepared:
            return
        best_crop = self._best_face_crop_or_image(prepared)

        # Indexer le selfie de l'utilisateur dans la collection de l'événement
        try:
            aws_metrics.inc('IndexFaces')
            resp = self.client.index_faces(
                CollectionId=coll_id,
                Image={"Bytes": best_crop},
                ExternalImageId=f"user:{user.id}",
                DetectionAttributes=[],
                QualityFilter="AUTO",
                MaxFaces=1,
            )
            # Mémoriser le FaceId pour accélérer les prochaines recherches
            try:
                for rec in (resp.get('FaceRecords') or []):
                    fid = ((rec or {}).get('Face') or {}).get('FaceId')
                    if fid:
                        self._user_faceid_cache[(event_id, user.id)] = fid
                        break
            except Exception:
                pass
        except ClientError:
            # Si l'indexation échoue, on laisse la fonction silencieuse pour ne pas interrompre le flux
            pass

    def _delete_photo_faces(self, event_id: int, photo_id: int):
        coll_id = self._collection_id(event_id)
        try:
            next_token = None
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                aws_metrics.inc('ListFaces')
                faces = self.client.list_faces(**kwargs)
                to_delete = []
                for f in faces.get('Faces', []) or []:
                    if f.get('ExternalImageId') == f"photo:{photo_id}":
                        fid = f.get('FaceId')
                        if fid:
                            to_delete.append(fid)
                if to_delete:
                    try:
                        self.client.delete_faces(CollectionId=coll_id, FaceIds=to_delete)
                    except ClientError:
                        pass
                next_token = faces.get("NextToken")
                if not next_token:
                    break
        except ClientError:
            pass

    def _index_photo_faces_and_get_ids(self, event_id: int, photo_id: int, image_bytes: bytes) -> List[str]:
        """Indexe les visages d'une photo (crops carrés) et retourne la liste des FaceId créés."""
        coll_id = self._collection_id(event_id)
        # Nettoyer d'abord d'anciens visages pour ce photo_id
        self._delete_photo_faces(event_id, photo_id)
        # Détecter et recadrer tous les visages puis indexer par crop pour une meilleure qualité
        try:
            faces = self._detect_faces_boxes(image_bytes)
            crops = self._crop_face_regions(image_bytes, faces) if faces else []
        except Exception:
            crops = []

        face_ids: List[str] = []
        if crops:
            for crop_bytes in crops:
                try:
                    aws_metrics.inc('IndexFaces')
                    resp = self.client.index_faces(
                        CollectionId=coll_id,
                        Image={"Bytes": crop_bytes},
                        ExternalImageId=f"photo:{photo_id}",
                        DetectionAttributes=[],
                        QualityFilter="AUTO",
                        MaxFaces=1,
                    )
                    for rec in (resp.get('FaceRecords') or []):
                        face = rec.get('Face') or {}
                        fid = face.get('FaceId')
                        if fid:
                            face_ids.append(fid)
                except ClientError as e:
                    print(f"❌ AWS IndexFaces error (crop) for photo {photo_id}: {e}")
                    continue
        else:
            # Fallback: indexation sur l'image entière (comportement historique)
            try:
                aws_metrics.inc('IndexFaces')
                resp = self.client.index_faces(
                    CollectionId=coll_id,
                    Image={"Bytes": image_bytes},
                    ExternalImageId=f"photo:{photo_id}",
                    DetectionAttributes=[],
                    QualityFilter="AUTO",
                    MaxFaces=50,
                )
                for rec in (resp.get('FaceRecords') or []):
                    face = rec.get('Face') or {}
                    fid = face.get('FaceId')
                    if fid:
                        face_ids.append(fid)
            except ClientError as e:
                print(f"❌ AWS IndexFaces error for photo {photo_id}: {e}")
                return []

        return face_ids

    def ensure_event_photos_indexed(self, event_id: int, db: Session):
        """Indexe tous les visages des photos de l'événement (idempotent grâce au nettoyage par photo).

        Toujours ré-exécuter pour couvrir les nouvelles photos; le nettoyage par photo rend l'opération sûre.
        """
        self.ensure_collection(event_id)
        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        for p in photos:
            photo_input = p.file_path if (p.file_path and os.path.exists(p.file_path)) else p.photo_data
            if not photo_input:
                continue
            img_bytes = self._prepare_image_bytes(photo_input)
            if not img_bytes:
                continue
            self._index_photo_faces_and_get_ids(event_id, p.id, img_bytes)
        # Ne pas mémoriser pour autoriser la réindexation quand de nouvelles photos arrivent

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

        # Nettoyer la collection des visages orphelins: 
        # - Conserver toutes les faces "photo:{photo_id}" (appartiennent à l'événement)
        # - Conserver les faces des users de l'événement sous formes "user:{id}" ou legacy "{id}"
        # - Supprimer uniquement les faces "user:*" dont l'id n'est pas dans la liste des users de l'événement
        try:
            allowed_user_ids = set(str(uid) for uid in user_ids)
            coll_id = self._collection_id(event_id)
            next_token = None
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                faces = self.client.list_faces(**kwargs)
                stale_face_ids = []
                for f in faces.get('Faces', []) or []:
                    ext = (f.get('ExternalImageId') or "").strip()
                    face_id = f.get('FaceId')
                    if ext.startswith('photo:'):
                        continue  # ne pas supprimer les faces des photos ici
                    if ext.startswith('user:'):
                        try:
                            uid = ext.split(':', 1)[1]
                        except Exception:
                            uid = None
                        if not uid or uid not in allowed_user_ids:
                            if face_id:
                                stale_face_ids.append(face_id)
                    else:
                        # legacy: ext est un id numérique
                        if ext and ext.isdigit():
                            if ext not in allowed_user_ids and face_id:
                                stale_face_ids.append(face_id)
                        else:
                            # ext inconnu -> supprimer prudemment
                            if face_id:
                                stale_face_ids.append(face_id)
                if stale_face_ids:
                    try:
                        aws_metrics.inc('DeleteFaces')
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
        """Appelle Rekognition DetectFaces (Attributes=ALL), filtre par confiance,
        et tente une deuxième passe upscalée si tous les visages détectés sont très petits.
        """
        try:
            aws_metrics.inc('DetectFaces')
            resp = self.client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["ALL"])
            faces = (resp.get("FaceDetails", []) or [])
            faces = [f for f in faces if float(f.get("Confidence", 0.0)) >= AWS_DETECT_MIN_CONF]
            if not faces:
                return []
            # Vérifier la taille relative des visages; si trop petits, retenter avec image upscalée
            try:
                # Ouvrir pour récupérer dimensions
                im = _Image.open(_BytesIO(image_bytes))
                W, H = im.size
                max_area = 0.0
                for f in faces:
                    bb = (f.get('BoundingBox') or {})
                    area = float(bb.get('Width', 0.0)) * float(bb.get('Height', 0.0))
                    if area > max_area:
                        max_area = area
                if max_area < AWS_TINY_FACE_AREA_THRESHOLD:
                    # Upscale x2 (borné par une limite raisonnable)
                    try:
                        up = im.resize((min(W * 2, AWS_IMAGE_MAX_DIM), min(H * 2, AWS_IMAGE_MAX_DIM)), _Image.Resampling.LANCZOS)
                        out = _BytesIO()
                        up.save(out, format="JPEG", quality=92, optimize=True)
                        up_bytes = out.getvalue()
                        aws_metrics.inc('DetectFaces')
                        resp2 = self.client.detect_faces(Image={"Bytes": up_bytes}, Attributes=["ALL"])
                        faces2 = (resp2.get("FaceDetails", []) or [])
                        faces2 = [f for f in faces2 if float(f.get("Confidence", 0.0)) >= AWS_DETECT_MIN_CONF]
                        # Garder la passe qui retourne le plus de visages
                        if len(faces2) >= len(faces):
                            return faces2
                    except Exception:
                        pass
            except Exception:
                pass
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
                # Rectangle initial
                x1 = int(max(0, left * W))
                y1 = int(max(0, top * H))
                x2 = int(min(W, (left + width) * W))
                y2 = int(min(H, (top + height) * H))
                # Padding proportionnel
                base_side = max(x2 - x1, y2 - y1)
                pad = int(base_side * AWS_CROP_PADDING)
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                half = (base_side // 2) + pad
                # Carré centré
                x1p = max(0, cx - half)
                y1p = max(0, cy - half)
                x2p = min(W, cx + half)
                y2p = min(H, cy + half)
                # Ajuster si on a été coupé par les bords (recentrer si possible)
                side = min(x2p - x1p, y2p - y1p)
                if side < AWS_MIN_CROP_SIDE:
                    continue
                try:
                    crop = im.crop((x1p, y1p, x1p + side, y1p + side))
                    # Upscale si le crop est trop petit pour une bonne empreinte
                    if side < AWS_MIN_OUTPUT_CROP_SIDE:
                        try:
                            crop = crop.resize((AWS_MIN_OUTPUT_CROP_SIDE, AWS_MIN_OUTPUT_CROP_SIDE), _Image.Resampling.LANCZOS)
                        except Exception:
                            pass
                    out = _BytesIO()
                    crop.save(out, format="JPEG", quality=92, optimize=True)
                    crops.append(out.getvalue())
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️  Crop error: {e}")
        return crops

    def _best_face_crop_or_image(self, image_bytes: bytes) -> bytes:
        """Retourne le meilleur crop visage (carré + padding) si détecté, sinon l'image telle quelle.

        Critère: priorité à Quality.Sharpness puis à l'aire du bounding box.
        """
        try:
            faces = self._detect_faces_boxes(image_bytes)
            if not faces:
                return image_bytes
            # Sélection du meilleur visage
            def score_face(fd: Dict) -> Tuple[float, float]:
                qual = (fd.get('Quality') or {})
                sharp = float(qual.get('Sharpness', 0.0))
                bb = (fd.get('BoundingBox') or {})
                area = float(bb.get('Width', 0.0)) * float(bb.get('Height', 0.0))
                return (sharp, area)
            best = max(faces, key=score_face)
            # Recadrer uniquement ce visage
            crops = self._crop_face_regions(image_bytes, [best])
            return crops[0] if crops else image_bytes
        except Exception:
            return image_bytes

    # ---------- Helpers AWS avec retry ----------
    def _search_faces_retry(self, collection_id: str, face_id: str, max_faces: Optional[int] = None):
        last_exc = None
        mf = int(max_faces or AWS_SEARCH_MAXFACES)
        for attempt in range(AWS_MAX_RETRIES + 1):
            try:
                aws_metrics.inc('SearchFaces')
                return self.client.search_faces(
                    CollectionId=collection_id,
                    FaceId=face_id,
                    MaxFaces=mf,
                    FaceMatchThreshold=self.search_threshold,
                )
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if "Throttl" in code or code in {"ProvisionedThroughputExceededException"}:
                    time.sleep(AWS_BACKOFF_BASE_SEC * (2 ** attempt))
                    last_exc = e
                    continue
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                break
        if last_exc:
            print(f"⚠️  search_faces retry failed: {last_exc}")
        return None

    def _search_faces_by_image_retry(self, collection_id: str, image_bytes: bytes):
        last_exc = None
        for attempt in range(AWS_MAX_RETRIES + 1):
            try:
                aws_metrics.inc('SearchFacesByImage')
                return self.client.search_faces_by_image(
                    CollectionId=collection_id,
                    Image={"Bytes": image_bytes},
                    MaxFaces=AWS_SEARCH_MAXFACES,
                    FaceMatchThreshold=self.search_threshold,
                    QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                )
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if "Throttl" in code or code in {"ProvisionedThroughputExceededException"}:
                    time.sleep(AWS_BACKOFF_BASE_SEC * (2 ** attempt))
                    last_exc = e
                    continue
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                break
        if last_exc:
            print(f"⚠️  search_faces_by_image retry failed: {last_exc}")
        return None

    def _find_user_face_id(self, event_id: int, user_id: int) -> Optional[str]:
        coll_id = self._collection_id(event_id)
        # Cache rapide
        fid_cached = self._user_faceid_cache.get((event_id, user_id))
        if fid_cached:
            return fid_cached
        next_token = None
        target_exts = {str(user_id), f"user:{user_id}"}
        try:
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                resp = self.client.list_faces(**kwargs)
                for f in resp.get('Faces', []) or []:
                    ext = (f.get('ExternalImageId') or '').strip()
                    if ext in target_exts:
                        fid = f.get('FaceId')
                        if fid:
                            # Mémoriser en cache et retourner
                            self._user_faceid_cache[(event_id, user_id)] = fid
                            return fid
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except ClientError as e:
            print(f"⚠️  list_faces error while finding user face id: {e}")
        return None

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
                    FaceMatchThreshold=self.search_threshold,
                    QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                )
            except ClientError as e:
                print(f"❌ Erreur AWS Rekognition (fallback search): {e}")
                return []
            user_best: Dict[int, float] = {}
            for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                ext_id = (fm.get("Face", {}) or {}).get("ExternalImageId") or ""
                similarity = float(fm.get("Similarity", 0.0))
                user_id: Optional[int] = None
                if isinstance(ext_id, str):
                    if ext_id.startswith("user:"):
                        try:
                            user_id = int(ext_id.split(":", 1)[1])
                        except Exception:
                            user_id = None
                    elif ext_id.isdigit():
                        try:
                            user_id = int(ext_id)
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
        if crops:
            coll_id = self._collection_id(event_id)
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_PER_REQUEST) as ex:
                futures = {ex.submit(self._search_faces_by_image_retry, coll_id, crop_bytes): idx for idx, crop_bytes in enumerate(crops)}
                for fut in as_completed(futures):
                    resp = fut.result()
                    if not resp:
                        continue
                    for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                        ext_id = (fm.get("Face", {}) or {}).get("ExternalImageId") or ""
                        similarity = float(fm.get("Similarity", 0.0))
                        user_id: Optional[int] = None
                        if isinstance(ext_id, str):
                            if ext_id.startswith("user:"):
                                try:
                                    user_id = int(ext_id.split(":", 1)[1])
                                except Exception:
                                    user_id = None
                            elif ext_id.isdigit():
                                try:
                                    user_id = int(ext_id)
                                except Exception:
                                    user_id = None
                        if user_id is None or user_id not in allowed_user_ids:
                            continue
                        if (user_id not in user_best) or (similarity > user_best[user_id]):
                            user_best[user_id] = similarity

        results: List[Dict] = [{"user_id": uid, "confidence_score": int(round(sim))} for uid, sim in user_best.items()]
        return results

    def match_user_selfie_with_photos_event(self, user: User, event_id: int, db: Session) -> int:
        """Matching inversé: recherche des faces de photos à partir du selfie (1 seul appel image).

        1) Indexer/mettre à jour le selfie (ExternalImageId=user:{id})
        2) SearchFacesByImage(selfie) sur la collection de l'événement
        3) Filtrer les matches "photo:{photo_id}" et créer FaceMatch en bulk
        """
        self.ensure_collection(event_id)
        self.index_user_selfie(event_id, user)

        # Charger les octets du selfie
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
            return 0

        # Ne pas supprimer les anciens FaceMatch; on ne fait qu'ajouter les nouveaux afin de préserver l'historique

        # Chercher les faces photo qui matchent le selfie
        # Préférence: utiliser SearchFaces avec le FaceId du selfie déjà indexé (plus robuste)
        resp = None
        user_fid = self._find_user_face_id(event_id, user.id)
        if user_fid:
            resp = self._search_faces_retry(self._collection_id(event_id), user_fid, max_faces=AWS_SELFIE_SEARCH_MAXFACES)
        if not resp:
            try:
                resp = self.client.search_faces_by_image(
                    CollectionId=self._collection_id(event_id),
                    Image={"Bytes": image_bytes},
                    MaxFaces=AWS_SELFIE_SEARCH_MAXFACES,
                    FaceMatchThreshold=self.search_threshold,
                    QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                )
            except ClientError as e:
                print(f"❌ Erreur AWS SearchFacesByImage (selfie->photo): {e}")
                return 0

        # Extraire les photo_id à partir des ExternalImageId "photo:{photo_id}"
        matched_photo_ids: Dict[int, int] = {}
        for fm in resp.get("FaceMatches", [])[:AWS_SELFIE_SEARCH_MAXFACES]:
            face = fm.get("Face") or {}
            ext = (face.get("ExternalImageId") or "").strip()
            if not ext or not ext.startswith("photo:"):
                continue
            try:
                pid = int(ext.split(":", 1)[1])
            except Exception:
                continue
            similarity = int(float(fm.get("Similarity", 0.0)))
            prev = matched_photo_ids.get(pid)
            if prev is None or similarity > prev:
                matched_photo_ids[pid] = similarity

        # Créer des FaceMatch en bulk
        from sqlalchemy import and_ as _and

        allowed_ids = set(pid for (pid,) in db.query(Photo.id).filter(Photo.event_id == event_id, Photo.id.in_(list(matched_photo_ids.keys()))).all())
        count_matches = 0
        for pid in allowed_ids:
            score = int(matched_photo_ids.get(pid) or 0)
            # Éviter les doublons; mettre à jour si meilleur score
            try:
                existing = db.query(FaceMatch).filter(FaceMatch.photo_id == pid, FaceMatch.user_id == user.id).first()
                if existing:
                    if score > int(existing.confidence_score or 0):
                        existing.confidence_score = score
                else:
                    db.add(FaceMatch(photo_id=pid, user_id=user.id, confidence_score=score))
                    count_matches += 1
            except Exception:
                # fallback: ajouter si problème de lecture
                db.add(FaceMatch(photo_id=pid, user_id=user.id, confidence_score=score))
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
            # Indexer les faces de la photo et rechercher des correspondances côté utilisateurs (selfies)
            # Utiliser les octets originaux (préparés) pour une meilleure empreinte faciale
            image_bytes = self._prepare_image_bytes(original_data)
            self.ensure_collection(event_id)
            self.ensure_event_users_indexed(event_id, db)
            face_ids = self._index_photo_faces_and_get_ids(event_id, photo.id, image_bytes)
            # Pour chaque FaceId indexé, rechercher des selfies correspondants (ExternalImageId user:{user_id})
            user_best: Dict[int, int] = {}
            for fid in face_ids:
                try:
                    resp = self.client.search_faces(
                        CollectionId=self._collection_id(event_id),
                        FaceId=fid,
                        MaxFaces=AWS_SEARCH_MAXFACES,
                        FaceMatchThreshold=self.search_threshold,
                    )
                except ClientError as e:
                    print(f"❌ AWS SearchFaces (photoFace->{photo.id}): {e}")
                    continue
                for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                    ext = (fm.get("Face") or {}).get("ExternalImageId") or ""
                    if not (ext.startswith("user:") or ext.isdigit()):
                        continue
                    try:
                        uid = int(ext.split(":", 1)[1]) if ext.startswith("user:") else int(ext)
                    except Exception:
                        continue
                    sim = int(float(fm.get("Similarity", 0.0)))
                    prev = user_best.get(uid)
                    if prev is None or sim > prev:
                        user_best[uid] = sim
            allowed_user_ids = self._get_allowed_event_user_ids(event_id, db)
            for uid, score in user_best.items():
                if uid in allowed_user_ids:
                    try:
                        existing = db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id, FaceMatch.user_id == uid).first()
                        if existing:
                            if int(score) > int(existing.confidence_score or 0):
                                existing.confidence_score = int(score)
                        else:
                            db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(score)))
                    except Exception:
                        db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(score)))
            # Réinitialiser l'expiration pour harmoniser (30 jours)
            try:
                from datetime import datetime, timedelta
                new_expiration = datetime.utcnow() + timedelta(days=30)
                db.query(Photo).filter(
                    Photo.event_id == event_id,
                    Photo.expires_at.isnot(None)
                ).update({
                    Photo.expires_at: new_expiration
                }, synchronize_session=False)
            except Exception:
                pass
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
        # Indexer les faces de la photo et rechercher des correspondances côté utilisateurs
        # Utiliser les octets originaux (préparés) pour une meilleure empreinte faciale
        image_bytes = self._prepare_image_bytes(original_data)
        self.ensure_collection(event_id)
        # IMPORTANT: indexer aussi les selfies des users de l'événement avant de matcher
        self.ensure_event_users_indexed(event_id, db)
        face_ids = self._index_photo_faces_and_get_ids(event_id, photo.id, image_bytes)
        user_best: Dict[int, int] = {}
        if not face_ids:
            # Si aucun visage détecté/indexé, tenter une recherche directe par image complète (fallback)
            resp = self._search_faces_by_image_retry(self._collection_id(event_id), image_bytes)
            if resp:
                for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                    ext = (fm.get("Face") or {}).get("ExternalImageId") or ""
                    if not (ext.startswith("user:") or ext.isdigit()):
                        continue
                    try:
                        uid = int(ext.split(":", 1)[1]) if ext.startswith("user:") else int(ext)
                    except Exception:
                        continue
                    sim = int(float(fm.get("Similarity", 0.0)))
                    prev = user_best.get(uid)
                    if prev is None or sim > prev:
                        user_best[uid] = sim
        if face_ids:
            coll_id = self._collection_id(event_id)
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_PER_REQUEST) as ex:
                futures = {ex.submit(self._search_faces_retry, coll_id, fid): fid for fid in face_ids}
                for fut in as_completed(futures):
                    resp = fut.result()
                    if not resp:
                        continue
                    for fm in resp.get("FaceMatches", [])[:AWS_SEARCH_MAXFACES]:
                        ext = (fm.get("Face") or {}).get("ExternalImageId") or ""
                        if not (ext.startswith("user:") or ext.isdigit()):
                            continue
                        try:
                            uid = int(ext.split(":", 1)[1]) if ext.startswith("user:") else int(ext)
                        except Exception:
                            continue
                        sim = int(float(fm.get("Similarity", 0.0)))
                        prev = user_best.get(uid)
                        if prev is None or sim > prev:
                            user_best[uid] = sim
        allowed_user_ids = self._get_allowed_event_user_ids(event_id, db)
        for uid, score in user_best.items():
            if uid in allowed_user_ids:
                try:
                    existing = db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id, FaceMatch.user_id == uid).first()
                    if existing:
                        if int(score) > int(existing.confidence_score or 0):
                            existing.confidence_score = int(score)
                    else:
                        db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(score)))
                except Exception:
                    db.add(FaceMatch(photo_id=photo.id, user_id=uid, confidence_score=int(score)))
        # Réinitialiser la date d'expiration de toutes les photos de l'événement (compte à rebours commun)
        try:
            from datetime import datetime, timedelta
            new_expiration = datetime.utcnow() + timedelta(days=30)
            db.query(Photo).filter(
                Photo.event_id == event_id,
                Photo.expires_at.isnot(None)
            ).update({
                Photo.expires_at: new_expiration
            }, synchronize_session=False)
        except Exception:
            pass
        db.commit()
        return photo


    def get_collection_snapshot(self, event_id: int) -> Dict:
        """Retourne un instantané de la collection Rekognition pour un événement.

        Structure:
        {
          "collection_id": str,
          "total_faces": int,
          "users": { user_id: { "count": int, "face_ids": [str, ...] } },
          "photos": { photo_id: { "count": int, "face_ids": [str, ...] } },
          "others": [ { "external_image_id": str, "face_id": str } ]
        }
        """
        coll_id = self._collection_id(event_id)
        try:
            self.ensure_collection(event_id)
        except Exception:
            # Si la collection n'existe pas et ne peut pas être créée, retourner vide
            return {
                "collection_id": coll_id,
                "total_faces": 0,
                "users": {},
                "photos": {},
                "others": []
            }

        users: Dict[str, Dict[str, object]] = {}
        photos: Dict[str, Dict[str, object]] = {}
        others: List[Dict[str, str]] = []
        total = 0

        next_token = None
        try:
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                aws_metrics.inc('ListFaces')
                resp = self.client.list_faces(**kwargs)
                for f in (resp.get('Faces') or []):
                    total += 1
                    face_id = f.get('FaceId') or ''
                    ext = (f.get('ExternalImageId') or '').strip()
                    if ext.startswith('user:'):
                        key = ext.split(':', 1)[1]
                        if key not in users:
                            users[key] = {"count": 0, "face_ids": []}
                        users[key]["count"] = int(users[key]["count"]) + 1
                        users[key]["face_ids"].append(face_id)
                    elif ext.startswith('photo:'):
                        key = ext.split(':', 1)[1]
                        if key not in photos:
                            photos[key] = {"count": 0, "face_ids": []}
                        photos[key]["count"] = int(photos[key]["count"]) + 1
                        photos[key]["face_ids"].append(face_id)
                    elif ext.isdigit():
                        # Legacy user id stocké en clair
                        key = ext
                        if key not in users:
                            users[key] = {"count": 0, "face_ids": []}
                        users[key]["count"] = int(users[key]["count"]) + 1
                        users[key]["face_ids"].append(face_id)
                    else:
                        others.append({"external_image_id": ext, "face_id": face_id})
                next_token = resp.get('NextToken')
                if not next_token:
                    break
        except ClientError as e:
            print(f"⚠️  list_faces error in snapshot: {e}")

        return {
            "collection_id": coll_id,
            "total_faces": total,
            "users": users,
            "photos": photos,
            "others": others,
        }

    def find_photo_matches_with_boxes(self, event_id: int, source_face_id: str, db: Session, limit: int = 10) -> List[Dict]:
        """Pour un FaceId donné (souvent un face utilisateur), retourne jusqu'à N photos
        correspondantes avec la bounding box exacte sur l'image originale.

        Retourne: [ { "photo_id": int, "face_id_photo": str, "similarity": int,
                       "box": {Left, Top, Width, Height} (normalisés 0..1) } ]
        """
        self.ensure_collection(event_id)
        coll_id = self._collection_id(event_id)

        # 1) Rechercher les matches du FaceId source
        try:
            resp = self._search_faces_retry(coll_id, source_face_id, max_faces=max(limit * 5, AWS_SEARCH_MAXFACES))
        except Exception:
            resp = None
        if not resp:
            return []

        # 2) Extraire les faces "photo:{pid}" avec leur FaceId et similarité
        photo_matches: List[Tuple[int, str, int]] = []  # (photo_id, photo_face_id, similarity)
        seen_photos: set[int] = set()
        for fm in resp.get("FaceMatches", []) or []:
            face = fm.get("Face") or {}
            ext = (face.get("ExternalImageId") or "").strip()
            if not ext.startswith("photo:"):
                continue
            try:
                pid = int(ext.split(":", 1)[1])
            except Exception:
                continue
            if pid in seen_photos:
                continue
            pfid = face.get("FaceId") or ""
            sim = int(float(fm.get("Similarity", 0.0)))
            photo_matches.append((pid, pfid, sim))
            seen_photos.add(pid)
            if len(photo_matches) >= limit:
                break

        if not photo_matches:
            return []

        # 3) Pour chaque photo, détecter les visages et identifier la box correspondant au photo_face_id
        results: List[Dict] = []
        for pid, pfid, sim in photo_matches:
            try:
                p = db.query(Photo).filter(Photo.id == pid).first()
                if not p:
                    continue
                # Charger bytes image
                photo_input = p.file_path if (getattr(p, 'file_path', None) and os.path.exists(p.file_path)) else p.photo_data
                if not photo_input:
                    continue
                img_bytes = self._prepare_image_bytes(photo_input)
                if not img_bytes:
                    continue
                # Détecter boxes (sur original) puis match par crop vers pfid
                boxes = self._detect_faces_boxes(img_bytes)
                if not boxes:
                    continue
                matching_box = None
                crops = self._crop_face_regions(img_bytes, boxes)
                for idx, crop_bytes in enumerate(crops):
                    r = self._search_faces_by_image_retry(coll_id, crop_bytes)
                    if not r:
                        continue
                    found = False
                    for m in r.get("FaceMatches", []) or []:
                        face = m.get("Face") or {}
                        if (face.get("FaceId") or "") == pfid:
                            found = True
                            break
                    if found:
                        bb = (boxes[idx].get('BoundingBox') or {})
                        matching_box = {
                            'Left': float(bb.get('Left', 0.0)),
                            'Top': float(bb.get('Top', 0.0)),
                            'Width': float(bb.get('Width', 0.0)),
                            'Height': float(bb.get('Height', 0.0)),
                        }
                        break
                if matching_box:
                    results.append({
                        'photo_id': pid,
                        'face_id_photo': pfid,
                        'similarity': sim,
                        'box': matching_box,
                    })
            except Exception as e:
                print(f"⚠️  find_photo_matches_with_boxes error for photo {pid}: {e}")
                continue

        return results

    def get_user_group_faces_with_boxes(self, event_id: int, user_id: int, db: Session, limit: Optional[int] = None) -> List[Dict]:
        """Retourne les photos associées à un utilisateur (via SearchFaces du selfie)
        avec la bounding box de la face photo correspondante (normalisée 0..1).

        Limit permet de restreindre le nombre de photos (None = toutes).
        """
        self.ensure_collection(event_id)
        # 1) Retrouver FaceId du selfie de l'utilisateur
        user_fid = self._find_user_face_id(event_id, user_id)
        if not user_fid:
            # tenter indexation rapide puis relecture
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                self.index_user_selfie(event_id, user)
                user_fid = self._find_user_face_id(event_id, user_id)
        if not user_fid:
            return []

        coll_id = self._collection_id(event_id)
        # 2) SearchFaces autour du selfie pour récupérer toutes les faces photo associées
        resp = self._search_faces_retry(coll_id, user_fid, max_faces=AWS_SELFIE_SEARCH_MAXFACES)
        if not resp:
            return []
        # Grouper par photo_id et garder la meilleure face (similarité max)
        best_for_photo: Dict[int, Tuple[str, float]] = {}  # pid -> (pfid, similarity_float)
        for fm in resp.get('FaceMatches', []) or []:
            face = fm.get('Face') or {}
            ext = (face.get('ExternalImageId') or '').strip()
            if not ext.startswith('photo:'):
                continue
            try:
                pid = int(ext.split(':', 1)[1])
            except Exception:
                continue
            # Filtrer par appartenance stricte à l'événement et existence en DB
            try:
                exists = db.query(Photo.id).filter(Photo.id == pid, Photo.event_id == event_id).first()
                if not exists:
                    continue
            except Exception:
                continue
            pfid = face.get('FaceId') or ''
            # Similarité float bornée [0,100]
            try:
                sim = float(fm.get('Similarity', 0.0))
            except Exception:
                sim = 0.0
            sim = max(0.0, min(100.0, sim))
            keep = best_for_photo.get(pid)
            if keep is None or sim > keep[1]:
                best_for_photo[pid] = (pfid, sim)

        if not best_for_photo:
            return []

        # 3) Construire un index FaceId -> BoundingBox par un passage sur ListFaces
        faceid_to_box: Dict[str, Dict[str, float]] = {}
        next_token = None
        try:
            while True:
                kwargs = {"CollectionId": coll_id, "MaxResults": 1000}
                if next_token:
                    kwargs["NextToken"] = next_token
                aws_metrics.inc('ListFaces')
                lf = self.client.list_faces(**kwargs)
                for f in (lf.get('Faces') or []):
                    ext = (f.get('ExternalImageId') or '').strip()
                    if not ext.startswith('photo:'):
                        continue
                    fid = f.get('FaceId')
                    bb = (f.get('BoundingBox') or {})
                    if fid and bb:
                        faceid_to_box[fid] = {
                            'Left': float(bb.get('Left', 0.0)),
                            'Top': float(bb.get('Top', 0.0)),
                            'Width': float(bb.get('Width', 0.0)),
                            'Height': float(bb.get('Height', 0.0)),
                        }
                next_token = lf.get('NextToken')
                if not next_token:
                    break
        except ClientError as e:
            print(f"⚠️  ListFaces error while building faceid_to_box: {e}")

        # 4) Assembler résultats en recalculant la box et la similarité via SearchFacesByImage (crop)
        pairs = list(best_for_photo.items())  # [(pid, (pfid, sim_float))]
        # Optionnel: limiter après tri par similarité
        pairs = sorted(pairs, key=lambda kv: -float(kv[1][1]))
        if isinstance(limit, int) and limit > 0:
            pairs = pairs[:limit]

        results: List[Dict] = []
        for pid, (pfid, _sim_from_searchfaces) in pairs:
            try:
                p = db.query(Photo).filter(Photo.id == pid).first()
                if not p:
                    continue
                if int(getattr(p, 'event_id', 0) or 0) != int(event_id):
                    continue
                photo_input = p.file_path if (getattr(p, 'file_path', None) and os.path.exists(p.file_path)) else p.photo_data
                if not photo_input:
                    continue
                img_bytes = self._prepare_image_bytes(photo_input)
                if not img_bytes:
                    continue
                boxes = self._detect_faces_boxes(img_bytes)
                if not boxes:
                    continue
                crops = self._crop_face_regions(img_bytes, boxes)
                found_idx = None
                sim_crop: Optional[float] = None
                for idx, crop_bytes in enumerate(crops):
                    r = self._search_faces_by_image_retry(coll_id, crop_bytes)
                    if not r:
                        continue
                    matched = False
                    for m in r.get('FaceMatches', []) or []:
                        face = m.get('Face') or {}
                        if (face.get('FaceId') or '') == pfid:
                            try:
                                sim_crop = float(m.get('Similarity', 0.0))
                            except Exception:
                                sim_crop = None
                            matched = True
                            break
                    if matched:
                        found_idx = idx
                        break
                if found_idx is None or found_idx < 0 or found_idx >= len(boxes):
                    continue
                bb = (boxes[found_idx].get('BoundingBox') or {})
                box = {
                    'Left': float(bb.get('Left', 0.0)),
                    'Top': float(bb.get('Top', 0.0)),
                    'Width': float(bb.get('Width', 0.0)),
                    'Height': float(bb.get('Height', 0.0)),
                }
                results.append({
                    'photo_id': pid,
                    # Afficher la similarité AWS entre le selfie et cette face (SearchFaces), pas la similarité du crop
                    'similarity': round(max(0.0, min(100.0, float(_sim_from_searchfaces or 0.0))), 2),
                    'box': box,
                })
            except Exception as e:
                print(f"⚠️  group box compute error pid={pid}: {e}")
                continue

        return results

    def build_snapshot_graph(self, event_id: int, db: Session, per_user_limit: int = 10) -> Dict:
        """Construit un snapshot visuel groupé par utilisateur pour un événement.

        Retourne:
        {
          "event_id": int,
          "users": [
            {
              "user_id": int,
              "selfie_available": bool,
              "faces": [ { "photo_id": int, "similarity": int, "box": {Left,Top,Width,Height} } ]
            }, ...
          ]
        }
        """
        self.ensure_collection(event_id)
        # Récupérer les utilisateurs de l'événement
        user_events = db.query(UserEvent).filter(UserEvent.event_id == event_id).all()
        user_ids = [ue.user_id for ue in user_events]
        # Statut selfie
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        selfie_map: Dict[int, bool] = {}
        for u in users:
            selfie_map[int(u.id)] = bool(getattr(u, 'selfie_data', None) or getattr(u, 'selfie_path', None))

        graph_users = []
        for uid in user_ids:
            try:
                faces = self.get_user_group_faces_with_boxes(event_id, uid, db, limit=per_user_limit)
            except Exception:
                faces = []
            graph_users.append({
                'user_id': int(uid),
                'selfie_available': bool(selfie_map.get(int(uid), False)),
                'faces': faces,
            })

        return {
            'event_id': int(event_id),
            'users': graph_users,
        }

    def compute_all_faces_similarity_to_user(self, event_id: int, user_id: int, db: Session,
                                             max_results_per_crop: int = 100) -> Dict:
        """Pour chaque visage détecté sur chaque photo de l'événement, calcule la similarité
        AWS Rekognition par rapport au selfie de l'utilisateur (s'il est indexé).

        Retour:
        {
          "event_id": int,
          "user_id": int,
          "photos": [
            { "photo_id": int, "faces": [ { "box": {Left,Top,Width,Height}, "similarity": float, "matched": bool } ] }
          ]
        }
        """
        self.ensure_collection(event_id)
        # S'assurer que le selfie est indexé et récupérer son FaceId
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            try:
                self.index_user_selfie(event_id, user)
            except Exception:
                pass
        user_fid = self._find_user_face_id(event_id, user_id)
        if not user_fid:
            return { 'event_id': int(event_id), 'user_id': int(user_id), 'photos': [] }

        coll_id = self._collection_id(event_id)
        # Parcourir toutes les photos de l'événement
        photos = db.query(Photo).filter(Photo.event_id == event_id).all()
        out_photos: List[Dict] = []
        for p in photos:
            try:
                photo_input = p.file_path if (getattr(p, 'file_path', None) and os.path.exists(p.file_path)) else p.photo_data
                if not photo_input:
                    continue
                img_bytes = self._prepare_image_bytes(photo_input)
                if not img_bytes:
                    continue
                boxes = self._detect_faces_boxes(img_bytes)
                if not boxes:
                    out_photos.append({ 'photo_id': int(p.id), 'faces': [] })
                    continue
                crops = self._crop_face_regions(img_bytes, boxes)
                faces_out: List[Dict] = []
                for idx, crop_bytes in enumerate(crops):
                    # Appel direct avec seuil 0 pour récupérer une similarité même faible
                    try:
                        aws_metrics.inc('SearchFacesByImage')
                        r = self.client.search_faces_by_image(
                            CollectionId=coll_id,
                            Image={"Bytes": crop_bytes},
                            MaxFaces=max_results_per_crop,
                            FaceMatchThreshold=0,
                            QualityFilter=AWS_SEARCH_QUALITY_FILTER,
                        )
                    except ClientError:
                        r = None
                    similarity_val: float = 0.0
                    matched = False
                    if r:
                        for m in r.get('FaceMatches', []) or []:
                            face = m.get('Face') or {}
                            if (face.get('FaceId') or '') == user_fid:
                                try:
                                    similarity_val = float(m.get('Similarity', 0.0))
                                except Exception:
                                    similarity_val = 0.0
                                matched = True
                                break
                    bb = (boxes[idx].get('BoundingBox') or {})
                    faces_out.append({
                        'box': {
                            'Left': float(bb.get('Left', 0.0)),
                            'Top': float(bb.get('Top', 0.0)),
                            'Width': float(bb.get('Width', 0.0)),
                            'Height': float(bb.get('Height', 0.0)),
                        },
                        'similarity': max(0.0, min(100.0, similarity_val)),
                        'matched': bool(matched),
                    })
                out_photos.append({ 'photo_id': int(p.id), 'faces': faces_out })
            except Exception:
                continue

        return { 'event_id': int(event_id), 'user_id': int(user_id), 'photos': out_photos }

