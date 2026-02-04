"""
Worker SQS pour le traitement asynchrone des photos.

Ce module remplace la PhotoQueue en mémoire par un système robuste basé sur SQS.
Les jobs ne sont plus perdus lors des redémarrages de workers ou d'instances.

Architecture:
    1. L'endpoint d'upload crée une Photo en DB (status=PENDING), upload vers S3, 
       puis envoie un message dans SQS avec {photo_id, event_id, s3_key}
    2. Ce worker consomme SQS en long polling
    3. Pour chaque message: récupère l'image depuis S3, traite la reconnaissance faciale,
       met à jour la DB (status=DONE ou FAILED)
    4. Si succès: supprime le message SQS. Si échec: laisse le message pour retry/DLQ.

Usage:
    from photo_worker_sqs import start_photo_worker, stop_photo_worker
    
    # Au startup de l'app FastAPI
    start_photo_worker()
    
    # Au shutdown
    stop_photo_worker()
"""

import os
import json
import time
import threading
import traceback
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError

from settings import settings


# État global du worker
_worker_thread: Optional[threading.Thread] = None
_worker_running: bool = False
_worker_lock = threading.Lock()


class PhotoWorkerSQS:
    """
    Worker qui consomme les messages SQS et traite les photos.
    Thread-safe et robuste aux redémarrages.
    """
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "total_processed": 0,
            "total_failed": 0,
            "total_received": 0,
            "last_poll_at": None,
            "last_error": None,
        }
        self._stats_lock = threading.Lock()
        
        # Clients AWS (créés à la demande)
        self._sqs_client = None
        self._s3_client = None
    
    @property
    def sqs_client(self):
        if self._sqs_client is None:
            self._sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)
        return self._sqs_client
    
    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        return self._s3_client
    
    def start(self):
        """Démarre le worker dans un thread daemon."""
        if not settings.is_sqs_configured:
            print("[PhotoWorkerSQS] SQS not configured, worker disabled")
            print(f"[PhotoWorkerSQS]   PHOTO_BUCKET_NAME={settings.PHOTO_BUCKET_NAME}")
            print(f"[PhotoWorkerSQS]   PHOTO_SQS_QUEUE_URL={settings.PHOTO_SQS_QUEUE_URL}")
            return
        
        if not settings.PHOTO_WORKER_ENABLED:
            print("[PhotoWorkerSQS] Worker disabled via PHOTO_WORKER_ENABLED=false")
            return
        
        if self._running:
            print("[PhotoWorkerSQS] Worker already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="PhotoWorkerSQS",
            daemon=True
        )
        self._thread.start()
        print(f"[PhotoWorkerSQS] Worker started (queue={settings.PHOTO_SQS_QUEUE_URL})")
    
    def stop(self, timeout: float = 30.0):
        """Arrête proprement le worker."""
        if not self._running:
            return
        
        print("[PhotoWorkerSQS] Stopping worker...")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        
        self._thread = None
        print("[PhotoWorkerSQS] Worker stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du worker."""
        with self._stats_lock:
            return {**self._stats, "running": self._running}
    
    def _worker_loop(self):
        """Boucle principale du worker."""
        print(f"[PhotoWorkerSQS] Worker loop started")
        
        while self._running:
            try:
                self._poll_and_process()
            except Exception as e:
                with self._stats_lock:
                    self._stats["last_error"] = f"{type(e).__name__}: {str(e)}"
                print(f"[PhotoWorkerSQS] Error in worker loop: {e}")
                traceback.print_exc()
                # Attendre avant de réessayer
                time.sleep(5.0)
        
        print(f"[PhotoWorkerSQS] Worker loop ended")
    
    def _poll_and_process(self):
        """Effectue un poll SQS et traite les messages reçus."""
        try:
            with self._stats_lock:
                self._stats["last_poll_at"] = time.time()
            
            # Long polling SQS
            response = self.sqs_client.receive_message(
                QueueUrl=settings.PHOTO_SQS_QUEUE_URL,
                MaxNumberOfMessages=settings.PHOTO_SQS_MAX_MESSAGES,
                WaitTimeSeconds=settings.PHOTO_SQS_WAIT_TIME_SECONDS,
                VisibilityTimeout=settings.PHOTO_SQS_VISIBILITY_TIMEOUT,
                MessageAttributeNames=["All"],
            )
            
            messages = response.get("Messages", [])
            
            if not messages:
                # Aucun message, attendre un peu avant le prochain poll
                time.sleep(settings.PHOTO_WORKER_POLL_INTERVAL)
                return
            
            with self._stats_lock:
                self._stats["total_received"] += len(messages)
            
            for message in messages:
                if not self._running:
                    break
                
                self._process_message(message)
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in {"AWS.SimpleQueueService.NonExistentQueue"}:
                print(f"[PhotoWorkerSQS] Queue does not exist: {settings.PHOTO_SQS_QUEUE_URL}")
                time.sleep(60.0)  # Attendre longtemps si la queue n'existe pas
            else:
                raise
    
    def _process_message(self, message: Dict):
        """Traite un message SQS individuel."""
        receipt_handle = message.get("ReceiptHandle")
        message_id = message.get("MessageId", "unknown")
        
        try:
            # Parser le corps du message
            body = json.loads(message.get("Body", "{}"))
            photo_id = body.get("photo_id")
            event_id = body.get("event_id")
            s3_key = body.get("s3_key")
            
            if not all([photo_id, event_id, s3_key]):
                print(f"[PhotoWorkerSQS] Invalid message {message_id}: missing required fields")
                print(f"[PhotoWorkerSQS]   body={body}")
                # Supprimer le message malformé pour éviter une boucle infinie
                self._delete_message(receipt_handle)
                return
            
            print(f"[PhotoWorkerSQS] Processing photo_id={photo_id} event_id={event_id} s3_key={s3_key}")
            
            # Mettre à jour le statut en DB: PROCESSING
            self._update_photo_status(photo_id, "PROCESSING")
            
            # Récupérer l'image depuis S3
            image_bytes = self._download_from_s3(s3_key)
            
            if not image_bytes:
                raise ValueError(f"Failed to download image from S3: {s3_key}")
            
            print(f"[PhotoWorkerSQS] Downloaded {len(image_bytes)} bytes from S3")
            
            # Traiter la photo avec reconnaissance faciale
            self._process_photo(photo_id, event_id, image_bytes)
            
            # Succès: mettre à jour le statut et supprimer le message SQS
            self._update_photo_status(photo_id, "DONE")
            self._delete_message(receipt_handle)
            
            with self._stats_lock:
                self._stats["total_processed"] += 1
            
            print(f"[PhotoWorkerSQS] Successfully processed photo_id={photo_id}")
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[PhotoWorkerSQS] Error processing message {message_id}: {error_msg}")
            traceback.print_exc()
            
            with self._stats_lock:
                self._stats["total_failed"] += 1
                self._stats["last_error"] = error_msg
            
            # Mettre à jour le statut en DB: FAILED avec le message d'erreur
            try:
                body = json.loads(message.get("Body", "{}"))
                photo_id = body.get("photo_id")
                if photo_id:
                    self._update_photo_status(photo_id, "FAILED", error_msg)
            except Exception:
                pass
            
            # NE PAS supprimer le message SQS en cas d'échec
            # Il sera retenté après le VisibilityTimeout ou envoyé en DLQ
    
    def _download_from_s3(self, s3_key: str) -> Optional[bytes]:
        """Télécharge un fichier depuis S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=settings.PHOTO_BUCKET_NAME,
                Key=s3_key
            )
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                print(f"[PhotoWorkerSQS] S3 object not found: {s3_key}")
            else:
                print(f"[PhotoWorkerSQS] S3 error: {e}")
            return None
    
    def _process_photo(self, photo_id: int, event_id: int, image_bytes: bytes):
        """Traite une photo avec reconnaissance faciale."""
        from database import SessionLocal
        from recognizer_factory import get_face_recognizer
        
        db = SessionLocal()
        try:
            face_recognizer = get_face_recognizer()
            
            # Utiliser la nouvelle méthode qui travaille avec des bytes
            face_recognizer.process_photo_from_bytes(
                photo_id=photo_id,
                image_bytes=image_bytes,
                event_id=event_id,
                db=db
            )
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _update_photo_status(self, photo_id: int, status: str, error_message: str = None):
        """Met à jour le statut d'une photo en DB."""
        from database import SessionLocal
        from models import Photo
        
        db = SessionLocal()
        try:
            photo = db.query(Photo).filter(Photo.id == photo_id).first()
            if photo:
                photo.processing_status = status
                if error_message:
                    photo.error_message = error_message[:2000]  # Limiter la taille
                db.commit()
        except Exception as e:
            print(f"[PhotoWorkerSQS] Failed to update photo status: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _delete_message(self, receipt_handle: str):
        """Supprime un message de la file SQS."""
        try:
            self.sqs_client.delete_message(
                QueueUrl=settings.PHOTO_SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            print(f"[PhotoWorkerSQS] Failed to delete message: {e}")


# Instance singleton du worker
_photo_worker: Optional[PhotoWorkerSQS] = None


def get_photo_worker() -> PhotoWorkerSQS:
    """Retourne l'instance singleton du worker."""
    global _photo_worker
    if _photo_worker is None:
        _photo_worker = PhotoWorkerSQS()
    return _photo_worker


def start_photo_worker():
    """Démarre le worker SQS (à appeler au startup de l'app)."""
    worker = get_photo_worker()
    worker.start()


def stop_photo_worker():
    """Arrête le worker SQS (à appeler au shutdown de l'app)."""
    global _photo_worker
    if _photo_worker is not None:
        _photo_worker.stop()
        _photo_worker = None


def get_worker_stats() -> Dict[str, Any]:
    """Retourne les statistiques du worker."""
    worker = get_photo_worker()
    return worker.get_stats()
