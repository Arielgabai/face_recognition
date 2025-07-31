from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import uuid
from datetime import timedelta
from sqlalchemy.exc import NoResultFound
import qrcode
from io import BytesIO
from fastapi import Request
import jwt
from dotenv import load_dotenv

load_dotenv()

from database import get_db, create_tables
from models import User, Photo, FaceMatch, UserType, Event, UserEvent
from schemas import UserCreate, UserLogin, Token, User as UserSchema, Photo as PhotoSchema, UserProfile
from auth import verify_password, get_password_hash, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from face_recognizer import FaceRecognizer

# Créer les tables au démarrage
create_tables()

app = FastAPI(title="Face Recognition API", version="1.0.0")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173",  # React dev servers
        "https://facerecognition-d0r8.onrender.com"  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialiser le recognizer
face_recognizer = FaceRecognizer()

def photo_to_dict(photo: Photo) -> dict:
    """Convertit un objet Photo en dictionnaire sans les données binaires"""
    return {
        "id": photo.id,
        "filename": photo.filename,
        "original_filename": photo.original_filename,
        "file_path": photo.file_path,
        "content_type": photo.content_type,
        "photo_type": photo.photo_type,
        "user_id": photo.user_id,
        "photographer_id": photo.photographer_id,
        "uploaded_at": photo.uploaded_at,
        "event_id": photo.event_id
    }

