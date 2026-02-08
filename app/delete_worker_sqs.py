"""
Worker SQS pour la suppression asynchrone des photos.

Ce module traite les jobs de suppression de photos en arrière-plan pour éviter
les timeouts HTTP lors de suppressions massives.

Architecture:
    1. L'endpoint de suppression crée un DeleteJob en DB (status=PENDING),
       puis envoie un message SQS avec {job_id, photographer_id}
    2. Ce worker consomme SQS en long polling
    3. Pour chaque job: récupère les photo_ids depuis DB, supprime par lots:
       - Face matches en DB
       - Faces dans Rekognition
       - Entrées Photo en DB
       - Objets S3 (batch delete)
    4. Si succès: status=DONE, si erreurs partielles: status=PARTIAL, 
       si échec total: status=FAILED
    5. Le message SQS est supprimé à la fin (même en cas d'erreur)

Robustesse:
    - Jobs en IN_PROGRESS sont repris au redémarrage du worker
    - Chaque photo est traitée individuellement (une erreur ne bloque pas les autres)
    - Logs détaillés pour le monitoring
    - S3 batch delete pour les performances

Usage:
    from delete_worker_sqs import start_delete_worker, stop_delete_worker
    
    # Au startup de l'app FastAPI
    start_delete_worker()
    
    # Au shutdown
    stop_delete_worker()
"""

import json
import time
import threading
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import and_

from settings import settings


# État global du worker
_delete_worker: Optional["DeleteWorkerSQS"] = None


