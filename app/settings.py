"""
Configuration centralisée pour l'application Face Recognition.

Utilise Pydantic Settings pour charger les variables d'environnement
avec validation de type et valeurs par défaut.

Usage:
    from settings import settings
    
    bucket = settings.PHOTO_BUCKET_NAME
    queue_url = settings.PHOTO_SQS_QUEUE_URL
"""

import os
from typing import Optional
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback pour anciennes versions de pydantic
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application.
    Toutes les valeurs peuvent être surchargées par des variables d'environnement.
    """
    
    # ========== AWS General ==========
    # Région par défaut pour S3, SQS, SSM (Paris)
    AWS_REGION: str = "eu-west-3"
    # Région spécifique pour Rekognition (Irlande - Rekognition non disponible à Paris)
    REKOGNITION_REGION: str = "eu-west-1"
    
    # ========== S3 Storage ==========
    # Bucket pour stocker les photos brutes uploadées
    PHOTO_BUCKET_NAME: str = ""
    # Préfixe pour les photos brutes (format: {prefix}/event_{event_id}/{photo_id}.jpg)
    PHOTO_S3_RAW_PREFIX: str = "raw"
    
    # ========== SQS Queue ==========
    # URL de la file SQS pour le traitement des photos
    PHOTO_SQS_QUEUE_URL: str = ""
    # Timeout de visibilité SQS en secondes (doit être > temps de traitement moyen)
    PHOTO_SQS_VISIBILITY_TIMEOUT: int = 300  # 5 minutes
    # Temps d'attente long polling SQS en secondes
    PHOTO_SQS_WAIT_TIME_SECONDS: int = 20
    # Nombre max de messages reçus par batch
    PHOTO_SQS_MAX_MESSAGES: int = 1
    
    # ========== Photo Worker ==========
    # Active/désactive le worker de traitement des photos
    PHOTO_WORKER_ENABLED: bool = True
    # Nombre de workers (threads) pour le traitement des photos
    PHOTO_WORKER_COUNT: int = 1
    # Délai entre les polls SQS en secondes (si aucun message)
    PHOTO_WORKER_POLL_INTERVAL: float = 1.0
    
    # ========== AWS Rekognition ==========
    AWS_REKOGNITION_COLLECTION_PREFIX: str = "event_"
    AWS_REKOGNITION_FACE_THRESHOLD: float = 60.0
    AWS_REKOGNITION_SEARCH_MAXFACES: int = 10
    AWS_REKOGNITION_SELFIE_SEARCH_MAXFACES: int = 500
    AWS_REKOGNITION_DETECT_MIN_CONF: float = 70.0
    AWS_REKOGNITION_IMAGE_MAX_DIM: int = 1536
    AWS_REKOGNITION_CROP_PADDING: float = 0.3
    AWS_REKOGNITION_MIN_CROP_SIDE: int = 36
    AWS_REKOGNITION_MIN_OUTPUT_CROP_SIDE: int = 448
    AWS_REKOGNITION_TINY_FACE_AREA: float = 0.015
    AWS_REKOGNITION_SEARCH_QUALITY_FILTER: str = "AUTO"
    AWS_REKOGNITION_PURGE_AUTO: bool = True
    
    # ========== AWS Concurrent Requests ==========
    AWS_CONCURRENT_REQUESTS: int = 10
    AWS_MAX_RETRIES: int = 2
    AWS_BACKOFF_BASE_SEC: float = 0.2
    
    # ========== Database ==========
    DATABASE_URL: str = "sqlite:///./face_recognition.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_TIMEOUT: int = 30
    
    # ========== Application ==========
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # ========== Authentication / JWT ==========
    # Clé secrète pour signer les JWT (OBLIGATOIRE en prod)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    # Algorithme de signature JWT
    JWT_ALGORITHM: str = "HS256"
    # Durée de vie du token d'accès en minutes (défaut: 480 = 8 heures pour soirées)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Durée de vie du refresh token en minutes (défaut: 1440 = 24 heures)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440
    # Marge avant expiration pour renouvellement anticipé (en minutes)
    TOKEN_REFRESH_MARGIN_MINUTES: int = 5
    
    # ========== Photo Processing ==========
    # Seuil minimum de similarité pour créer un FaceMatch
    AWS_MATCH_MIN_SIMILARITY: int = 70
    # Active les logs de debug pour le matching
    AWS_MATCH_DEBUG: bool = False
    # Active le fallback CompareFaces (coûteux)
    ENABLE_COMPARE_FACES_FALLBACK: bool = False
    
    class Config:
        # Nom du fichier .env à charger (si présent)
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Ignorer les variables d'environnement inconnues
        extra = "ignore"
        # Sensibilité à la casse des variables d'environnement
        case_sensitive = True
    
    @property
    def is_sqs_configured(self) -> bool:
        """Vérifie si SQS est configuré pour le traitement asynchrone."""
        return bool(self.PHOTO_SQS_QUEUE_URL and self.PHOTO_BUCKET_NAME)
    
    @property
    def is_s3_configured(self) -> bool:
        """Vérifie si S3 est configuré pour le stockage des photos."""
        return bool(self.PHOTO_BUCKET_NAME)


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne l'instance singleton des settings.
    Utilise lru_cache pour éviter de recharger les settings à chaque appel.
    """
    return Settings()


# Alias pour un accès direct
settings = get_settings()


def reload_settings() -> Settings:
    """
    Force le rechargement des settings (utile pour les tests).
    """
    get_settings.cache_clear()
    return get_settings()
