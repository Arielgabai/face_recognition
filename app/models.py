from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table, LargeBinary, Float, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserType(str, enum.Enum):
    USER = "user"
    PHOTOGRAPHER = "photographer"
    ADMIN = "admin"


class PhotoProcessingStatus(str, enum.Enum):
    """Statut de traitement d'une photo dans le workflow asynchrone S3+SQS."""
    PENDING = "PENDING"       # Photo créée en DB, en attente de traitement
    PROCESSING = "PROCESSING" # Traitement en cours par le worker
    DONE = "DONE"             # Traitement terminé avec succès
    FAILED = "FAILED"         # Traitement échoué


class DeleteJobStatus(str, enum.Enum):
    """Statut d'un job de suppression de photos."""
    PENDING = "PENDING"       # Job créé, en attente de traitement
    IN_PROGRESS = "IN_PROGRESS"  # Suppression en cours
    DONE = "DONE"             # Toutes les photos supprimées avec succès
    PARTIAL = "PARTIAL"       # Terminé avec des erreurs partielles
    FAILED = "FAILED"         # Échec complet du job

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    event_code = Column(String, unique=True, index=True)
    date = Column(DateTime(timezone=True), nullable=True)
    photographer_id = Column(Integer, ForeignKey("users.id"))

    photographer = relationship("User", foreign_keys=[photographer_id], back_populates="events")
    photos = relationship("Photo", back_populates="event")
    users = relationship("UserEvent", back_populates="event")

# Table d'association User <-> Event
class UserEvent(Base):
    __tablename__ = "user_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    # FaceId Rekognition du selfie pour cet event (évite les scans list_faces)
    rekognition_face_id = Column(String, nullable=True, index=True)

    user = relationship("User", back_populates="user_events")
    event = relationship("Event", back_populates="users")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)  # Removed unique=True (now handled by composite constraint)
    email = Column(String, index=True)  # Removed unique=True (now handled by composite constraint)
    hashed_password = Column(String)
    user_type = Column(String, default=UserType.USER)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)  # NEW: événement principal
    selfie_path = Column(String, nullable=True)
    selfie_data = Column(LargeBinary, nullable=True)  # Données binaires du selfie
    selfie_status = Column(String, nullable=True, default=None)  # none|uploaded|valid|invalid
    selfie_error = Column(String, nullable=True, default=None)  # Message d'erreur si selfie invalide
    selfie_content_type = Column(String, nullable=True, default=None)  # ex: image/jpeg
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Contraintes unique composites : permet le même email/username pour des événements différents
    # COALESCE(event_id, -1) traite NULL comme -1 pour garantir l'unicité des photographes/admins
    __table_args__ = (
        Index('users_email_event_unique', 'email', func.coalesce(event_id, -1), unique=True),
        Index('users_username_event_unique', 'username', func.coalesce(event_id, -1), unique=True),
        # Index composites pour accélérer les checks par événement
        Index('idx_users_event_username', 'event_id', 'username'),
        Index('idx_users_event_email', 'event_id', 'email'),
    )
    
    # Relations - spécifier explicitement les clés étrangères
    photos = relationship("Photo", back_populates="owner", foreign_keys="Photo.user_id")
    uploaded_photos = relationship("Photo", back_populates="photographer", foreign_keys="Photo.photographer_id")
    face_matches = relationship("FaceMatch", back_populates="user")
    events = relationship("Event", back_populates="photographer", foreign_keys="Event.photographer_id")
    user_events = relationship("UserEvent", back_populates="user")
    primary_event = relationship("Event", foreign_keys=[event_id], viewonly=True)  # NEW: relation vers l'événement principal (lecture seule)

class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    original_filename = Column(String)
    file_path = Column(String, nullable=True)  # Gardé pour compatibilité
    photo_data = Column(LargeBinary, nullable=True)  # Données binaires de la photo
    content_type = Column(String, default="image/jpeg")  # Type MIME de l'image
    photo_type = Column(String)  # 'group', 'selfie', 'uploaded'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    photographer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    
    # ========== Nouveaux champs pour workflow S3+SQS asynchrone ==========
    # Clé S3 de l'image brute uploadée (format: raw/event_{event_id}/{photo_id}.jpg)
    s3_key = Column(String, nullable=True, index=True)
    # Statut de traitement: PENDING, PROCESSING, DONE, FAILED
    processing_status = Column(String, nullable=True, default=PhotoProcessingStatus.PENDING.value, index=True)
    # Message d'erreur en cas d'échec du traitement
    error_message = Column(Text, nullable=True)
    # Timestamp de mise à jour du statut
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Colonnes d'optimisation des photos
    original_size = Column(Integer, nullable=True)
    compressed_size = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    retention_days = Column(Integer, nullable=True, default=30)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    quality_level = Column(String, nullable=True, default="medium")
    
    # Visibilité dans l'onglet "Général"
    show_in_general = Column(Boolean, nullable=True, default=None)
    # Indique si la photo a été indexée côté Rekognition
    is_indexed = Column(Boolean, nullable=True, default=False)

    # Index pour accélérer les filtres courants
    __table_args__ = (
        Index('idx_photos_user', 'user_id'),
        Index('idx_photos_event', 'event_id'),
    )
    
    # Relations
    owner = relationship("User", back_populates="photos", foreign_keys=[user_id])
    photographer = relationship("User", back_populates="uploaded_photos", foreign_keys=[photographer_id])
    face_matches = relationship("FaceMatch", back_populates="photo")
    event = relationship("Event", back_populates="photos")

