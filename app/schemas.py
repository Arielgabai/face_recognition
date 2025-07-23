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

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    selfie_path: Optional[str] = None

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
    file_path: str
    user_id: Optional[int] = None
    photographer_id: Optional[int] = None
    uploaded_at: datetime

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