class DeleteWorkerSQS:
    """
    Worker qui consomme les messages SQS et traite les jobs de suppression.
    Thread-safe et robuste aux redémarrages.
    """
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "total_jobs_processed": 0,
            "total_photos_deleted": 0,
            "total_errors": 0,
            "last_poll_at": None,
            "last_error": None,
            "current_job_id": None,
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
        if not settings.is_delete_sqs_configured:
            print("[DeleteWorkerSQS] SQS not configured, worker disabled")
            print(f"[DeleteWorkerSQS]   DELETE_SQS_QUEUE_URL={settings.DELETE_SQS_QUEUE_URL}")
            print(f"[DeleteWorkerSQS]   PHOTO_SQS_QUEUE_URL={settings.PHOTO_SQS_QUEUE_URL}")
            return
        
        if not settings.DELETE_WORKER_ENABLED:
            print("[DeleteWorkerSQS] Worker disabled via DELETE_WORKER_ENABLED=false")
            return
        
        if self._running:
            print("[DeleteWorkerSQS] Worker already running")
            return
        
        # Reprendre les jobs en cours (interrompus par un redémarrage)
        self._recover_pending_jobs()
        
        self._running = True
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="DeleteWorkerSQS",
            daemon=True
        )
        self._thread.start()
        print(f"[DeleteWorkerSQS] Worker started (queue={settings.delete_sqs_queue_url})")
    
    def stop(self, timeout: float = 30.0):
        """Arrête proprement le worker."""
        if not self._running:
            return
        
        print("[DeleteWorkerSQS] Stopping worker...")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        
        self._thread = None
        print("[DeleteWorkerSQS] Worker stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du worker."""
        with self._stats_lock:
            return {**self._stats, "running": self._running}
    
    def _recover_pending_jobs(self):
        """Reprend les jobs interrompus (status=IN_PROGRESS ou PENDING)."""
        from database import SessionLocal
        from models import DeleteJob, DeleteJobStatus
        
        db = SessionLocal()
        try:
            # Chercher les jobs non terminés
            pending_jobs = db.query(DeleteJob).filter(
                DeleteJob.status.in_([
                    DeleteJobStatus.PENDING.value,
                    DeleteJobStatus.IN_PROGRESS.value
                ])
            ).all()
            
            if pending_jobs:
                print(f"[DeleteWorkerSQS] Found {len(pending_jobs)} pending jobs to recover")
                for job in pending_jobs:
                    # Remettre en PENDING pour retraitement
                    job.status = DeleteJobStatus.PENDING.value
                    print(f"[DeleteWorkerSQS]   Recovering job_id={job.job_id}")
                db.commit()
        except Exception as e:
            print(f"[DeleteWorkerSQS] Error recovering pending jobs: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _worker_loop(self):
        """Boucle principale du worker."""
        print(f"[DeleteWorkerSQS] Worker loop started")
        
        while self._running:
            try:
                self._poll_and_process()
            except Exception as e:
                with self._stats_lock:
                    self._stats["last_error"] = f"{type(e).__name__}: {str(e)}"
                print(f"[DeleteWorkerSQS] Error in worker loop: {e}")
                traceback.print_exc()
                # Attendre avant de réessayer
                time.sleep(5.0)
        
        print(f"[DeleteWorkerSQS] Worker loop ended")
    
    def _poll_and_process(self):
        """Effectue un poll SQS et traite les messages reçus."""
        try:
            with self._stats_lock:
                self._stats["last_poll_at"] = time.time()
            
            # Long polling SQS
            response = self.sqs_client.receive_message(
                QueueUrl=settings.delete_sqs_queue_url,
                MaxNumberOfMessages=1,  # Un job à la fois
                WaitTimeSeconds=settings.PHOTO_SQS_WAIT_TIME_SECONDS,
                VisibilityTimeout=settings.DELETE_SQS_VISIBILITY_TIMEOUT,
                MessageAttributeNames=["All"],
            )
            
            messages = response.get("Messages", [])
            
            if not messages:
                # Aucun message, vérifier les jobs PENDING en DB (recovery)
                self._process_pending_jobs_from_db()
                time.sleep(settings.PHOTO_WORKER_POLL_INTERVAL)
                return
            
            for message in messages:
                if not self._running:
                    break
                
                self._process_message(message)
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in {"AWS.SimpleQueueService.NonExistentQueue"}:
                print(f"[DeleteWorkerSQS] Queue does not exist: {settings.delete_sqs_queue_url}")
                time.sleep(60.0)  # Attendre longtemps si la queue n'existe pas
            else:
                raise
    
    def _process_pending_jobs_from_db(self):
        """Traite les jobs PENDING qui n'ont pas de message SQS (recovery)."""
        from database import SessionLocal
        from models import DeleteJob, DeleteJobStatus
        
        db = SessionLocal()
        try:
            pending_job = db.query(DeleteJob).filter(
                DeleteJob.status == DeleteJobStatus.PENDING.value
            ).order_by(DeleteJob.created_at.asc()).first()
            
            if pending_job:
                print(f"[DeleteWorkerSQS] Processing pending job from DB: {pending_job.job_id}")
                self._process_delete_job(pending_job.job_id)
        except Exception as e:
            print(f"[DeleteWorkerSQS] Error processing pending jobs from DB: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _process_message(self, message: Dict):
        """Traite un message SQS individuel."""
        receipt_handle = message.get("ReceiptHandle")
        message_id = message.get("MessageId", "unknown")
        
        try:
            # Parser le corps du message
            body = json.loads(message.get("Body", "{}"))
            job_type = body.get("job_type")
            job_id = body.get("job_id")
            
            # Ignorer les messages qui ne sont pas des jobs de suppression
            if job_type != "delete_photos":
                print(f"[DeleteWorkerSQS] Ignoring message {message_id}: job_type={job_type}")
                # Ne pas supprimer, laisser l'autre worker le traiter
                return
            
            if not job_id:
                print(f"[DeleteWorkerSQS] Invalid message {message_id}: missing job_id")
                self._delete_message(receipt_handle)
                return
            
            print(f"[DeleteWorkerSQS] Processing delete job_id={job_id}")
            
            # Traiter le job
            self._process_delete_job(job_id)
            
            # Supprimer le message SQS (même en cas d'erreur, le job est géré en DB)
            self._delete_message(receipt_handle)
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[DeleteWorkerSQS] Error processing message {message_id}: {error_msg}")
            traceback.print_exc()
            
            # Supprimer le message pour éviter une boucle infinie
            # Les erreurs sont gérées dans le job en DB
            try:
                self._delete_message(receipt_handle)
            except Exception:
                pass
    
    def _process_delete_job(self, job_id: str):
        """Traite un job de suppression complet."""
        from database import SessionLocal
        from models import DeleteJob, DeleteJobStatus, Photo, FaceMatch
        
        start_time = time.time()
        db = SessionLocal()
        
        try:
            # Récupérer le job
            job = db.query(DeleteJob).filter(DeleteJob.job_id == job_id).first()
            if not job:
                print(f"[DeleteWorkerSQS] Job not found: {job_id}")
                return
            
            # Vérifier si déjà terminé
            if job.status in [DeleteJobStatus.DONE.value, DeleteJobStatus.PARTIAL.value]:
                print(f"[DeleteWorkerSQS] Job already completed: {job_id} (status={job.status})")
                return
            
            with self._stats_lock:
                self._stats["current_job_id"] = job_id
            
            # Mettre à jour le statut: IN_PROGRESS
            job.status = DeleteJobStatus.IN_PROGRESS.value
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Parser les photo_ids
            photo_ids = json.loads(job.photo_ids_json)
            total = len(photo_ids)
            
            print(f"[DELETE-JOB] job_id={job_id} starting deletion of {total} photos")
            
            # Traiter par lots
            batch_size = settings.DELETE_BATCH_SIZE
            success_count = 0
            error_count = 0
            errors = []
            s3_keys_to_delete = []
            
            for i in range(0, total, batch_size):
                if not self._running:
                    print(f"[DELETE-JOB] job_id={job_id} interrupted by shutdown")
                    break
                
                batch = photo_ids[i:i+batch_size]
                print(f"[DELETE-JOB] job_id={job_id} processing batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
                
                for photo_id in batch:
                    try:
                        # Récupérer la photo
                        photo = db.query(Photo).filter(Photo.id == photo_id).first()
                        if not photo:
                            print(f"[DELETE-JOB]   photo_id={photo_id} not found, skipping")
                            success_count += 1  # Considéré comme succès (déjà supprimée)
                            continue
                        
                        # 1. Supprimer les face_matches
                        fm_count = db.query(FaceMatch).filter(FaceMatch.photo_id == photo_id).delete()
                        if fm_count > 0:
                            print(f"[DELETE-JOB]   photo_id={photo_id} deleted {fm_count} face_matches")
                        
                        # 2. Supprimer dans Rekognition (si applicable)
                        self._delete_from_rekognition(photo, db)
                        
                        # 3. Collecter la clé S3 pour suppression batch
                        if photo.s3_key:
                            s3_keys_to_delete.append(photo.s3_key)
                        
                        # 4. Supprimer de la DB
                        db.delete(photo)
                        success_count += 1
                        
                        print(f"[DELETE-PHOTO] photo_id={photo_id} deleted successfully")
                    
                    except Exception as e:
                        error_msg = f"photo_id={photo_id}: {type(e).__name__}: {str(e)}"
                        print(f"[DELETE-JOB]   ERROR: {error_msg}")
                        errors.append({"photo_id": photo_id, "error": str(e)})
                        error_count += 1
                        # Continuer avec les autres photos
                
                # Commit par batch
                try:
                    db.commit()
                except Exception as e:
                    print(f"[DELETE-JOB]   Commit failed: {e}")
                    db.rollback()
                
                # Mise à jour du job
                job.processed_count = success_count + error_count
                job.success_count = success_count
                job.error_count = error_count
                if errors:
                    job.errors_json = json.dumps(errors[-50:])  # Garder les 50 dernières erreurs
                db.commit()
            
            # 5. Suppression S3 batch
            if s3_keys_to_delete:
                print(f"[DELETE-JOB] job_id={job_id} deleting {len(s3_keys_to_delete)} S3 objects")
                try:
                    from s3_service import get_s3_service
                    s3 = get_s3_service()
                    s3_result = s3.delete_photos_batch(s3_keys_to_delete)
                    deleted_s3 = len(s3_result.get("deleted", []))
                    s3_errors = s3_result.get("errors", [])
                    print(f"[DELETE-JOB]   S3 batch delete: {deleted_s3} deleted, {len(s3_errors)} errors")
                    
                    if s3_errors:
                        for err in s3_errors[:5]:  # Log les 5 premières erreurs
                            errors.append({"s3_key": err.get("key"), "error": err.get("error")})
                            print(f"[DELETE-JOB]   S3 error: {err}")
                except Exception as e:
                    print(f"[DELETE-JOB]   S3 batch delete failed: {e}")
                    errors.append({"s3_batch": str(e)})
            
            # Finaliser le job
            duration = time.time() - start_time
            
            if error_count == 0:
                job.status = DeleteJobStatus.DONE.value
            elif success_count > 0:
                job.status = DeleteJobStatus.PARTIAL.value
            else:
                job.status = DeleteJobStatus.FAILED.value
            
            job.completed_at = datetime.utcnow()
            job.duration_seconds = duration
            job.success_count = success_count
            job.error_count = error_count
            if errors:
                job.errors_json = json.dumps(errors[-100:])  # Garder les 100 dernières
            db.commit()
            
            with self._stats_lock:
                self._stats["total_jobs_processed"] += 1
                self._stats["total_photos_deleted"] += success_count
                self._stats["total_errors"] += error_count
                self._stats["current_job_id"] = None
            
            print(f"[PERF][delete_job] job_id={job_id} completed in {duration:.2f}s: {success_count} deleted, {error_count} errors, status={job.status}")
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[DELETE-JOB] job_id={job_id} FAILED: {error_msg}")
            traceback.print_exc()
            
            try:
                job = db.query(DeleteJob).filter(DeleteJob.job_id == job_id).first()
                if job:
                    job.status = DeleteJobStatus.FAILED.value
                    job.errors_json = json.dumps([{"fatal": error_msg}])
                    job.completed_at = datetime.utcnow()
                    job.duration_seconds = time.time() - start_time
                    db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
            
            with self._stats_lock:
                self._stats["last_error"] = error_msg
                self._stats["current_job_id"] = None
        
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _delete_from_rekognition(self, photo, db):
        """Supprime les faces d'une photo dans Rekognition."""
        try:
            if photo.event_id is None:
                return
            
            from recognizer_factory import get_face_recognizer
            from aws_face_recognizer import AwsFaceRecognizer as _Aws
            
            face_recognizer = get_face_recognizer()
            
            if isinstance(face_recognizer, _Aws):
                try:
                    face_recognizer.ensure_collection(int(photo.event_id))
                except Exception:
                    pass
                try:
                    face_recognizer._delete_photo_faces(int(photo.event_id), int(photo.id))
                    print(f"[DELETE-JOB]   photo_id={photo.id} rekognition faces deleted")
                except Exception as e:
                    print(f"[DELETE-JOB]   photo_id={photo.id} rekognition delete failed: {e}")
        except Exception as e:
            print(f"[DELETE-JOB]   rekognition cleanup failed: {e}")
    
    def _delete_message(self, receipt_handle: str):
        """Supprime un message de la file SQS."""
        try:
            self.sqs_client.delete_message(
                QueueUrl=settings.delete_sqs_queue_url,
                ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            print(f"[DeleteWorkerSQS] Failed to delete message: {e}")


# ========== API publique ==========

def get_delete_worker() -> DeleteWorkerSQS:
    """Retourne l'instance singleton du worker."""
    global _delete_worker
    if _delete_worker is None:
        _delete_worker = DeleteWorkerSQS()
    return _delete_worker


def start_delete_worker():
    """Démarre le worker SQS (à appeler au startup de l'app)."""
    worker = get_delete_worker()
    worker.start()


def stop_delete_worker():
    """Arrête le worker SQS (à appeler au shutdown de l'app)."""
    global _delete_worker
    if _delete_worker is not None:
        _delete_worker.stop()
        _delete_worker = None


def get_delete_worker_stats() -> Dict[str, Any]:
    """Retourne les statistiques du worker."""
    worker = get_delete_worker()
    return worker.get_stats()
