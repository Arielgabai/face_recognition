import face_recognition_patch
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import uuid
from datetime import timedelta, datetime
from sqlalchemy.exc import NoResultFound
import qrcode
from io import BytesIO
from fastapi import Request
import jwt
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import hashlib

load_dotenv()

from database import get_db, create_tables
from models import User, Photo, FaceMatch, UserType, Event, UserEvent
from schemas import UserCreate, UserLogin, Token, User as UserSchema, Photo as PhotoSchema, UserProfile
from auth import verify_password, get_password_hash, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from recognizer_factory import get_face_recognizer
from photo_optimizer import PhotoOptimizer
import requests

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

# Initialiser le recognizer (local ou Azure selon FACE_RECOGNIZER_PROVIDER)
face_recognizer = get_face_recognizer()
print(f"[FaceRecognition] Provider actif: {type(face_recognizer).__name__}")

@app.get("/api/admin/provider")
async def get_active_provider(current_user: User = Depends(get_current_user)):
    """Retourne le provider de reconnaissance actif (admin uniquement)."""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder à cette route")
    return {
        "provider_class": type(face_recognizer).__name__,
        "FACE_RECOGNIZER_PROVIDER": os.environ.get("FACE_RECOGNIZER_PROVIDER", "(unset)")
    }

@app.post("/api/admin/eval-recognition")
async def admin_eval_recognition(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Évalue la reconnaissance pour un utilisateur sur un événement.
    Body JSON: {"event_id": int, "user_id": int, "provider": "local"|"azure" (optionnel)}
    Retourne la liste des photos matchées/non matchées et les scores.
    """
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder à cette route")

    event_id = payload.get("event_id")
    user_id = payload.get("user_id")
    provider = (payload.get("provider") or "").strip().lower()
    if not event_id or not user_id:
        raise HTTPException(status_code=400, detail="event_id et user_id sont requis")

    # Sélection du provider (override optionnel)
    recognizer = face_recognizer
    if provider in {"local", "azure"}:
        try:
            if provider == "local":
                from face_recognizer import FaceRecognizer as _LocalR
                recognizer = _LocalR()
            else:
                from azure_face_recognizer import AzureFaceRecognizer as _AzureR
                recognizer = _AzureR()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Impossible d'initialiser le provider '{provider}': {str(e)}")

    # Charger l'utilisateur et les photos
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    if photos is None:
        photos = []

    matched = []
    unmatched = []
    errors = []
    for p in photos:
        photo_input = p.file_path if (p.file_path and os.path.exists(p.file_path)) else p.photo_data
        if not photo_input:
            unmatched.append({"photo_id": p.id, "filename": p.filename, "reason": "no_file_or_data"})
            continue
        try:
            matches = recognizer.process_photo_for_event(photo_input, event_id, db)
            hit = next((m for m in matches if m.get("user_id") == user_id), None)
            if hit:
                matched.append({
                    "photo_id": p.id,
                    "filename": p.filename,
                    "confidence": hit.get("confidence_score")
                })
            else:
                unmatched.append({"photo_id": p.id, "filename": p.filename})
        except Exception as e:
            errors.append({"photo_id": p.id, "filename": p.filename, "error": str(e)})

    return {
        "provider": type(recognizer).__name__,
        "event_id": event_id,
        "user_id": user_id,
        "total_photos": len(photos),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "matched": matched,
        "unmatched": unmatched,
        "errors": errors,
    }

def validate_selfie_image(image_bytes: bytes) -> None:
    """Valide qu'un selfie contient exactement un visage exploitable.

    - Rejette si aucun visage n'est détecté
    - Rejette si plusieurs visages sont détectés
    - Rejette si le visage détecté est trop petit (qualité insuffisante)
    """
    try:
        # Forcer conversion bytes
        if not isinstance(image_bytes, (bytes, bytearray)):
            image_bytes = bytes(image_bytes)

        # Charger via PIL et réduire pour limiter la RAM
        from PIL import Image, ImageOps
        import io as _io
        pil_img = Image.open(_io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        if pil_img.mode not in ("RGB", "L"):
            pil_img = pil_img.convert("RGB")
        max_dim = 1024
        w, h = pil_img.size
        scale = min(1.0, max_dim / float(max(w, h)))
        if scale < 1.0:
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        # Vers numpy
        import numpy as _np
        np_img = _np.array(pil_img)
        img_h, img_w = (np_img.shape[0], np_img.shape[1])

        # Si provider Azure actif, tenter une validation via Azure Face Detect d'abord
        try:
            provider_env = os.getenv("FACE_RECOGNIZER_PROVIDER", "local").strip().lower()
            azure_ep = os.getenv("AZURE_FACE_ENDPOINT", "").rstrip("/")
            azure_key = os.getenv("AZURE_FACE_KEY", "")
            if provider_env == "azure" and azure_ep and azure_key:
                resp = requests.post(
                    f"{azure_ep}/face/v1.0/detect?returnFaceId=true&recognitionModel=recognition_04&detectionModel=detection_03",
                    headers={
                        "Ocp-Apim-Subscription-Key": azure_key,
                        "Content-Type": "application/octet-stream",
                    },
                    data=image_bytes,
                    timeout=15,
                )
                if resp.ok:
                    faces = resp.json() or []
                    print(f"[SelfieValidation][Azure] faces_detected={len(faces)} img_w={img_w} img_h={img_h}")
                    if len(faces) == 0:
                        raise HTTPException(status_code=400, detail="Aucun visage détecté (Azure).")
                    if len(faces) > 1:
                        raise HTTPException(status_code=400, detail="Plusieurs visages détectés (Azure).")
                    rect = faces[0].get("faceRectangle") or {}
                    face_width = int(rect.get("width", 0))
                    face_height = int(rect.get("height", 0))
                    face_area = face_width * face_height
                    min_abs_area = 5000
                    min_rel_ratio = 0.008
                    min_face_area = max(min_abs_area, int((img_h * img_w) * min_rel_ratio))
                    min_side = 44
                    print(f"[SelfieValidation][Azure] face_w={face_width} face_h={face_height} face_area={face_area} thresholds: min_area={min_face_area} min_side={min_side}")
                    if face_area < min_face_area or face_width < min_side or face_height < min_side:
                        raise HTTPException(status_code=400, detail="Visage trop petit (Azure).")
                    # Azure OK → on valide et on sort
                    return
                else:
                    try:
                        print(f"[SelfieValidation][Azure] Detect failed: {resp.status_code} {resp.text}")
                    except Exception:
                        pass
        except HTTPException:
            raise
        except Exception:
            # En cas d'erreur Azure, fallback local
            pass

        # Détections multi-techniques (HOG sensible + Haar cascades)
        import face_recognition as _fr
        faces = []  # (top, right, bottom, left)

        try:
            faces_hog = _fr.face_locations(np_img, model='hog', number_of_times_to_upsample=1)
        except Exception:
            faces_hog = []
        faces.extend(faces_hog or [])

        # Si peu de visages, tenter un upsample supplémentaire
        if len(faces) <= 1:
            try:
                faces_hog2 = _fr.face_locations(np_img, model='hog', number_of_times_to_upsample=2)
            except Exception:
                faces_hog2 = []
            faces.extend(faces_hog2 or [])

        # Fallback Haar (frontal + alt2 + profil)
        try:
            import cv2 as _cv2
            gray = _cv2.cvtColor(np_img, _cv2.COLOR_RGB2GRAY)
            cascades = [
                _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
                _cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',
                _cv2.data.haarcascades + 'haarcascade_profileface.xml',
            ]
            rects_all = []
            for cpath in cascades:
                fc = _cv2.CascadeClassifier(cpath)
                if fc.empty():
                    continue
                rects = fc.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5, minSize=(36, 36))
                rects_all.extend(rects)
            # Convert to (t, r, b, l)
            haar_faces = [(int(y), int(x+w), int(y+h), int(x)) for (x, y, w, h) in rects_all]
            faces.extend(haar_faces)
        except Exception:
            pass

        # Déduplication par IoU
        def _iou(a, b):
            (t1, r1, b1, l1) = a
            (t2, r2, b2, l2) = b
            xA = max(l1, l2)
            yA = max(t1, t2)
            xB = min(r1, r2)
            yB = min(b1, b2)
            interW = max(0, xB - xA)
            interH = max(0, yB - yA)
            inter = interW * interH
            area1 = max(0, (r1 - l1)) * max(0, (b1 - t1))
            area2 = max(0, (r2 - l2)) * max(0, (b2 - t2))
            union = area1 + area2 - inter if (area1 + area2 - inter) > 0 else 1
            return inter / union

        unique = []
        for f in faces:
            if (f[1] - f[3]) <= 0 or (f[2] - f[0]) <= 0:
                continue
            if not unique:
                unique.append(f)
                continue
            if all(_iou(f, u) < 0.4 for u in unique):
                unique.append(f)

        face_locations = unique
        print(f"[SelfieValidation] faces_detected={len(face_locations)} img_w={img_w} img_h={img_h}")

        if not face_locations or len(face_locations) == 0:
            raise HTTPException(status_code=400, detail="Aucun visage détecté dans l'image. Veuillez envoyer un selfie clair de votre visage.")
        if len(face_locations) > 1:
            raise HTTPException(status_code=400, detail="Plusieurs visages détectés. Veuillez envoyer un selfie avec un seul visage.")

        # Taille minimale
        top, right, bottom, left = face_locations[0]
        face_width = max(0, right - left)
        face_height = max(0, bottom - top)
        face_area = face_width * face_height

        min_abs_area = 5000
        min_rel_ratio = 0.008  # 0.8%
        min_face_area = max(min_abs_area, int((img_h * img_w) * min_rel_ratio))
        min_side = 44
        print(f"[SelfieValidation] face_w={face_width} face_h={face_height} face_area={face_area} thresholds: min_area={min_face_area} min_side={min_side}")
        if face_area < min_face_area or face_width < min_side or face_height < min_side:
            raise HTTPException(status_code=400, detail="Visage trop petit. Approchez-vous de l'appareil et assurez-vous que le visage est net.")
    except HTTPException:
        raise
    except Exception:
        import traceback as _tb
        print("[SelfieValidation] Unexpected error:\n" + _tb.format_exc())
        raise HTTPException(status_code=400, detail="Erreur lors de la vérification du selfie. Veuillez réessayer avec une photo plus claire.")

def parse_user_type(user_type_str: str) -> UserType:
    """Convertit une chaîne quelconque (USER/user/Photographer...) vers UserType de manière sûre."""
    value = (user_type_str or '').strip().lower()
    mapping = {
        'user': UserType.USER,
        'photographer': UserType.PHOTOGRAPHER,
        'admin': UserType.ADMIN,
    }
    return mapping.get(value, UserType.USER)

def photo_to_dict(photo: Photo) -> dict:
    """Convertit un objet Photo en dictionnaire sans les donn+�es binaires"""
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

# Cr+�er les dossiers n+�cessaires
os.makedirs("static/uploads/selfies", exist_ok=True)
os.makedirs("static/uploads/photos", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Servir le frontend HTML selon le type d'utilisateur"""
    try:
        # V+�rifier si l'utilisateur est connect+� et son type
        token = request.headers.get('authorization')
        if token and token.startswith('Bearer '):
            try:
                # D+�coder le token pour obtenir le type d'utilisateur
                payload = jwt.decode(token.split(' ')[1], SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                if username:
                    # R+�cup+�rer l'utilisateur depuis la base de donn+�es
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
    """Point d'entr+�e de l'API"""
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
    """Page d'inscription pour les invit+�s avec code +�v+�nement"""
    try:
        with open("static/register.html", "r", encoding="utf-8") as f:
            content = f.read()
            # Injecter le code +�v+�nement dans le JavaScript
            content = content.replace('{{EVENT_CODE}}', event_code or '')
            return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Page d'inscription</h1><p>Page d'inscription non trouv+�e</p>")

# === AUTHENTIFICATION ===

@app.post("/api/register", response_model=Token)
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un nouvel utilisateur avec selfie et v+�rification"""
    
    # V+�rifier si l'utilisateur existe d+�j+�
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Un utilisateur avec ce nom d'utilisateur ou cet email existe d+�j+�"
        )
    
    # V+�rifier le type de fichier
    if not selfie.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit +�tre une image"
        )
    
    # V+�rifier la taille du fichier (max 5MB)
    file_size = 0
    file_data = b""
    for chunk in selfie.file:
        file_data += chunk
        file_size += len(chunk)
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=400,
                detail="Le fichier est trop volumineux (maximum 5MB)"
            )
    
    # Vérifier le selfie avec la reconnaissance faciale (qualité stricte)
    validate_selfie_image(file_data)
    
    # Cr+�er le nouvel utilisateur
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_type=UserType.USER
    )
    
    # Sauvegarder le selfie
    new_user.selfie_data = file_data
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Cr+�er un token d'acc+�s
    access_token = create_access_token(data={"sub": new_user.username})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/register-invite", response_model=UserSchema)
async def register_invite(
    user_data: UserCreate = Body(...),
    event_code: str = Body(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un invit+� +� partir d'un event_code (QR code)"""
    # V+�rifier si l'utilisateur existe d+�j+�
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username ou email d+�j+� utilis+�"
        )
    # V+�rifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="event_code invalide")
    # Cr+�er le nouvel utilisateur
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
    # Lier l'utilisateur +� l'+�v+�nement
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
    """Inscription d'un invit+� avec selfie et event_code (QR code)"""
    # V+�rifier si l'utilisateur existe d+�j+�
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username ou email d+�j+� utilis+�"
        )
    # V+�rifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="event_code invalide")
    # Cr+�er le nouvel utilisateur
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
    # Lier l'utilisateur +� l'+�v+�nement
    user_event = UserEvent(user_id=db_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    # Gérer le selfie (validation stricte + persistance)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    selfie_bytes = await file.read()
    validate_selfie_image(selfie_bytes)
    import uuid, os
    file_extension = os.path.splitext(file.filename)[1] or ".jpg"
    unique_filename = f"{db_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("static/uploads/selfies", unique_filename)
    with open(file_path, "wb") as buffer:
        buffer.write(selfie_bytes)
    db_user.selfie_path = file_path
    db_user.selfie_data = selfie_bytes
    db.commit()
    # Relancer le matching du selfie avec toutes les photos de l'événement
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
async def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """R+�cup+�rer les informations de l'utilisateur connect+� avec son +�v+�nement associ+�"""
    # R+�cup+�rer l'+�v+�nement associ+� +� l'utilisateur
    user_event = db.query(UserEvent).filter(UserEvent.user_id == current_user.id).first()
    
    if user_event:
        event = db.query(Event).filter(Event.id == user_event.event_id).first()
        if event:
            # Cr+�er un dictionnaire avec les informations de l'utilisateur et de l'+�v+�nement
            user_dict = {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "user_type": current_user.user_type,
                "is_active": current_user.is_active,
                "created_at": current_user.created_at,
                "event_name": event.name,
                "event_id": event.id,
                "event_code": event.event_code,
                "event_date": event.date
            }
            return user_dict
    
    # Si pas d'+�v+�nement associ+�, retourner juste les infos utilisateur
    return current_user

@app.get("/api/my-selfie")
async def get_my_selfie(current_user: User = Depends(get_current_user)):
    """Récupérer les informations du selfie de l'utilisateur connecté"""
    if not current_user.selfie_data:
        raise HTTPException(status_code=404, detail="Aucun selfie trouvé")
    
    return {
        "user_id": current_user.id,
        "created_at": current_user.created_at
    }

# === VALIDATION SELFIE (pré-validation côté client) ===

@app.post("/api/validate-selfie")
async def validate_selfie_endpoint(file: UploadFile = File(...), debug: bool = False):
    """Valide uniquement le selfie (sans créer de compte).
    - Retourne 200 si valide (et éventuellement des métriques si debug=true)
    - Retourne 400 sinon (et inclut des métriques si debug=true)
    """
    if not file or not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Le fichier est trop volumineux (maximum 5MB)")

    try:
        validate_selfie_image(file_bytes)
        if not debug:
            return {"valid": True}
        # En mode debug, renvoyer quelques métriques simples
        from PIL import Image, ImageOps as _ImageOps
        import io as _io
        import numpy as _np
        import face_recognition as _fr
        import cv2 as _cv2

        pil_img = Image.open(_io.BytesIO(file_bytes))
        pil_img = _ImageOps.exif_transpose(pil_img)
        if pil_img.mode not in ("RGB", "L"):
            pil_img = pil_img.convert("RGB")
        np_img = _np.array(pil_img)
        img_h, img_w = (np_img.shape[0], np_img.shape[1])
        faces_hog = []
        try:
            faces_hog = _fr.face_locations(np_img, model='hog', number_of_times_to_upsample=1) or []
        except Exception:
            faces_hog = []
        gray = _cv2.cvtColor(np_img, _cv2.COLOR_RGB2GRAY)
        cascade_path = _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        rects = _cv2.CascadeClassifier(cascade_path).detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(36, 36))
        faces_haar = [(int(y), int(x+w), int(y+h), int(x)) for (x, y, w, h) in rects]
        faces_total = len(faces_hog) + len(faces_haar)
        return {"valid": True, "debug": {"img_w": img_w, "img_h": img_h, "faces_hog": len(faces_hog), "faces_haar": len(faces_haar), "faces_total": faces_total}}
    except HTTPException as e:
        if not debug:
            raise
        # En mode debug, tenter d'expliquer pourquoi
        try:
            from PIL import Image, ImageOps as _ImageOps
            import io as _io
            import numpy as _np
            import face_recognition as _fr
            import cv2 as _cv2
            pil_img = Image.open(_io.BytesIO(file_bytes))
            pil_img = _ImageOps.exif_transpose(pil_img)
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")
            np_img = _np.array(pil_img)
            img_h, img_w = (np_img.shape[0], np_img.shape[1])
            faces_hog = []
            try:
                faces_hog = _fr.face_locations(np_img, model='hog', number_of_times_to_upsample=2) or []
            except Exception:
                faces_hog = []
            gray = _cv2.cvtColor(np_img, _cv2.COLOR_RGB2GRAY)
            cascade_path = _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            rects = _cv2.CascadeClassifier(cascade_path).detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5, minSize=(36, 36))
            faces_haar = [(int(y), int(x+w), int(y+h), int(x)) for (x, y, w, h) in rects]
            faces_total = len(faces_hog) + len(faces_haar)
            return Response(status_code=400, content=_io.BytesIO(_np.array([])).getvalue(), media_type="application/json", headers={
            })
        except Exception:
            raise e

