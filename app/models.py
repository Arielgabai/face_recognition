from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table, LargeBinary, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class UserType(str, enum.Enum):
    USER = "user"
    PHOTOGRAPHER = "photographer"
    ADMIN = "admin"

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    event_code = Column(String, unique=True, index=True)
    date = Column(DateTime(timezone=True), nullable=True)
    photographer_id = Column(Integer, ForeignKey("users.id"))

    photographer = relationship("User", back_populates="events")
    photos = relationship("Photo", back_populates="event")
    users = relationship("UserEvent", back_populates="event")

# Table d'association User <-> Event
class UserEvent(Base):
    __tablename__ = "user_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="user_events")
    event = relationship("Event", back_populates="users")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    user_type = Column(String, default=UserType.USER)
    selfie_path = Column(String, nullable=True)
    selfie_data = Column(LargeBinary, nullable=True)  # Données binaires du selfie
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations - spécifier explicitement les clés étrangères
    photos = relationship("Photo", back_populates="owner", foreign_keys="Photo.user_id")
    uploaded_photos = relationship("Photo", back_populates="photographer", foreign_keys="Photo.photographer_id")
    face_matches = relationship("FaceMatch", back_populates="user")
    events = relationship("Event", back_populates="photographer", foreign_keys="Event.photographer_id")
    user_events = relationship("UserEvent", back_populates="user")

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
    
    # Colonnes d'optimisation des photos
    original_size = Column(Integer, nullable=True)
    compressed_size = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    retention_days = Column(Integer, nullable=True, default=30)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    quality_level = Column(String, nullable=True, default="medium")
    
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