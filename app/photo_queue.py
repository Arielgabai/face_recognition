"""
Système de queue asynchrone pour le traitement des photos.
Permet de découpler l'upload des photos du traitement de reconnaissance faciale.
"""
import os
import time
import threading
import queue
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import traceback
from sqlalchemy.orm import Session
from database import SessionLocal

# Configuration
QUEUE_MAX_SIZE = int(os.environ.get("PHOTO_QUEUE_MAX_SIZE", "1000"))
MAX_WORKERS = int(os.environ.get("PHOTO_QUEUE_WORKERS", "3"))  # Nombre de workers parallèles
WORKER_BATCH_SIZE = int(os.environ.get("PHOTO_QUEUE_BATCH_SIZE", "5"))  # Photos traitées par batch


@dataclass
class PhotoJob:
    """Représente un job de traitement de photo."""
    job_id: str
    event_id: int
    photographer_id: int
    temp_path: str
    filename: str
    original_filename: str
    watcher_id: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3


class PhotoQueue:
    """
    Queue thread-safe pour gérer le traitement asynchrone des photos.
    Implémente un pattern producer-consumer avec plusieurs workers.
    """
    
    def __init__(self):
        self._queue = queue.Queue(maxsize=QUEUE_MAX_SIZE)
        self._jobs: Dict[str, PhotoJob] = {}  # job_id -> PhotoJob
        self._jobs_lock = threading.Lock()
        self._workers: List[threading.Thread] = []
        self._running = False
        self._stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "current_queue_size": 0,
            "workers_active": 0,
        }
        self._stats_lock = threading.Lock()
        
    def start(self, num_workers: int = MAX_WORKERS):
        """Démarre les workers de traitement."""
        if self._running:
            return
        
        self._running = True
        print(f"[PhotoQueue] Starting {num_workers} workers...")
        
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"PhotoWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        print(f"[PhotoQueue] {num_workers} workers started")
    
    def stop(self, timeout: float = 30.0):
        """Arrête proprement les workers."""
        if not self._running:
            return
        
        print("[PhotoQueue] Stopping workers...")
        self._running = False
        
        # Envoyer des sentinelles pour débloquer les workers
        for _ in self._workers:
            try:
                self._queue.put(None, timeout=1)
            except queue.Full:
                pass
        
        # Attendre que les workers se terminent
        for worker in self._workers:
            worker.join(timeout=timeout)
        
        self._workers.clear()
        print("[PhotoQueue] Workers stopped")
    
    def enqueue(self, job: PhotoJob) -> bool:
        """
        Ajoute un job à la queue.
        Retourne True si succès, False si la queue est pleine.
        """
        try:
            self._queue.put(job, block=False)
            
            with self._jobs_lock:
                self._jobs[job.job_id] = job
            
            with self._stats_lock:
                self._stats["total_enqueued"] += 1
                self._stats["current_queue_size"] = self._queue.qsize()
            
            print(f"[PhotoQueue] Job {job.job_id} enqueued (queue size: {self._queue.qsize()})")
            return True
            
        except queue.Full:
            print(f"[PhotoQueue] Queue is full, cannot enqueue job {job.job_id}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un job."""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            
            return {
                "job_id": job.job_id,
                "event_id": job.event_id,
                "filename": job.original_filename,
                "status": job.status,
                "error": job.error,
                "attempts": job.attempts,
                "created_at": job.created_at,
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la queue."""
        with self._stats_lock:
            return {
                **self._stats,
                "current_queue_size": self._queue.qsize(),
                "total_jobs": len(self._jobs),
            }
    
    def _worker_loop(self):
        """Boucle principale d'un worker."""
        print(f"[{threading.current_thread().name}] Worker started")
        
        while self._running:
            try:
                # Récupérer un job avec timeout pour pouvoir vérifier _running régulièrement
                job = self._queue.get(timeout=1.0)
                
                # Sentinel pour arrêt propre
                if job is None:
                    break
                
                # Traiter le job
                with self._stats_lock:
                    self._stats["workers_active"] += 1
                
                try:
                    self._process_job(job)
                finally:
                    with self._stats_lock:
                        self._stats["workers_active"] -= 1
                        self._stats["current_queue_size"] = self._queue.qsize()
                    
                    self._queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[{threading.current_thread().name}] Unexpected error: {e}")
                traceback.print_exc()
        
        print(f"[{threading.current_thread().name}] Worker stopped")
    
    def _process_job(self, job: PhotoJob):
        """Traite un job de photo."""
        print(f"[{threading.current_thread().name}] Processing job {job.job_id}: {job.original_filename}")
        
        # Mettre à jour le statut
        job.status = "processing"
        job.attempts += 1
        
        db = None
        try:
            # Créer une session DB pour ce worker
            db = SessionLocal()
            
            # Importer ici pour éviter les imports circulaires
            from recognizer_factory import get_face_recognizer
            from models import LocalIngestionLog
            
            face_recognizer = get_face_recognizer()
            
            # Traiter la photo
            photo = face_recognizer.process_and_save_photo_for_event(
                job.temp_path,
                job.filename,
                job.photographer_id,
                job.event_id,
                db
            )
            
            # Logger l'ingestion si watcher_id présent
            if job.watcher_id is not None:
                try:
                    db.add(LocalIngestionLog(
                        watcher_id=job.watcher_id,
                        event_id=job.event_id,
                        file_name=job.original_filename,
                        status="ingested",
                    ))
                    db.commit()
                except Exception as e:
                    print(f"[PhotoQueue] Warning: could not log ingestion: {e}")
            
            # Succès
            job.status = "completed"
            
            with self._stats_lock:
                self._stats["total_processed"] += 1
            
            print(f"[{threading.current_thread().name}] Job {job.job_id} completed: {photo.filename}")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[{threading.current_thread().name}] Job {job.job_id} failed: {error_msg}")
            traceback.print_exc()
            
            job.error = error_msg
            
            # Réessayer si pas trop de tentatives
            if job.attempts < job.max_attempts:
                job.status = "pending"
                print(f"[{threading.current_thread().name}] Job {job.job_id} will be retried (attempt {job.attempts}/{job.max_attempts})")
                # Remettre en queue avec un délai
                threading.Timer(5.0, lambda: self._requeue_job(job)).start()
            else:
                job.status = "failed"
                with self._stats_lock:
                    self._stats["total_failed"] += 1
                
                # Logger l'échec si watcher_id présent
                if job.watcher_id is not None and db is not None:
                    try:
                        from models import LocalIngestionLog
                        db.add(LocalIngestionLog(
                            watcher_id=job.watcher_id,
                            event_id=job.event_id,
                            file_name=job.original_filename,
                            status="failed",
                            error=error_msg,
                        ))
                        db.commit()
                    except Exception:
                        pass
        
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(job.temp_path):
                try:
                    os.remove(job.temp_path)
                    print(f"[{threading.current_thread().name}] Cleaned up temp file: {job.temp_path}")
                except Exception as e:
                    print(f"[{threading.current_thread().name}] Could not remove temp file {job.temp_path}: {e}")
            
            # Fermer la session DB
            if db:
                try:
                    db.close()
                except Exception:
                    pass
            
            # Libérer la mémoire
            try:
                import gc
                gc.collect()
            except Exception:
                pass
    
    def _requeue_job(self, job: PhotoJob):
        """Remet un job en queue après un délai."""
        try:
            self._queue.put(job, block=False)
            print(f"[PhotoQueue] Job {job.job_id} requeued")
        except queue.Full:
            print(f"[PhotoQueue] Could not requeue job {job.job_id}: queue full")
            job.status = "failed"
            job.error = "Queue full during retry"
            with self._stats_lock:
                self._stats["total_failed"] += 1


# Instance globale singleton
_photo_queue: Optional[PhotoQueue] = None


def get_photo_queue() -> PhotoQueue:
    """Récupère l'instance globale de la queue (singleton)."""
    global _photo_queue
    if _photo_queue is None:
        _photo_queue = PhotoQueue()
        _photo_queue.start()
    return _photo_queue


def shutdown_photo_queue():
    """Arrête proprement la queue (à appeler au shutdown de l'app)."""
    global _photo_queue
    if _photo_queue is not None:
        _photo_queue.stop()
        _photo_queue = None