@app.delete("/api/my-selfie")
async def delete_my_selfie(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer le selfie de l'utilisateur connecté et les correspondances associées"""
    if not current_user.selfie_data:
        raise HTTPException(status_code=404, detail="Aucun selfie à supprimer")

    # Supprimer les donn+�es binaires de la base utilisateur
    current_user.selfie_data = None
    current_user.selfie_path = None
    db.commit()
    # Supprimer tous les FaceMatch li+�s +� cet utilisateur
    db.query(FaceMatch).filter(FaceMatch.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Selfie supprimé avec succès"}

# === GESTION DES SELFIES ===

@app.post("/api/upload-selfie")
async def upload_selfie(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    strict: bool = True,
):
    """Upload d'un selfie pour l'utilisateur"""
    if current_user.user_type == UserType.PHOTOGRAPHER:
        raise HTTPException(
            status_code=403, 
            detail="Les photographes ne peuvent pas uploader de selfies"
        )
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit +�tre une image")
    
    # Lire les données binaires du fichier
    file_data = await file.read()
    # Valider le selfie (1 visage, taille minimale) sauf si désactivée
    strict_env = os.getenv("SELFIE_VALIDATION_STRICT", "true").strip().lower() not in {"false", "0", "no"}
    if strict and strict_env:
        validate_selfie_image(file_data)

    # Mettre à jour l'utilisateur avec les données binaires
    current_user.selfie_data = file_data
    current_user.selfie_path = None  # Plus besoin du chemin de fichier
    db.commit()

    # Supprimer les anciennes correspondances pour cet utilisateur sur tous ses événements
    user_events = db.query(UserEvent).filter(UserEvent.user_id == current_user.id).all()
    from sqlalchemy import and_
    total_deleted = 0
    for ue in user_events:
        photo_ids = [p.id for p in db.query(Photo).filter(Photo.event_id == ue.event_id).all()]
        if photo_ids:
            deleted = db.query(FaceMatch).filter(
                and_(FaceMatch.user_id == current_user.id, FaceMatch.photo_id.in_(photo_ids))
            ).delete(synchronize_session=False)
            try:
                total_deleted += int(deleted or 0)
            except Exception:
                pass
    db.commit()

    # Relancer le matching pour chaque événement de l'utilisateur
    match_count = 0
    for ue in user_events:
        try:
            if hasattr(face_recognizer, 'match_user_selfie_with_photos_event'):
                match_count += face_recognizer.match_user_selfie_with_photos_event(current_user, ue.event_id, db)
            else:
                match_count += face_recognizer.match_user_selfie_with_photos(current_user, db)
        except Exception:
            pass
    print(f"[SelfieUpdate] deleted_matches={total_deleted} new_matches={match_count} for user_id={current_user.id}")
    return {"message": "Selfie upload+�e avec succ+�s", "deleted": total_deleted, "matches": match_count}

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
        temp_path = f"./temp_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
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
        "message": f"{len(uploaded_photos)} photos upload+�es et trait+�es avec succ+�s",
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
        raise HTTPException(status_code=400, detail="Le fichier doit +�tre une image")
    
    # Sauvegarder temporairement le fichier
    temp_path = f"./temp_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Traiter la photo avec reconnaissance faciale
        photo = face_recognizer.process_and_save_photo(
            temp_path, file.filename, current_user.id, db
        )
        
        return {
            "message": "Photo upload+�e et trait+�e avec succ+�s",
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
    """R+�cup+�rer toutes les photos o+� l'utilisateur appara+�t pour son +�v+�nement principal"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent acc+�der +� cette route")
    
    # Trouver le premier +�v+�nement de l'utilisateur (+�v+�nement principal)
    user_event = db.query(UserEvent).filter_by(user_id=current_user.id).first()
    if not user_event:
        raise HTTPException(status_code=404, detail="Aucun +�v+�nement associ+� +� cet utilisateur")
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
    """R+�cup+�rer toutes les photos de l'+�v+�nement principal de l'utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent acc+�der +� cette route")
    
    user_event = db.query(UserEvent).filter_by(user_id=current_user.id).first()
    if not user_event:
        raise HTTPException(status_code=404, detail="Aucun +�v+�nement associ+� +� cet utilisateur")
    event_id = user_event.event_id
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les m+�tadonn+�es, pas les donn+�es binaires
    return [photo_to_dict(photo) for photo in photos]

@app.get("/api/my-uploaded-photos", response_model=List[PhotoSchema])
async def get_my_uploaded_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer les photos upload+�es par le photographe connect+�"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent acc+�der +� cette route")
    
    photos = db.query(Photo).filter(
        Photo.photographer_id == current_user.id,
        Photo.photo_type == "uploaded"
    ).all()
    
    # Retourner seulement les m+�tadonn+�es, pas les donn+�es binaires
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
    """R+�cup+�rer le profil complet de l'utilisateur"""
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
    """Servir une image depuis les dossiers static (pour compatibilit+�)"""
    # Chercher dans diff+�rents dossiers possibles
    possible_paths = [
        os.path.join("static", filename),
        os.path.join("static/uploads/photos", filename),
        os.path.join("static/uploads/selfies", filename)
    ]
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    # Si aucune image n'est trouv+�e
    raise HTTPException(status_code=404, detail=f"Image non trouv+�e: {filename}")

@app.get("/api/photo/{photo_id}")
async def get_photo_by_id(
    photo_id: int,
    db: Session = Depends(get_db)
):
    """Servir une photo depuis la base de donn+�es par son ID"""
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo non trouv+�e")
    
    if not photo.photo_data:
        raise HTTPException(status_code=404, detail="Donn+�es de photo non disponibles")
    
    # Retourner les donn+�es binaires avec le bon type MIME
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
    """Servir un selfie depuis la base de données par l'ID utilisateur"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouv+�")
    
    if not user.selfie_data:
        raise HTTPException(status_code=404, detail="Selfie non disponible")
    
    # Retourner les donn+�es binaires avec le bon type MIME
    return Response(
        content=user.selfie_data,
        media_type="image/jpeg",  # Par d+�faut pour les selfies
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
    
    # R+�cup+�rer la photo
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo non trouv+�e")
    
    # V+�rifier que le photographe est bien le propri+�taire de la photo
    if photo.photographer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres photos")
    
    try:
        # Supprimer les correspondances de visages associ+�es
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo_id).delete()
        
        # Supprimer l'enregistrement de la base de donn+�es
        db.delete(photo)
        db.commit()
        
        return {"message": "Photo supprim+�e avec succ+�s"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

@app.delete("/api/photos")
async def delete_multiple_photos(
    photo_ids: str,  # Recevoir comme string s+�par+�e par des virgules
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer plusieurs photos (photographes seulement)"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent supprimer des photos")
    
    if not photo_ids:
        raise HTTPException(status_code=400, detail="Aucune photo s+�lectionn+�e")
    
    # Convertir la string en liste d'IDs
    try:
        photo_id_list = [int(id.strip()) for id in photo_ids.split(',') if id.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Format d'ID invalide")
    
    if not photo_id_list:
        raise HTTPException(status_code=400, detail="Aucune photo s+�lectionn+�e")
    
    # R+�cup+�rer les photos du photographe
    photos = db.query(Photo).filter(
        Photo.id.in_(photo_id_list),
        Photo.photographer_id == current_user.id
    ).all()
    
    if not photos:
        raise HTTPException(status_code=404, detail="Aucune photo trouv+�e")
    
    deleted_count = 0
    try:
        for photo in photos:
            # Supprimer les correspondances de visages associ+�es
            db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
            
            # Supprimer l'enregistrement de la base de donn+�es
            db.delete(photo)
            deleted_count += 1
        
        db.commit()
        return {"message": f"{deleted_count} photos supprim+�es avec succ+�s"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

# === ADMINISTRATION ===

@app.get("/api/admin/photographers")
async def admin_get_photographers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer tous les photographes (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent acc+�der +� cette route")
    
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
    """Cr+�er un nouveau photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent cr+�er des photographes")
    
    # V+�rifier si l'utilisateur existe d+�j+�
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email d+�j+� utilis+�")
    
    # Cr+�er le nouveau photographe
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
    
    return {"message": "Photographe cr+�+� avec succ+�s", "photographer_id": db_photographer.id}

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
    
    # R+�cup+�rer le photographe
    photographer = db.query(User).filter(
        User.id == photographer_id,
        User.user_type == UserType.PHOTOGRAPHER
    ).first()
    
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouv+�")
    
    # V+�rifier si le nouveau username/email n'est pas d+�j+� utilis+� par un autre utilisateur
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email),
        User.id != photographer_id
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email d+�j+� utilis+�")
    
    # Mettre +� jour le photographe
    photographer.username = username
    photographer.email = email
    db.commit()
    db.refresh(photographer)
    
    return {"message": "Photographe modifi+� avec succ+�s"}

@app.delete("/api/admin/photographers/{photographer_id}")
async def admin_delete_photographer(
    photographer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer des photographes")
    
    # R+�cup+�rer le photographe
    photographer = db.query(User).filter(
        User.id == photographer_id,
        User.user_type == UserType.PHOTOGRAPHER
    ).first()
    
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouv+�")
    
    # V+�rifier s'il y a des +�v+�nements associ+�s
    events = db.query(Event).filter(Event.photographer_id == photographer_id).all()
    if events:
        event_names = [event.name for event in events]
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer le photographe car il est associ+� aux +�v+�nements: {', '.join(event_names)}"
        )
    
    # Supprimer les photos upload+�es par ce photographe
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
    
    return {"message": "Photographe supprim+� avec succ+�s"}

@app.get("/api/admin/events")
async def admin_get_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer tous les +�v+�nements (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent acc+�der +� cette route")
    
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
    """Cr+�er un +�v+�nement (mariage) et l'assigner +� un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent cr+�er des +�v+�nements")
    # V+�rifier unicit+� du code
    if db.query(Event).filter_by(event_code=event_code).first():
        raise HTTPException(status_code=400, detail="event_code d+�j+� utilis+�")
    # V+�rifier que le photographe existe
    photographer = db.query(User).filter_by(id=photographer_id, user_type=UserType.PHOTOGRAPHER).first()
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouv+�")
    # Cr+�er l'+�v+�nement
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
    return {"message": "+�v+�nement cr+�+�", "event_id": event.id, "event_code": event.event_code}

@app.post("/api/admin/register-admin")
async def register_admin(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    """Cr+�er le premier compte admin (seulement si aucun admin n'existe)"""
    from models import UserType
    existing_admin = db.query(User).filter(User.user_type == UserType.ADMIN).first()
    if existing_admin:
        raise HTTPException(status_code=403, detail="Un admin existe d+�j+�")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username ou email d+�j+� utilis+�")
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
    return {"message": "Admin cr+�+�", "user_id": db_user.id}

@app.post("/api/admin/create-photographer")
async def create_photographer(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cr+�er un photographe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent cr+�er un photographe")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username ou email d+�j+� utilis+�")
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
    return {"message": "Photographe cr+�+�", "user_id": db_user.id}

@app.get("/api/admin/event-qr/{event_code}")
async def generate_event_qr(event_code: str, current_user: User = Depends(get_current_user)):
    """G+�n+�rer un QR code pour l'inscription +� un +�v+�nement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent g+�n+�rer un QR code")
    
    # V+�rifier que l'+�v+�nement existe
    db = next(get_db())
    event = db.query(Event).filter(Event.event_code == event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # G+�n+�rer l'URL d'inscription vers le domaine de production
    url = f"https://facerecognition-d0r8.onrender.com/register?event_code={event_code}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# === NOUVELLES ROUTES POUR LA GESTION DES +�V+�NEMENTS ===

@app.get("/api/photographer/events")
async def get_photographer_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer tous les +�v+�nements du photographe connect+�"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent acc+�der +� cette route")
    
    events = db.query(Event).filter(Event.photographer_id == current_user.id).all()
    return events

@app.get("/api/photographer/events/{event_id}/photos")
async def get_event_photos(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer toutes les photos d'un +�v+�nement sp+�cifique pour un photographe"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent acc+�der +� cette route")
    
    # V+�rifier que l'+�v+�nement appartient au photographe
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.photographer_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les m+�tadonn+�es, pas les donn+�es binaires
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
    """Upload de photos pour un +�v+�nement sp+�cifique"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent uploader des photos")
    
    # V+�rifier que l'+�v+�nement appartient au photographe
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.photographer_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    uploaded_photos = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        
        # Sauvegarder temporairement le fichier
        temp_path = f"./temp_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Traiter la photo avec reconnaissance faciale pour l'+�v+�nement sp+�cifique
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
        "message": f"{len(uploaded_photos)} photos upload+�es et trait+�es avec succ+�s",
        "uploaded_photos": uploaded_photos
    }

@app.get("/api/user/events")
async def get_user_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer tous les +�v+�nements auxquels l'utilisateur est inscrit"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent acc+�der +� cette route")
    
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
    """R+�cup+�rer les photos d'un +�v+�nement sp+�cifique pour un utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent acc+�der +� cette route")
    
    # V+�rifier que l'utilisateur est inscrit +� cet +�v+�nement
    user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event_id
    ).first()
    
    if not user_event:
        raise HTTPException(status_code=403, detail="Vous n'+�tes pas inscrit +� cet +�v+�nement")
    
    # R+�cup+�rer les photos o+� l'utilisateur appara+�t dans cet +�v+�nement
    photos = db.query(Photo).join(FaceMatch).filter(
        FaceMatch.user_id == current_user.id,
        FaceMatch.photo_id == Photo.id,
        Photo.event_id == event_id
    ).all()
    
    # Retourner seulement les m+�tadonn+�es, pas les donn+�es binaires
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
    """R+�cup+�rer toutes les photos d'un +�v+�nement pour un utilisateur"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent acc+�der +� cette route")
    
    # V+�rifier que l'utilisateur est inscrit +� cet +�v+�nement
    user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event_id
    ).first()
    
    if not user_event:
        raise HTTPException(status_code=403, detail="Vous n'+�tes pas inscrit +� cet +�v+�nement")
    
    # R+�cup+�rer toutes les photos de l'+�v+�nement
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    
    # Retourner seulement les m+�tadonn+�es, pas les donn+�es binaires
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

