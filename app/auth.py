from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
import os

# Import des settings centralisés
from settings import settings

# Configuration JWT depuis settings (configurable via variables d'environnement)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
TOKEN_REFRESH_MARGIN_MINUTES = settings.TOKEN_REFRESH_MARGIN_MINUTES

# Log de la configuration au démarrage (utile pour debug)
print(f"[Auth] Token expiration configured: ACCESS={ACCESS_TOKEN_EXPIRE_MINUTES}min, REFRESH={REFRESH_TOKEN_EXPIRE_MINUTES}min, MARGIN={TOKEN_REFRESH_MARGIN_MINUTES}min")

# Configuration du hachage des mots de passe
# OPTIMISÉ : Réduction des rounds bcrypt pour améliorer les performances
# Production : 12 rounds (défaut), Tests de charge : 4-6 rounds
import os as _os
BCRYPT_ROUNDS = int(_os.getenv("BCRYPT_ROUNDS", "4"))  # 4 pour tests, 12 pour prod
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si le mot de passe correspond au hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Génère un hash du mot de passe"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Vérifie et décode le token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")  # Récupérer l'user_id si présent
        
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Si user_id est présent dans le token, l'utiliser en priorité
    # (important pour gérer plusieurs comptes avec le même username sur des événements différents)
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        # Fallback: chercher par username (pour compatibilité avec anciens tokens)
        user = db.query(User).filter(User.username == username).first()
    
    if user is None:
        raise credentials_exception
    return user

def get_current_user(current_user: User = Depends(verify_token)):
    """Récupère l'utilisateur actuel"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 