class FaceMatch(Base):
    __tablename__ = "face_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    confidence_score = Column(Integer)  # Score de confiance (0-100)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    photo = relationship("Photo", back_populates="face_matches")
    user = relationship("User", back_populates="face_matches")

# --- Intégration Google Drive ---

class GoogleDriveIntegration(Base):
    __tablename__ = "gdrive_integrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    photographer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_email = Column(String, nullable=True)
    folder_id = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    delta_token = Column(String, nullable=True)  # réservé si on passe au Changes API
    status = Column(String, default="connected")  # connected|revoked|error
    # Écoute continue (polling)
    listening = Column(Boolean, nullable=False, default=False)
    poll_interval_sec = Column(Integer, nullable=True)  # défaut côté app si null
    batch_size = Column(Integer, nullable=True)  # taille des sous-lots lors de l'ingestion
    last_poll_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    event = relationship("Event")
    photographer = relationship("User")


class PhotoFace(Base):
    """Tracks FaceIds returned by Rekognition IndexFaces per photo.

    Replaces the expensive ListFaces scan to find which FaceIds belong to a photo.
    """
    __tablename__ = "photo_faces"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    face_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('uq_photo_faces_photo_face', 'photo_id', 'face_id', unique=True),
        Index('idx_photo_faces_event', 'event_id'),
    )

    photo = relationship("Photo")
    event = relationship("Event")


class GoogleDriveIngestionLog(Base):
    __tablename__ = "gdrive_ingestion_log"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("gdrive_integrations.id"), nullable=False)
    file_id = Column(String, index=True)
    file_name = Column(String)
    md5_checksum = Column(String, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="ingested")  # ingested|failed
    error = Column(String, nullable=True)

    integration = relationship("GoogleDriveIntegration")


class LocalWatcher(Base):
    __tablename__ = "local_watchers"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    label = Column(String, nullable=True)
    expected_path = Column(String, nullable=True)
    move_uploaded_dir = Column(String, nullable=True)
    machine_label = Column(String, nullable=True)
    listening = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=True)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    event = relationship("Event")


class LocalIngestionLog(Base):
    __tablename__ = "local_ingestion_log"

    id = Column(Integer, primary_key=True, index=True)
    watcher_id = Column(Integer, ForeignKey("local_watchers.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    file_name = Column(String)
    status = Column(String, default="ingested")  # ingested|failed
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    watcher = relationship("LocalWatcher")
    event = relationship("Event")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class DeleteJob(Base):
    """
    Job de suppression de photos asynchrone.
    
    Permet de traiter la suppression de multiples photos en arrière-plan
    pour éviter les timeouts HTTP sur les suppressions massives.
    
    Workflow:
    1. Endpoint crée un DeleteJob avec status=PENDING et photo_ids en JSON
    2. Message SQS envoyé avec job_id
    3. Worker traite les photos par lots (face_matches, rekognition, DB, S3)
    4. Status mis à jour: IN_PROGRESS -> DONE/PARTIAL/FAILED
    """
    __tablename__ = "delete_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    # UUID unique pour identifier le job (exposé dans l'API)
    job_id = Column(String, unique=True, index=True, nullable=False)
    # ID du photographe qui a demandé la suppression
    photographer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Liste des IDs de photos à supprimer (JSON array)
    photo_ids_json = Column(Text, nullable=False)
    # Nombre total de photos à supprimer
    total_photos = Column(Integer, nullable=False, default=0)
    # Nombre de photos traitées (succès + erreurs)
    processed_count = Column(Integer, nullable=False, default=0)
    # Nombre de photos supprimées avec succès
    success_count = Column(Integer, nullable=False, default=0)
    # Nombre d'erreurs
    error_count = Column(Integer, nullable=False, default=0)
    # Détails des erreurs (JSON array)
    errors_json = Column(Text, nullable=True)
    # Statut du job
    status = Column(String, nullable=False, default=DeleteJobStatus.PENDING.value, index=True)
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Durée totale en secondes (pour monitoring)
    duration_seconds = Column(Float, nullable=True)
    
    # Index pour les requêtes de monitoring
    __table_args__ = (
        Index('idx_delete_jobs_photographer', 'photographer_id'),
        Index('idx_delete_jobs_status', 'status'),
        Index('idx_delete_jobs_created', 'created_at'),
    )
    
    photographer = relationship("User")