# === ROUTES POUR LES CODES +�V+�NEMENT MANUELS ===

@app.post("/api/register-with-event-code")
async def register_with_event_code(
    user_data: UserCreate = Body(...),
    event_code: str = Body(...),
    db: Session = Depends(get_db)
):
    """Inscription d'un utilisateur avec un code +�v+�nement saisi manuellement"""
    # V+�rifier si l'utilisateur existe d+�j+�
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username ou email d+�j+� utilis+�")
    
    # V+�rifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Code +�v+�nement invalide")
    
    # Cr+�er le nouvel utilisateur
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
    
    # Lier l'utilisateur +� l'+�v+�nement
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
    """Rejoindre un +�v+�nement avec un code (pour utilisateurs d+�j+� inscrits)"""
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent rejoindre des +�v+�nements")
    
    # V+�rifier l'event_code
    event = db.query(Event).filter_by(event_code=event_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Code +�v+�nement invalide")
    
    # V+�rifier si l'utilisateur est d+�j+� inscrit +� cet +�v+�nement
    existing_user_event = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event.id
    ).first()
    
    if existing_user_event:
        raise HTTPException(status_code=400, detail="Vous +�tes d+�j+� inscrit +� cet +�v+�nement")
    
    # Inscrire l'utilisateur +� l'+�v+�nement
    user_event = UserEvent(user_id=current_user.id, event_id=event.id)
    db.add(user_event)
    db.commit()
    
    return {"message": f"Inscrit avec succ+�s +� l'+�v+�nement {event.name}"}

