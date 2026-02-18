"""
Configuration Gunicorn optimisée pour AWS App Runner

Utilisation:
    gunicorn main:app -c gunicorn_config.py

Variables d'environnement:
    GUNICORN_WORKERS      : Nombre de workers (défaut: 3)
    GUNICORN_THREADS      : Threads par worker (défaut: 2)
    GUNICORN_TIMEOUT      : Timeout requête en secondes (défaut: 90)
    GUNICORN_LOGLEVEL     : Niveau de log (défaut: info)
    GUNICORN_MAX_REQUESTS : Nombre de requêtes avant recyclage (défaut: 0 = désactivé)
    PORT                  : Port d'écoute (défaut: 10000)
    GUNICORN_GRACEFUL_TIMEOUT : Temps pour terminer les requêtes en cours (défaut: 30)
    GUNICORN_KEEPALIVE    : Keep-alive en secondes (défaut: 5)
"""
import os

# ========== WORKERS ==========
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# Recyclage des workers (0 = désactivé)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = 50 if max_requests > 0 else 0

# ========== TIMEOUTS ==========
timeout = int(os.getenv("GUNICORN_TIMEOUT", "90"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# ========== CONNEXIONS ==========
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
backlog = 2048

# ========== LOGS ==========
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# ========== BIND ==========
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# ========== PERFORMANCE ==========
preload_app = False

# ========== HOOKS ==========
def on_starting(server):
    """Callback au démarrage du serveur"""
    print("=" * 70)
    print("GUNICORN - CONFIGURATION (AWS App Runner Ready)")
    print("=" * 70)
    print(f"  Workers           : {workers}")
    print(f"  Worker class      : {worker_class}")
    print(f"  Threads/worker    : {threads}")
    print(f"  Worker connections: {worker_connections}")
    print(f"  Max requests      : {max_requests} {'(disabled)' if max_requests == 0 else ''}")
    print(f"  Timeout           : {timeout}s")
    print(f"  Graceful timeout  : {graceful_timeout}s")
    print(f"  Keepalive         : {keepalive}s")
    print(f"  Log level         : {loglevel}")
    print(f"  Bind              : {bind}")
    print(f"  Preload app       : {preload_app}")
    print("=" * 70)

def worker_exit(server, worker):
    """Callback lors de la sortie d'un worker"""
    print(f"Worker {worker.pid} exited")
