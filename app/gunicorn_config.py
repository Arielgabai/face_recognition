"""
Configuration Gunicorn optimisée pour AWS App Runner

Utilisation:
    gunicorn main:app -c gunicorn_config.py

Variables d'environnement:
    GUNICORN_WORKERS      : Nombre de workers (défaut: 1 pour App Runner)
    GUNICORN_MAX_REQUESTS : Nombre de requêtes avant recyclage (défaut: 0 = désactivé)
    PORT                  : Port d'écoute (défaut: 8000)

IMPORTANT pour AWS App Runner:
    - Avec le nouveau workflow S3+SQS, les jobs ne sont plus perdus lors des redémarrages
    - On peut donc utiliser max_requests > 0 si besoin (pour les fuites mémoire)
    - Ou le désactiver (max_requests = 0) pour éviter les interruptions
"""
import multiprocessing
import os

# ========== WORKERS ==========
# Pour App Runner avec le nouveau workflow S3+SQS:
# - 1 worker suffit généralement (le traitement lourd est fait par le worker SQS en arrière-plan)
# - On peut augmenter à 2-3 si le trafic HTTP est important
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = "uvicorn.workers.UvicornWorker"  # Async workers pour FastAPI
worker_connections = 1000
threads = int(os.getenv("GUNICORN_THREADS", "2"))  # Threads par worker pour I/O parallèle

# Recyclage des workers:
# - Avec S3+SQS: on peut mettre max_requests > 0 car les jobs ne sont plus perdus
# - Par défaut: désactivé (0) pour éviter les interruptions inutiles
# - Activer si vous observez des fuites mémoire (ex: 500-1000)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = 50 if max_requests > 0 else 0  # Variabilité seulement si recyclage actif

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
    print("🚀 GUNICORN - CONFIGURATION (AWS App Runner Ready)")
    print("=" * 70)
    print(f"  Workers           : {workers}")
    print(f"  Worker class      : {worker_class}")
    print(f"  Threads/worker    : {threads}")
    print(f"  Worker connections: {worker_connections}")
    print(f"  Max requests      : {max_requests} {'(disabled)' if max_requests == 0 else ''}")
    print(f"  Timeout           : {timeout}s")
    print(f"  Bind              : {bind}")
    print(f"  Preload app       : {preload_app}")
    print("=" * 70)
    print(f"📊 Capacité théorique : ~{workers * worker_connections} connexions simultanées")
    print(f"🔄 Workflow photos   : S3+SQS (robuste aux redémarrages)")
    print("=" * 70)

def worker_exit(server, worker):
    """Callback lors de la sortie d'un worker"""
    print(f"⚠️  Worker {worker.pid} exited")