# === ROUTES ADMIN POUR CR+�ER DES CODES +�V+�NEMENT COMPLEXES ===

@app.post("/api/admin/generate-event-code")
async def generate_complex_event_code(
    event_id: int = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """G+�n+�rer un nouveau code +�v+�nement complexe (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent g+�n+�rer des codes +�v+�nement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # G+�n+�rer un code complexe (8 caract+�res alphanum+�riques)
    import random
    import string
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # V+�rifier l'unicit+�
    while db.query(Event).filter(Event.event_code == new_code).first():
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    event.event_code = new_code
    db.commit()
    
    return {"message": "Code +�v+�nement g+�n+�r+�", "event_code": new_code}

@app.post("/api/admin/set-event-code")
async def set_custom_event_code(
    event_id: int = Body(...),
    event_code: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """D+�finir un code +�v+�nement personnalis+� (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent d+�finir des codes +�v+�nement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # V+�rifier l'unicit+�
    existing_event = db.query(Event).filter(
        Event.event_code == event_code,
        Event.id != event_id
    ).first()
    if existing_event:
        raise HTTPException(status_code=400, detail="Ce code +�v+�nement est d+�j+� utilis+�")
    
    event.event_code = event_code
    db.commit()
    
    return {"message": "Code +�v+�nement d+�fini", "event_code": event_code}

# === NOUVELLES ROUTES POUR LA GESTION DES PHOTOGRAPHES ET +�V+�NEMENTS ===

@app.delete("/api/admin/events/{event_id}")
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un +�v+�nement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer un +�v+�nement")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # Supprimer les photos associ+�es +� cet +�v+�nement
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
    
    # Supprimer les associations utilisateur-+�v+�nement
    db.query(UserEvent).filter(UserEvent.event_id == event_id).delete()
    
    # Supprimer l'+�v+�nement
    db.delete(event)
    db.commit()
    return {"message": "+�v+�nement supprim+� avec succ+�s"}

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
    """Modifier un +�v+�nement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent modifier des +�v+�nements")
    
    # R+�cup+�rer l'+�v+�nement
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # V+�rifier unicit+� du code (sauf pour l'+�v+�nement actuel)
    existing_event = db.query(Event).filter(
        Event.event_code == event_code,
        Event.id != event_id
    ).first()
    if existing_event:
        raise HTTPException(status_code=400, detail="event_code d+�j+� utilis+�")
    
    # V+�rifier que le photographe existe
    photographer = db.query(User).filter_by(id=photographer_id, user_type=UserType.PHOTOGRAPHER).first()
    if not photographer:
        raise HTTPException(status_code=404, detail="Photographe non trouv+�")
    
    # Mettre +� jour l'+�v+�nement
    from datetime import datetime as dt
    event.name = name
    event.event_code = event_code
    event.date = dt.fromisoformat(date) if date else None
    event.photographer_id = photographer_id
    
    db.commit()
    db.refresh(event)
    
    return {"message": "+�v+�nement modifi+� avec succ+�s"}

@app.delete("/api/admin/events/{event_id}")
async def admin_delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un +�v+�nement (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent supprimer des +�v+�nements")
    
    # R+�cup+�rer l'+�v+�nement
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="+�v+�nement non trouv+�")
    
    # Supprimer toutes les photos associ+�es +� cet +�v+�nement
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    for photo in photos:
        # Supprimer les correspondances de visages
        db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
        # Supprimer le fichier physique
        if photo.file_path and os.path.exists(photo.file_path):
            os.remove(photo.file_path)
        # Supprimer l'enregistrement photo
        db.delete(photo)
    
    # Supprimer les associations utilisateur-+�v+�nement
    db.query(UserEvent).filter(UserEvent.event_id == event_id).delete()
    
    # Supprimer l'+�v+�nement
    db.delete(event)
    db.commit()
    
    return {"message": "+�v+�nement supprim+� avec succ+�s"}

@app.get("/api/photographer/my-event")
async def get_photographer_event(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """R+�cup+�rer l'+�v+�nement assign+� au photographe connect+�"""
    if current_user.user_type != UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Seuls les photographes peuvent acc+�der +� cette ressource")
    
    event = db.query(Event).filter(Event.photographer_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Aucun +�v+�nement assign+� +� ce photographe")
    
    return {
        "id": event.id,
        "name": event.name,
        "event_code": event.event_code,
        "date": event.date,
        "photographer_id": event.photographer_id
    }

# === ENDPOINTS D'OPTIMISATION PHOTOS (ADMIN) ===

@app.get("/api/admin/photo-optimization/stats")
async def get_photo_optimization_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les statistiques d'optimisation des photos (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder aux statistiques")
    
    # Récupérer toutes les photos avec métadonnées d'optimisation
    photos = db.query(Photo).filter(
        Photo.original_size.isnot(None),
        Photo.compressed_size.isnot(None)
    ).all()
    
    if not photos:
        return {
            "total_photos": 0,
            "total_original_size_mb": 0,
            "total_compressed_size_mb": 0,
            "total_space_saved_mb": 0,
            "average_compression_ratio": 0,
            "photos_by_quality": {},
            "expired_photos_count": 0
        }
    
    # Calculer les statistiques
    photos_data = []
    for photo in photos:
        photos_data.append({
            'original_size': photo.original_size,
            'compressed_size': photo.compressed_size,
            'expires_at': photo.expires_at
        })
    
    stats = PhotoOptimizer.calculate_storage_savings(photos_data)
    expired_count = PhotoOptimizer.get_expired_photos_count(photos_data)
    
    # Statistiques par niveau de qualité
    quality_stats = {}
    for photo in photos:
        quality = photo.quality_level or 85
        if quality not in quality_stats:
            quality_stats[quality] = 0
        quality_stats[quality] += 1
    
    return {
        "total_photos": stats['total_photos'],
        "total_original_size_mb": stats['original_size_mb'],
        "total_compressed_size_mb": stats['compressed_size_mb'],
        "total_space_saved_mb": stats['space_saved_mb'],
        "average_compression_ratio": stats['average_compression_ratio'],
        "photos_by_quality": quality_stats,
        "expired_photos_count": expired_count
    }

@app.get("/api/admin/photo-optimization/estimate")
async def estimate_photo_compression(
    file_size: int,
    quality_profile: str = "high",
    current_user: User = Depends(get_current_user)
):
    """Estimer la compression pour une taille de fichier donnée (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder à cette fonctionnalité")
    
    if quality_profile not in PhotoOptimizer.QUALITY_PROFILES:
        raise HTTPException(status_code=400, detail="Profil de qualité invalide")
    
    estimation = PhotoOptimizer.estimate_compression(file_size, quality_profile)
    
    return {
        "original_size_mb": round(estimation['original_size'] / (1024 * 1024), 2),
        "estimated_compressed_size_mb": round(estimation['estimated_compressed_size'] / (1024 * 1024), 2),
        "estimated_space_saved_mb": round(estimation['estimated_space_saved'] / (1024 * 1024), 2),
        "estimated_compression_ratio": estimation['estimated_compression_ratio'],
        "quality_profile": estimation['quality_profile']
    }

@app.post("/api/admin/photo-optimization/cleanup-expired")
async def cleanup_expired_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nettoyer les photos expirées (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent nettoyer les photos")
    
    from datetime import datetime
    now = datetime.utcnow()
    
    # Trouver les photos expirées
    expired_photos = db.query(Photo).filter(
        Photo.expires_at.isnot(None),
        Photo.expires_at < now
    ).all()
    
    if not expired_photos:
        return {
            "message": "Aucune photo expirée trouvée",
            "deleted_count": 0,
            "space_freed_mb": 0
        }
    
    deleted_count = 0
    space_freed = 0
    
    try:
        for photo in expired_photos:
            # Calculer l'espace libéré
            if photo.compressed_size:
                space_freed += photo.compressed_size
            
            # Supprimer les correspondances de visages
            db.query(FaceMatch).filter(FaceMatch.photo_id == photo.id).delete()
            
            # Supprimer la photo
            db.delete(photo)
            deleted_count += 1
        
        db.commit()
        
        return {
            "message": f"{deleted_count} photos expirées supprimées avec succès",
            "deleted_count": deleted_count,
            "space_freed_mb": round(space_freed / (1024 * 1024), 2)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")

@app.get("/api/admin/photo-optimization/profiles")
async def get_quality_profiles(
    current_user: User = Depends(get_current_user)
):
    """Récupérer les profils de qualité disponibles (admin uniquement)"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent accéder aux profils")
    
    return {
        "profiles": PhotoOptimizer.QUALITY_PROFILES,
        "default_profile": "high",
        "default_retention_days": PhotoOptimizer.DEFAULT_RETENTION_DAYS
    }

# === ROUTE CATCH-ALL POUR LE FRONTEND ===

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Route catch-all pour servir le frontend HTML ou retourner une erreur 404"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # V+�rifier si c'est une route valide pour le frontend
    valid_frontend_routes = ["", "admin", "photographer", "register"]
    
    # Si c'est une route valide, servir le frontend appropri+�
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

# === R+�INITIALISATION MOT DE PASSE ===

@app.post("/api/password-reset")
async def request_password_reset(
    request_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Demander une r+�initialisation de mot de passe par email"""
    email = request_data.get('email')
    
    if not email:
        raise HTTPException(status_code=400, detail="Email requis")
    
    # Chercher l'utilisateur par email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Pour des raisons de s+�curit+�, on renvoie toujours le m+�me message
        return {"message": "Si cette adresse email existe, un lien de r+�initialisation a +�t+� envoy+�"}
    
    # Pour l'instant, on simule l'envoi (vous pouvez activer l'email plus tard)
    print(f"Demande de r+�initialisation pour: {email}")
    return {"message": "Un email de r+�initialisation a +�t+� envoy+�"}

@app.post("/api/admin/migrate-photo-optimization")
async def migrate_photo_optimization_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint pour exécuter la migration des colonnes d'optimisation photo"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import text, inspect
        
        migration_log = []
        migration_log.append("🔄 Début de la migration pour l'optimisation photos...")
        
        # Obtenir l'inspecteur pour vérifier les colonnes existantes
        inspector = inspect(db.bind)
        existing_columns = [col['name'] for col in inspector.get_columns('photos')]
        
        migration_log.append(f"📋 Colonnes existantes: {existing_columns}")
        
        new_columns_definitions = {
            'original_size': 'INTEGER',
            'compressed_size': 'INTEGER', 
            'compression_ratio': 'REAL',
            'retention_days': 'INTEGER DEFAULT 30',
            'expires_at': 'TIMESTAMP',
            'quality_level': 'VARCHAR(20) DEFAULT \'medium\''
        }
        
        # Ajouter les colonnes manquantes
        for column_name, column_def in new_columns_definitions.items():
            if column_name not in existing_columns:
                migration_log.append(f"📝 Ajout de la colonne '{column_name}'...")
                
                try:
                    # Utiliser SQLAlchemy pour exécuter la commande ALTER TABLE
                    alter_query = text(f"ALTER TABLE photos ADD COLUMN {column_name} {column_def}")
                    db.execute(alter_query)
                    db.commit()
                    migration_log.append(f"✅ Colonne '{column_name}' ajoutée avec succès")
                except Exception as col_error:
                    migration_log.append(f"❌ Erreur ajout '{column_name}': {str(col_error)}")
            else:
                migration_log.append(f"⏭️ Colonne '{column_name}' existe déjà")
        
        # Mettre à jour les photos existantes avec des valeurs par défaut
        migration_log.append("🔄 Mise à jour des photos existantes...")
        
        # Compter les photos à mettre à jour
        count_query = text("SELECT COUNT(*) FROM photos WHERE original_size IS NULL")
        photos_to_update_count = db.execute(count_query).scalar()
        
        migration_log.append(f"📊 {photos_to_update_count} photos à mettre à jour")
        
        if photos_to_update_count > 0:
            # Obtenir les photos à mettre à jour (avec limite pour éviter les timeouts)
            photos_query = text("SELECT id, LENGTH(photo_data) as data_size FROM photos WHERE original_size IS NULL LIMIT 100")
            photos_result = db.execute(photos_query).fetchall()
            
            for photo_row in photos_result:
                photo_id = photo_row[0]
                data_size = photo_row[1] or 0
                
                # Calculer la date d'expiration (30 jours par défaut)
                expires_at = datetime.now() + timedelta(days=30)
                
                update_query = text("""
                    UPDATE photos 
                    SET original_size = :original_size,
                        compressed_size = :compressed_size,
                        compression_ratio = 1.0,
                        retention_days = 30,
                        expires_at = :expires_at,
                        quality_level = 'medium'
                    WHERE id = :photo_id
                """)
                
                db.execute(update_query, {
                    'original_size': data_size,
                    'compressed_size': data_size,
                    'expires_at': expires_at,
                    'photo_id': photo_id
                })
            
            db.commit()
            migration_log.append(f"✅ {len(photos_result)} photos mises à jour")
        
        # Vérifier le résultat final
        final_count_query = text("SELECT COUNT(*) FROM photos WHERE original_size IS NOT NULL")
        updated_count = db.execute(final_count_query).scalar()
        
        migration_log.append(f"📈 Total photos avec métadonnées d'optimisation : {updated_count}")
        migration_log.append("🎉 Migration terminée avec succès !")
        
        return {
            "success": True,
            "message": "Migration exécutée avec succès",
            "log": migration_log,
            "photos_updated": photos_to_update_count,
            "total_photos_with_metadata": updated_count
        }
        
    except Exception as e:
        migration_log.append(f"❌ Erreur lors de la migration : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la migration : {str(e)}")

@app.post("/api/admin/reload-models")
async def reload_models_endpoint(current_user: User = Depends(get_current_user)):
    """Endpoint pour recharger les modèles SQLAlchemy après migration"""
    try:
        from sqlalchemy import inspect
        from models import Photo, User, Event  # Force reload
        
        reload_log = []
        reload_log.append("🔄 Rechargement des modèles SQLAlchemy...")
        
        # Forcer la réflexion de la table
        db = next(get_db())
        inspector = inspect(db.bind)
        
        # Vérifier que les nouvelles colonnes sont détectées
        photo_columns = [col['name'] for col in inspector.get_columns('photos')]
        reload_log.append(f"📋 Colonnes détectées dans 'photos': {photo_columns}")
        
        # Vérifier si les attributs sont maintenant disponibles
        optimization_columns = ['original_size', 'compressed_size', 'compression_ratio', 'retention_days', 'expires_at', 'quality_level']
        
        detected_optimization_columns = []
        for col in optimization_columns:
            if col in photo_columns:
                detected_optimization_columns.append(col)
        
        reload_log.append(f"✅ Colonnes d'optimisation détectées: {detected_optimization_columns}")
        
        if len(detected_optimization_columns) == len(optimization_columns):
            reload_log.append("🎉 Toutes les colonnes d'optimisation sont présentes !")
            reload_log.append("📊 Les statistiques d'optimisation devraient maintenant fonctionner")
            
            return {
                "success": True,
                "message": "Modèles rechargés avec succès",
                "log": reload_log,
                "optimization_columns_detected": len(detected_optimization_columns),
                "ready_for_stats": True
            }
        else:
            missing = set(optimization_columns) - set(detected_optimization_columns)
            reload_log.append(f"⚠️ Colonnes manquantes: {list(missing)}")
            
            return {
                "success": False,
                "message": "Certaines colonnes d'optimisation sont manquantes",
                "log": reload_log,
                "optimization_columns_detected": len(detected_optimization_columns),
                "missing_columns": list(missing),
                "ready_for_stats": False
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur lors du rechargement : {str(e)}",
            "log": [f"❌ Erreur: {str(e)}"],
            "ready_for_stats": False
        }