# Créer les dossiers nécessaires
os.makedirs("static/uploads/selfies", exist_ok=True)
os.makedirs("static/uploads/photos", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Servir le frontend HTML selon le type d'utilisateur"""
    try:
        # Vérifier si l'utilisateur est connecté et son type
        token = request.headers.get('authorization')
        if token and token.startswith('Bearer '):
            try:
                # Décoder le token pour obtenir le type d'utilisateur
                payload = jwt.decode(token.split(' ')[1], SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                if username:
                    # Récupérer l'utilisateur depuis la base de données
                    db = next(get_db())
                    user = db.query(User).filter(User.username == username).first()
                    if user and user.user_type == UserType.ADMIN:
                        # Rediriger vers l'interface admin
                        with open("static/admin.html", "r", encoding="utf-8") as f:
                            return HTMLResponse(content=f.read())
                    elif user and user.user_type == UserType.PHOTOGRAPHER:
                        # Rediriger vers l'interface photographe
                        with open("static/photographer.html", "r", encoding="utf-8") as f:
                            return HTMLResponse(content=f.read())
            except:
                pass
        
        # Interface normale pour les autres utilisateurs
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Face Recognition API</h1><p>Frontend not found</p>")

@app.get("/api")
async def api_root():
    """Point d'entrée de l'API"""
    return {"message": "Face Recognition API"}

@app.get("/admin", response_class=HTMLResponse)
async def admin_interface():
    """Servir l'interface d'administration"""
    try:
        with open("static/admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin Interface</h1><p>Admin interface not found</p>")

@app.get("/photographer", response_class=HTMLResponse)
async def photographer_interface():
    """Servir l'interface photographe"""
    try:
        with open("static/photographer.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Photographer Interface</h1><p>Photographer interface not found</p>")

@app.get("/register", response_class=HTMLResponse)
async def register_page(event_code: str = None):
    """Page d'inscription pour les invités avec code événement"""
    try:
        with open("static/register.html", "r", encoding="utf-8") as f:
            content = f.read()
            # Injecter le code événement dans le JavaScript
            content = content.replace('{{EVENT_CODE}}', event_code or '')
            return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Page d'inscription</h1><p>Page d'inscription non trouvée</p>")

# === AUTHENTIFICATION ===

@app.post("/api/register", response_model=UserSchema)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Inscription d'un nouvel utilisateur"""
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username ou email déjà utilisé"
        )
    
    # Créer le nouvel utilisateur
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        user_type=user_data.user_type
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/api/register-invite", response_model=UserSchema)
async def register_invite(
    user_data: UserCreate = Body(...),
    event_code: str = Body(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un invité à partir d'un event_code (QR code)"""
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username ou email déjà utilisé"
        )
    # Vérifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="event_code invalide")
    # Créer le nouvel utilisateur
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        user_type=UserType.USER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Lier l'utilisateur à l'événement
    user_event = UserEvent(user_id=db_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    return db_user

@app.post("/api/register-invite-with-selfie", response_model=UserSchema)
async def register_invite_with_selfie(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    event_code: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un invité avec selfie et event_code (QR code)"""
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username ou email déjà utilisé"
        )
    # Vérifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="event_code invalide")
    # Créer le nouvel utilisateur
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_type=UserType.USER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Lier l'utilisateur à l'événement
    user_event = UserEvent(user_id=db_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    # Gérer la selfie
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    import uuid, os, shutil
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{db_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("static/uploads/selfies", unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    db_user.selfie_path = file_path
    db.commit()
    # Relancer le matching de la selfie avec toutes les photos de l'événement
    face_recognizer.match_user_selfie_with_photos_event(db_user, event.id, db)
    return db_user

@app.post("/api/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Connexion utilisateur"""
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Récupérer les informations de l'utilisateur connecté"""
    return current_user

@app.get("/api/my-selfie")
async def get_my_selfie(current_user: User = Depends(get_current_user)):
    """Récupérer les informations de la selfie de l'utilisateur connecté"""
    if not current_user.selfie_data:
        raise HTTPException(status_code=404, detail="Aucune selfie trouvée")
    
    return {
        "user_id": current_user.id,
        "created_at": current_user.created_at
    }

@app.delete("/api/my-selfie")
async def delete_my_selfie(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer la selfie de l'utilisateur connecté et les correspondances associées"""
    if not current_user.selfie_data:
        raise HTTPException(status_code=404, detail="Aucune selfie à supprimer")

    # Supprimer les données binaires de la base utilisateur
    current_user.selfie_data = None
    current_user.selfie_path = None
    db.commit()
    # Supprimer tous les FaceMatch liés à cet utilisateur
    db.query(FaceMatch).filter(FaceMatch.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Selfie supprimée avec succès"}

# === GESTION DES SELFIES ===

@app.post("/api/upload-selfie")
async def upload_selfie(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload d'une selfie pour l'utilisateur"""
    if current_user.user_type == UserType.PHOTOGRAPHER:
        raise HTTPException(
            status_code=403, 
            detail="Les photographes ne peuvent pas uploader de selfies"
        )
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    
    # Lire les données binaires du fichier
    file_data = await file.read()
    
    # Mettre à jour l'utilisateur avec les données binaires
    current_user.selfie_data = file_data
    current_user.selfie_path = None  # Plus besoin du chemin de fichier
    db.commit()

    # Relancer le matching de la selfie avec toutes les photos existantes
    match_count = face_recognizer.match_user_selfie_with_photos(current_user, db)

    return {"message": "Selfie uploadée avec succès", "matches": match_count}

# === GESTION DES PHOTOS (PHOTOGRAPHES) ===

@app.post("/api/upload-photos")
async def upload_multiple_photos(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de plusieurs photos par un photographe"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(
            status_code=403, 
            detail="Seuls les photographes peuvent uploader des photos"
        )
    
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    uploaded_photos = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue  # Ignorer les fichiers non-images
        
        # Sauvegarder temporairement le fichier
        temp_path = f"/tmp/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Traiter la photo avec reconnaissance faciale
            photo = face_recognizer.process_and_save_photo(
                temp_path, file.filename, current_user.id, db
            )
            uploaded_photos.append({
                "filename": photo.filename,
                "original_filename": photo.original_filename
            })
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    return {
        "message": f"{len(uploaded_photos)} photos uploadées et traitées avec succès",
        "uploaded_photos": uploaded_photos
    }

@app.post("/api/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload d'une photo par un photographe"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(
            status_code=403, 
            detail="Seuls les photographes peuvent uploader des photos"
        )
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    
    # Sauvegarder temporairement le fichier
    temp_path = f"/tmp/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Traiter la photo avec reconnaissance faciale
        photo = face_recognizer.process_and_save_photo(
            temp_path, file.filename, current_user.id, db
        )
        
        return {
            "message": "Photo uploadée et traitée avec succès",
            "photo_id": photo.id,
            "filename": photo.filename
        }
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(temp_path):
            os.remove(temp_path)

# === GESTION DES PHOTOS (UTILISATEURS) ===

@app.get("/api/my-photos", response_model=List[PhotoSchema])
async def get_my_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les photos où l'utilisateur apparaît pour son événement principal"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent accéder à cette route")
    
    # Trouver le premier événement de l'utilisateur (événement principal)
    user_event = db.query(UserEvent).filter_by(user_id=current_user.id).first()
    if not user_event:
        raise HTTPException(status_code=404, detail="Aucun événement associé à cet utilisateur")
    event_id = user_event.event_id
    photos = db.query(Photo).join(FaceMatch).filter(
        FaceMatch.user_id == current_user.id,
        FaceMatch.photo_id == Photo.id,
        Photo.event_id == event_id
    ).all()
    return photos

@app.get("/api/all-photos", response_model=List[PhotoSchema])
async def get_all_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les photos de l'événement principal de l'utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent accéder à cette route")
    
    user_event = db.query(UserEvent).filter_by(user_id=current_user.id).first()
    if not user_event:
        raise HTTPException(status_code=404, detail="Aucun événement associé à cet utilisateur")
    event_id = user_event.event_id
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les métadonnées, pas les données binaires
    return [photo_to_dict(photo) for photo in photos]

@app.get("/api/my-uploaded-photos", response_model=List[PhotoSchema])
async def get_my_uploaded_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les photos uploadées par le photographe connecté"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent accéder à cette route")
    
    photos = db.query(Photo).filter(
        Photo.photographer_id == current_user.id,
        Photo.photo_type == "uploaded"
    ).all()
    
    # Retourner seulement les métadonnées, pas les données binaires
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id,
            "filename": photo.filename,
            "original_filename": photo.original_filename,
            "file_path": photo.file_path,
            "content_type": photo.content_type,
            "photo_type": photo.photo_type,
            "user_id": photo.user_id,
            "photographer_id": photo.photographer_id,
            "uploaded_at": photo.uploaded_at,
            "event_id": photo.event_id
        })
    
    return photo_list

@app.get("/api/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer le profil complet de l'utilisateur"""
    photos_with_face = face_recognizer.get_user_photos_with_face(current_user.id, db)
    all_photos = face_recognizer.get_all_photos_for_user(current_user.id, db)
    
    return UserProfile(
        user=current_user,
        total_photos=len(all_photos),
        photos_with_face=len(photos_with_face)
    )

# === SERVIR LES IMAGES ===

@app.get("/api/image/{filename}")
async def get_image(filename: str):
    """Servir une image depuis les dossiers static (pour compatibilité)"""
    # Chercher dans différents dossiers possibles
    possible_paths = [
        os.path.join("static", filename),
        os.path.join("static/uploads/photos", filename),
        os.path.join("static/uploads/selfies", filename)
    ]
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    # Si aucune image n'est trouvée
    raise HTTPException(status_code=404, detail=f"Image non trouvée: {filename}")

@app.get("/api/photo/{photo_id}")
async def get_photo_by_id(
    photo_id: int,
    db: Session = Depends(get_db)
):
    """Servir une photo depuis la base de données par son ID"""
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    
    if not photo.photo_data:
        raise HTTPException(status_code=404, detail="Données de photo non disponibles")
    
    # Retourner les données binaires avec le bon type MIME
    return Response(
        content=photo.photo_data,
        media_type=photo.content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"}  # Cache pour 1 an
    )

@app.get("/api/selfie/{user_id}")
async def get_selfie_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Servir une selfie depuis la base de données par l'ID utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    if not user.selfie_data:
        raise HTTPException(status_code=404, detail="Selfie non disponible")
    
    # Retourner les données binaires avec le bon type MIME
    return Response(
        content=user.selfie_data,
        media_type="image/jpeg",  # Par défaut pour les selfies
        headers={"Cache-Control": "public, max-age=31536000"}  # Cache pour 1 an
    )

# === ROUTES ADMIN ===

@app.delete("/api/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer une photo (photographes seulement)"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent supprimer des photos")
    
    # Récupérer la photo
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    
    # Vérifier que le photographe est bien le propriétaire de la photo
    if photo.photographer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres photos")
    
    try:
        # Supprimer les correspondances de visages associées
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo_id).delete()
        
        # Supprimer l'enregistrement de la base de données
        db.delete(photo)
        db.commit()
        
        return {"message": "Photo supprimée avec succès"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

@app.delete("/api/photos")
async def delete_multiple_photos(
    photo_ids: str,  # Recevoir comme string séparée par des virgules
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer plusieurs photos (photographes seulement)"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent supprimer des photos")
    
    if not photo_ids:
        raise HTTPException(status_code=400, detail="Aucune photo sélectionnée")
    
    # Convertir la string en liste d'IDs
    try:
        photo_id_list = [int(id.strip()) for id in photo_ids.split(',') if id.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Format d'ID invalide")
    
    if not photo_id_list:
        raise HTTPException(status_code=400, detail="Aucune photo sélectionnée")
    
    # Récupérer les photos du photographe
    photos = db.query(Photo).filter(
        Photo.id.in_(photo_id_list),
        Photo.photographer_id == current_user.id
    ).all()
    
    if not photos:
        raise HTTPException(status_code=404, detail="Aucune photo trouvée")
    
    deleted_count = 0
    try:
        for photo in photos:
            # Supprimer les correspondances de visages associées
            db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
            
            # Supprimer l'enregistrement de la base de données
            db.delete(photo)
            deleted_count += 1
        
        db.commit()
        return {"message": f"{deleted_count} photos supprimées avec succès"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

# === ADMINISTRATION ===

@app.get("/api/admin/photographers")
async def admin_get_photographers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer tous les photographes (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder à cette route")
    
    photographers = db.query(User).filter(User.user_type == UserType.PHOTOGRAPHER).all()
    return photographers

@app.post("/api/admin/photographers")
async def admin_create_photographer(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer un nouveau photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent créer des photographes")
    
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email déjà utilisé")
    
    # Créer le nouveau photographe
    hashed_password = get_password_hash(password)
    db_photographer = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_type=UserType.PHOTOGRAPHER
    )
    
    db.add(db_photographer)
    db.commit()
    db.refresh(db_photographer)
    
    return {"message": "Photographe créé avec succès", "photographer_id": db_photographer.id}

@app.put("/api/admin/photographers/{photographer_id}")
async def admin_update_photographer(
    photographer_id: int,
    username: str = Body(...),
    email: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Modifier un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent modifier des photographes")
    
    # Récupérer le photographe
    photographer = db.query(User).filter(
        User.id == photographer_id,
        User.user_type == UserType.PHOTOGRAPHER
    ).first()
    
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouvé")
    
    # Vérifier si le nouveau username/email n'est pas déjà utilisé par un autre utilisateur
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email),
        User.id != photographer_id
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email déjà utilisé")
    
    # Mettre à jour le photographe
    photographer.username = username
    photographer.email = email
    db.commit()
    db.refresh(photographer)
    
    return {"message": "Photographe modifié avec succès"}

@app.delete("/api/admin/photographers/{photographer_id}")
async def admin_delete_photographer(
    photographer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer des photographes")
    
    # Récupérer le photographe
    photographer = db.query(User).filter(
        User.id == photographer_id,
        User.user_type == UserType.PHOTOGRAPHER
    ).first()
    
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouvé")
    
    # Vérifier s'il y a des événements associés
    events = db.query(Event).filter(Event.photographer_id == photographer_id).all()
    if events:
        event_names = [event.name for event in events]
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer le photographe car il est associé aux événements: {', '.join(event_names)}"
        )
    
    # Supprimer les photos uploadées par ce photographe
    photos = db.query(Photo).filter(Photo.photographer_id == photographer_id).all()
    for photo in photos:
        # Supprimer les correspondances de visages
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
        # Supprimer le fichier physique
        if photo.file_path and os.path.exists(photo.file_path):
            os.remove(photo.file_path)
        # Supprimer l'enregistrement photo
        db.delete(photo)
    
    # Supprimer le photographe
    db.delete(photographer)
    db.commit()
    
    return {"message": "Photographe supprimé avec succès"}

@app.get("/api/admin/events")
async def admin_get_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer tous les événements (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder à cette route")
    
    events = db.query(Event).all()
    return events

@app.post("/api/admin/create-event")
async def admin_create_event(
    name: str = Body(...),
    event_code: str = Body(...),
    date: str = Body(None),
    photographer_id: int = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Créer un événement (mariage) et l'assigner à un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent créer des événements")
    # Vérifier unicité du code
    if db.query(Event).filter_by(event_code=event_code).first():
        raise HTTPException(status_code=400, detail="event_code déjà utilisé")
    # Vérifier que le photographe existe
    photographer = db.query(User).filter_by(id=photographer_id, user_type=UserType.PHOTOGRAPHER).first()
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouvé")
    # Créer l'événement
    from datetime import datetime as dt
    event = Event(
        name=name,
        event_code=event_code,
        date=dt.fromisoformat(date) if date else None,
        photographer_id=photographer_id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"message": "Événement créé", "event_id": event.id, "event_code": event.event_code}

@app.post("/api/admin/register-admin")
async def register_admin(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    """Créer le premier compte admin (seulement si aucun admin n'existe)"""
    from models import UserType
    existing_admin = db.query(User).filter(User.user_type == UserType.ADMIN).first()
    if existing_admin:
        raise HTTPException(status_code=403, detail="Un admin existe déjà")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username ou email déjà utilisé")
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_type=UserType.ADMIN
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "Admin créé", "user_id": db_user.id}

@app.post("/api/admin/create-photographer")
async def create_photographer(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent créer un photographe")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username ou email déjà utilisé")
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_type=UserType.PHOTOGRAPHER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "Photographe créé", "user_id": db_user.id}

@app.get("/api/admin/event-qr/{event_code}")
async def generate_event_qr(event_code: str, current_user: User = Depends(get_current_user)):
    """Générer un QR code pour l'inscription à un événement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent générer un QR code")
    
    # Vérifier que l'événement existe
    db = next(get_db())
    event = db.query(Event).filter(Event.event_code == event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Générer l'URL d'inscription vers le domaine de production
    url = f"https://facerecognition-d0r8.onrender.com/register?event_code={event_code}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# === NOUVELLES ROUTES POUR LA GESTION DES ÉVÉNEMENTS ===

@app.get("/api/photographer/events")
async def get_photographer_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer tous les événements du photographe connecté"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent accéder à cette route")
    
    events = db.query(Event).filter(Event.photographer_id == current_user.id).all()
    return events

@app.get("/api/photographer/events/{event_id}/photos")
async def get_event_photos(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les photos d'un événement spécifique pour un photographe"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent accéder à cette route")
    
    # Vérifier que l'événement appartient au photographe
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.photographer_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les métadonnées, pas les données binaires
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id,
            "filename": photo.filename,
            "original_filename": photo.original_filename,
            "file_path": photo.file_path,
            "content_type": photo.content_type,
            "photo_type": photo.photo_type,
            "user_id": photo.user_id,
            "photographer_id": photo.photographer_id,
            "uploaded_at": photo.uploaded_at,
            "event_id": photo.event_id
        })
    
    return photo_list

@app.post("/api/photographer/events/{event_id}/upload-photos")
async def upload_photos_to_event(
    event_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de photos pour un événement spécifique"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent uploader des photos")
    
    # Vérifier que l'événement appartient au photographe
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.photographer_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    uploaded_photos = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        
        # Sauvegarder temporairement le fichier
        temp_path = f"/tmp/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Traiter la photo avec reconnaissance faciale pour l'événement spécifique
            photo = face_recognizer.process_and_save_photo_for_event(
                temp_path, file.filename, current_user.id, event_id, db
            )
            uploaded_photos.append({
                "filename": photo.filename,
                "original_filename": photo.original_filename
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    return {
        "message": f"{len(uploaded_photos)} photos uploadées et traitées avec succès",
        "uploaded_photos": uploaded_photos
    }

@app.get("/api/user/events")
async def get_user_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer tous les événements auxquels l'utilisateur est inscrit"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent accéder à cette route")
    
    user_events = db.query(UserEvent).filter(UserEvent.user_id == current_user.id).all()
    events = []
    for user_event in user_events:
        event = db.query(Event).filter(Event.id == user_event.event_id).first()
        if event:
            events.append({
                "id": event.id,
                "name": event.name,
                "event_code": event.event_code,
                "date": event.date,
                "joined_at": user_event.joined_at
            })
    
    return events

@app.get("/api/user/events/{event_id}/photos")
async def get_user_event_photos(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les photos d'un événement spécifique pour un utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent accéder à cette route")
    
    # Vérifier que l'utilisateur est inscrit à cet événement
    user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event_id
    ).first()
    
    if not user_event:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à cet événement")
    
    # Récupérer les photos où l'utilisateur apparaît dans cet événement
    photos = db.query(Photo).join(FaceMatch).filter(
        FaceMatch.user_id == current_user.id,
        FaceMatch.photo_id == Photo.id,
        Photo.event_id == event_id
    ).all()
    
    # Retourner seulement les métadonnées, pas les données binaires
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id,
            "filename": photo.filename,
            "original_filename": photo.original_filename,
            "file_path": photo.file_path,
            "content_type": photo.content_type,
            "photo_type": photo.photo_type,
            "user_id": photo.user_id,
            "photographer_id": photo.photographer_id,
            "uploaded_at": photo.uploaded_at,
            "event_id": photo.event_id
        })
    
    return photo_list

@app.get("/api/user/events/{event_id}/all-photos")
async def get_all_event_photos(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les photos d'un événement pour un utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent accéder à cette route")
    
    # Vérifier que l'utilisateur est inscrit à cet événement
    user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event_id
    ).first()
    
    if not user_event:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à cet événement")
    
    # Récupérer toutes les photos de l'événement
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les métadonnées, pas les données binaires
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id,
            "filename": photo.filename,
            "original_filename": photo.original_filename,
            "file_path": photo.file_path,
            "content_type": photo.content_type,
            "photo_type": photo.photo_type,
            "user_id": photo.user_id,
            "photographer_id": photo.photographer_id,
            "uploaded_at": photo.uploaded_at,
            "event_id": photo.event_id
        })
    
    return photo_list

# === ROUTES POUR LES CODES ÉVÉNEMENT MANUELS ===

@app.post("/api/register-with-event-code")
async def register_with_event_code(
    user_data: UserCreate = Body(...),
    event_code: str = Body(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un utilisateur avec un code événement saisi manuellement"""
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email déjà utilisé")
    
    # Vérifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Code événement invalide")
    
    # Créer le nouvel utilisateur
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        user_type=UserType.USER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Lier l'utilisateur à l'événement
    user_event = UserEvent(user_id=db_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    
    return db_user

@app.post("/api/join-event")
async def join_event(
    event_code: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rejoindre un événement avec un code (pour utilisateurs déjà inscrits)"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent rejoindre des événements")
    
    # Vérifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Code événement invalide")
    
    # Vérifier si l'utilisateur est déjà inscrit à cet événement
    existing_user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event.id
    ).first()
    
    if existing_user_event:
        raise HTTPException(status_code=400, detail="Vous êtes déjà inscrit à cet événement")
    
    # Inscrire l'utilisateur à l'événement
    user_event = UserEvent(user_id=current_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    
    return {"message": f"Inscrit avec succès à l'événement {event.name}"}

# === ROUTES ADMIN POUR CRÉER DES CODES ÉVÉNEMENT COMPLEXES ===

@app.post("/api/admin/generate-event-code")
async def generate_complex_event_code(
    event_id: int = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Générer un nouveau code événement complexe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent générer des codes événement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Générer un code complexe (8 caractères alphanumériques)
    import random
    import string
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Vérifier l'unicité
    while db.query(Event).filter(Event.event_code == new_code).first():
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    event.event_code = new_code
    db.commit()
    
    return {"message": "Code événement généré", "event_code": new_code}

@app.post("/api/admin/set-event-code")
async def set_custom_event_code(
    event_id: int = Body(...),
    event_code: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Définir un code événement personnalisé (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent définir des codes événement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Vérifier l'unicité
    existing_event = db.query(Event).filter(
        Event.event_code == event_code,
        Event.id != event_id
    ).first()
    if existing_event:
        raise HTTPException(status_code=400, detail="Ce code événement est déjà utilisé")
    
    event.event_code = event_code
    db.commit()
    
    return {"message": "Code événement défini", "event_code": event_code}

# === NOUVELLES ROUTES POUR LA GESTION DES PHOTOGRAPHES ET ÉVÉNEMENTS ===

@app.delete("/api/admin/events/{event_id}")
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un événement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer un événement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Supprimer les photos associées à cet événement
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    for photo in photos:
        # Supprimer le fichier physique
        try:
            if os.path.exists(photo.file_path):
                os.remove(photo.file_path)
        except:
            pass
        # Supprimer les correspondances de visages
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
        # Supprimer la photo
        db.delete(photo)
    
    # Supprimer les associations utilisateur-événement
    db.query(UserEvent).filter(UserEvent.event_id == event_id).delete()
    
    # Supprimer l'événement
    db.delete(event)
    db.commit()
    return {"message": "Événement supprimé avec succès"}

@app.put("/api/admin/events/{event_id}")
async def admin_update_event(
    event_id: int,
    name: str = Body(...),
    event_code: str = Body(...),
    date: str = Body(None),
    photographer_id: int = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Modifier un événement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent modifier des événements")
    
    # Récupérer l'événement
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Vérifier unicité du code (sauf pour l'événement actuel)
    existing_event = db.query(Event).filter(
        Event.event_code == event_code,
        Event.id != event_id
    ).first()
    if existing_event:
        raise HTTPException(status_code=400, detail="event_code déjà utilisé")
    
    # Vérifier que le photographe existe
    photographer = db.query(User).filter_by(id=photographer_id, user_type=UserType.PHOTOGRAPHER).first()
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouvé")
    
    # Mettre à jour l'événement
    from datetime import datetime as dt
    event.name = name
    event.event_code = event_code
    event.date = dt.fromisoformat(date) if date else None
    event.photographer_id = photographer_id
    
    db.commit()
    db.refresh(event)
    
    return {"message": "Événement modifié avec succès"}

@app.delete("/api/admin/events/{event_id}")
async def admin_delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un événement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer des événements")
    
    # Récupérer l'événement
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Supprimer toutes les photos associées à cet événement
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    for photo in photos:
        # Supprimer les correspondances de visages
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
        # Supprimer le fichier physique
        if photo.file_path and os.path.exists(photo.file_path):
            os.remove(photo.file_path)
        # Supprimer l'enregistrement photo
        db.delete(photo)
    
    # Supprimer les associations utilisateur-événement
    db.query(UserEvent).filter(UserEvent.event_id == event_id).delete()
    
    # Supprimer l'événement
    db.delete(event)
    db.commit()
    
    return {"message": "Événement supprimé avec succès"}

@app.get("/api/photographer/my-event")
async def get_photographer_event(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer l'événement assigné au photographe connecté"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent accéder à cette ressource")
    
    event = db.query(Event).filter(Event.photographer_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Aucun événement assigné à ce photographe")
    
    return {
        "id": event.id,
        "name": event.name,
        "event_code": event.event_code,
        "date": event.date,
        "photographer_id": event.photographer_id
    }

# === ROUTE CATCH-ALL POUR LE FRONTEND ===

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Route catch-all pour servir le frontend HTML ou retourner une erreur 404"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Vérifier si c'est une route valide pour le frontend
    valid_frontend_routes = ["", "admin", "photographer", "register"]
    
    # Si c'est une route valide, servir le frontend approprié
    if full_path in valid_frontend_routes:
        try:
            if full_path == "admin":
                with open("static/admin.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            elif full_path == "photographer":
                with open("static/photographer.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            elif full_path == "register":
                with open("static/register.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            else:  # Route racine
                with open("static/index.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Face Recognition API</h1><p>Frontend not found</p>")
    
    # Pour toutes les autres URLs, retourner une erreur 404
    raise HTTPException(
        status_code=404, 
        detail=f"Page not found: /{full_path}"
    )