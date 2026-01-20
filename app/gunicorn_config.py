"""
Configuration Gunicorn optimisée pour tests de charge

Utilisation:
    gunicorn main:app -c gunicorn_config.py

Variables d'environnement:
    GUNICORN_WORKERS    : Nombre de workers (défaut: CPU * 2 + 1)
    PORT                : Port d'écoute (défaut: 8000)
"""
import multiprocessing
import os

# ========== WORKERS ==========
# OPTIMISÉ : 3 workers par défaut (stable avec semaphores dlib/face_recognition)
# Peut être augmenté à 4 si ressources suffisantes
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
worker_class = "uvicorn.workers.UvicornWorker"  # Async workers pour FastAPI
worker_connections = 1000
threads = int(os.getenv("GUNICORN_THREADS", "2")) # Threads par worker pour I/O parallèle

# Recycler les workers après N requêtes (évite les fuites mémoire)
max_requests = 1000
max_requests_jitter = 50  # Variabilité pour éviter les redémarrages simultanés

# Timeout (secondes)
timeout = 120  # 2 minutes pour les requêtes longues (upload photos)
graceful_timeout = 30  # Temps pour terminer les requêtes en cours lors du reload

# ========== CONNEXIONS ==========
keepalive = 5  # Garde les connexions ouvertes (réduit latence)
backlog = 2048  # File d'attente des connexions

# ========== LOGS ==========
accesslog = "-"  # Stdout
errorlog = "-"   # Stderr
loglevel = "info"  # debug, info, warning, error, critical

# ========== BIND ==========
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# ========== PERFORMANCE ==========
# Charge l'app avant de forker les workers (économise RAM)
preload_app = False

# ========== HOOKS ==========
def on_starting(server):
    """Callback au démarrage du serveur"""
    print("=" * 70)
    print("🚀 GUNICORN - CONFIGURATION")
    print("=" * 70)
    print(f"  Workers           : {workers}")
    print(f"  Worker class      : {worker_class}")
    print(f"  Threads/worker    : {threads}")
    print(f"  Worker connections: {worker_connections}")
    print(f"  Max requests      : {max_requests}")
    print(f"  Timeout           : {timeout}s")
    print(f"  Bind              : {bind}")
    print(f"  Preload app       : {preload_app}")
    print("=" * 70)
    print(f"📊 Capacité théorique : ~{workers * worker_connections} connexions simultanées")
    print("=" * 70)

def worker_exit(server, worker):
    """Callback lors de la sortie d'un worker"""
    print(f"⚠️  Worker {worker.pid} exited")
