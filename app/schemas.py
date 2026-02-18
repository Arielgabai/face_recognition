from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import UserType
from fastapi import UploadFile

# Schémas pour l'authentification
class UserBase(BaseModel):
    username: str
    email: EmailStr
    user_type: UserType = UserType.USER  # Peut être USER, PHOTOGRAPHER ou ADMIN

class UserCreate(UserBase):
    password: str

class UserCreateWithSelfie(UserBase):
    password: str
    # Le champ selfie sera géré côté route avec UploadFile

class UserLogin(BaseModel):
    username: str
    password: str
    user_id: Optional[int] = None  # Pour sélection de compte spécifique quand plusieurs événements

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    selfie_path: Optional[str] = None  # Peut être None car les selfies sont stockées en binaire
    selfie_status: Optional[str] = None  # none|uploaded|valid|invalid
    selfie_error: Optional[str] = None  # Message d'erreur si selfie invalide
    # Champs de l'événement (optionnels)
    event_name: Optional[str] = None
    event_id: Optional[int] = None
    event_code: Optional[str] = None
    event_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Schémas pour les photos
class PhotoBase(BaseModel):
    original_filename: str
    photo_type: str

class PhotoCreate(PhotoBase):
    pass

class Photo(PhotoBase):
    id: int
    filename: str
    file_path: Optional[str] = None  # Peut être None car les photos sont stockées en binaire
    user_id: Optional[int] = None
    photographer_id: Optional[int] = None
    uploaded_at: datetime
    # Champs additionnels renvoyés par l'API
    content_type: Optional[str] = None
    event_id: Optional[int] = None
    event_name: Optional[str] = None
    has_face_match: Optional[bool] = False

    class Config:
        from_attributes = True

# Schémas pour les correspondances faciales
class FaceMatchBase(BaseModel):
    confidence_score: int

class FaceMatch(FaceMatchBase):
    id: int
    photo_id: int
    user_id: int
    detected_at: datetime

    class Config:
        from_attributes = True

# Schémas pour les réponses API
class UserProfile(BaseModel):
    user: User
    total_photos: int
    photos_with_face: int

class PhotoWithMatches(BaseModel):
    photo: Photo
    matches: List[FaceMatch] = [] 


# ========== SCHÉMAS PAGINATION ROBUSTE ==========

class PhotoMeta(BaseModel):
    """
    Métadonnées d'une photo sans les données binaires.
    Utilisé pour les listings paginés haute performance.
    """
    id: int
    original_filename: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    uploaded_at: datetime
    event_id: Optional[int] = None
    event_name: Optional[str] = None
    show_in_general: Optional[bool] = None
    has_face_match: bool = False
    # Optionnel: pour les photographes ou si exposé
    s3_key: Optional[str] = None
    processing_status: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedPhotosResponse(BaseModel):
    """
    Réponse paginée pour les photos.
    
    Pagination cursor-based: stabilité lors d'insertions/suppressions.
    Le cursor encode (uploaded_at, id) pour un tri déterministe.
    
    Usage:
    - Premier appel: GET /api/.../photos?limit=100
    - Appels suivants: GET /api/.../photos?limit=100&cursor=<next_cursor>
    """
    items: List[PhotoMeta]
    next_cursor: Optional[str] = None  # Base64 de "uploaded_at:id", None si fin
    has_more: bool = False
    total: Optional[int] = None  # Optionnel car COUNT(*) peut être coûteux


class CursorParams(BaseModel):
    """Paramètres décodés depuis un cursor."""
    uploaded_at: datetime
    id: int