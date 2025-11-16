import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données
# Par défaut, on utilise le même fichier que la prod Render
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")

# Si c'est PostgreSQL, ajuster l'URL pour SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Options de pool pour éviter les connexions mortes et élargir la capacité
# Ajustables via variables d'environnement côté déploiement (Render)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20") or "20")
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "50") or "50")
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800") or "1800")
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "60") or "60")

# Pour SQLite, désactiver check_same_thread pour éviter les erreurs en environnement async/multithread
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_timeout=POOL_TIMEOUT,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Fonction pour créer toutes les tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Fonction pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # En cas d'exception non gérée, s'assurer que la transaction est rollback
        db.rollback()
        raise
    finally:
        db.close()