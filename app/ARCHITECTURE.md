# Architecture de l'Application FindMe - Face Recognition

## Vue d'ensemble

**FindMe** est une application de reconnaissance faciale permettant aux photographes d'événements de permettre aux participants de retrouver automatiquement les photos où ils apparaissent.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS App Runner                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Gunicorn + UvicornWorker                      │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      FastAPI Application                        │  │  │
│  │  │                                                                 │  │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │  │  │
│  │  │  │   API    │  │  Auth    │  │  Models  │  │   Services   │    │  │  │
│  │  │  │ Endpoints│  │  (JWT)   │  │  (ORM)   │  │  (Business)  │    │  │  │
│  │  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │  │  │
│  │  │       │             │             │               │            │  │  │
│  │  │       └─────────────┴─────────────┴───────────────┘            │  │  │
│  │  │                           │                                     │  │  │
│  │  │              ┌────────────┴────────────┐                       │  │  │
│  │  │              │     Photo Worker SQS    │ (Thread daemon)       │  │  │
│  │  │              └────────────┬────────────┘                       │  │  │
│  │  └───────────────────────────┼─────────────────────────────────────┘  │  │
│  └───────────────────────────────┼───────────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   AWS S3        │    │ AWS Rekognition │
│   (Database)    │    │   (Photos)      │    │ (Face Matching) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                  │
                                  ▼
                       ┌─────────────────┐
                       │    AWS SQS      │
                       │  (Job Queue)    │
                       └─────────────────┘
```

---

## 1. Cycle de démarrage de l'application

L'ordre de démarrage est **critique** car les modules lisent `os.environ` au moment de l'import.

```
main.py (point d'entrée)
    │
    ├── 1. import face_recognition_patch    # Patch dlib (aucune dépendance config)
    │
    ├── 2. load_ssm_parameters()            # Charge SSM → os.environ
    │       └── Lit APP_CONFIG_PREFIX, AWS_REGION
    │       └── Injecte les paramètres SSM dans os.environ
    │
    ├── 3. load_dotenv()                    # Charge .env (SSM a priorité)
    │
    ├── 4. from database import ...         # Crée engine SQLAlchemy
    │       └── Lit DATABASE_URL, DB_POOL_SIZE, etc.
    │
    ├── 5. from settings import settings    # Crée Settings Pydantic
    │       └── Lit PHOTO_BUCKET_NAME, PHOTO_SQS_QUEUE_URL, etc.
    │
    ├── 6. Création de l'app FastAPI        # Routes, middleware, etc.
    │
    └── 7. @app.on_event("startup")         # Événements de démarrage
            ├── create_tables()             # Migration auto des tables
            ├── start_photo_worker()        # Démarre le worker SQS (si configuré)
            └── start_gdrive_listeners()    # Démarre les listeners Google Drive
```

---

## 2. Structure des fichiers

```
face_recognition/app/
│
├── main.py                     # Point d'entrée FastAPI (6000+ lignes)
│                               # Contient TOUS les endpoints API
│
├── ─────────── CONFIGURATION ───────────
├── ssm_loader.py               # Chargement des paramètres depuis AWS SSM
├── settings.py                 # Configuration centralisée (Pydantic Settings)
├── database.py                 # Configuration SQLAlchemy + pool de connexions
├── gunicorn_config.py          # Configuration du serveur Gunicorn
│
├── ─────────── MODÈLES & SCHÉMAS ───────────
├── models.py                   # Modèles SQLAlchemy (ORM)
├── schemas.py                  # Schémas Pydantic (validation API)
│
├── ─────────── AUTHENTIFICATION ───────────
├── auth.py                     # JWT, hachage bcrypt, OAuth2
│
├── ─────────── RECONNAISSANCE FACIALE ───────────
├── recognizer_factory.py       # Factory pour choisir le provider
├── aws_face_recognizer.py      # Provider AWS Rekognition (production)
├── azure_face_recognizer.py    # Provider Azure Face API (alternatif)
├── face_recognizer.py          # Provider local dlib (dev/fallback)
├── face_recognition_patch.py   # Patch pour dlib/face_recognition
│
├── ─────────── TRAITEMENT DES PHOTOS ───────────
├── photo_worker_sqs.py         # Worker SQS (nouveau, prod-ready)
├── photo_queue.py              # Queue en mémoire (legacy, fallback)
├── photo_optimizer.py          # Compression et optimisation des images
├── s3_service.py               # Services S3 et SQS
│
├── ─────────── INTÉGRATIONS EXTERNES ───────────
├── local_watcher.py            # Watcher pour dossiers locaux
├── aws_metrics.py              # Métriques et coûts AWS Rekognition
│
├── ─────────── MIGRATIONS ───────────
├── add_photo_sqs_columns.py    # Migration colonnes S3+SQS
├── add_photo_indexed_column.py # Migration colonne is_indexed
├── add_show_in_general_column.py
├── add_password_reset_table.py
│
├── ─────────── INFRASTRUCTURE ───────────
├── Dockerfile                  # Image Docker de production
├── start.sh                    # Script de démarrage
├── requirements.txt            # Dépendances Python
│
├── ─────────── FRONTEND ───────────
├── static/                     # Fichiers statiques (HTML, JS, CSS)
├── templates/                  # Templates Jinja2
└── frontend/                   # Build React (optionnel)
```

---

## 3. Modèles de données (SQLAlchemy)

### 3.1 Diagramme des relations

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │───────│  UserEvent  │───────│    Event    │
│             │  N:M  │  (junction) │  N:1  │             │
└──────┬──────┘       └─────────────┘       └──────┬──────┘
       │                                           │
       │ 1:N                                       │ 1:N
       ▼                                           ▼
┌─────────────┐                            ┌─────────────┐
│  FaceMatch  │◄───────────────────────────│    Photo    │
│             │           N:1              │             │
└─────────────┘                            └─────────────┘
```

### 3.2 Modèles principaux

#### User
```python
class User(Base):
    id              # PK
    username        # Unique par événement
    email           # Unique par événement
    hashed_password
    user_type       # USER | PHOTOGRAPHER | ADMIN
    event_id        # FK vers Event (événement principal)
    selfie_path     # Chemin du selfie (legacy)
    selfie_data     # Données binaires du selfie
    is_active
    created_at
```

#### Event
```python
class Event(Base):
    id              # PK
    name            # Nom de l'événement
    event_code      # Code unique (ex: "MARIAGE2024")
    date            # Date de l'événement
    photographer_id # FK vers User (photographe propriétaire)
```

#### Photo
```python
class Photo(Base):
    id                  # PK
    filename            # Nom unique généré (UUID)
    original_filename   # Nom original du fichier
    photo_data          # Données binaires (compressées)
    content_type        # MIME type
    photo_type          # 'uploaded' | 'selfie'
    event_id            # FK vers Event
    photographer_id     # FK vers User
    
    # Colonnes S3+SQS (nouveau workflow)
    s3_key              # Clé S3 de l'image brute
    processing_status   # PENDING | PROCESSING | DONE | FAILED
    error_message       # Message d'erreur si FAILED
    
    # Colonnes d'optimisation
    original_size
    compressed_size
    compression_ratio
    quality_level
    is_indexed          # Indexé dans Rekognition ?
```

#### FaceMatch
```python
class FaceMatch(Base):
    id                # PK
    photo_id          # FK vers Photo
    user_id           # FK vers User
    confidence_score  # Score de similarité (0-100)
    detected_at       # Timestamp
```

#### UserEvent (table de jonction)
```python
class UserEvent(Base):
    id                  # PK
    user_id             # FK vers User
    event_id            # FK vers Event
    joined_at           # Date d'inscription
    rekognition_face_id # FaceId du selfie dans Rekognition
```

---

## 4. Flux de traitement des photos

### 4.1 Workflow S3 + SQS (Production)

Ce workflow est **robuste aux redémarrages** d'instances et de workers.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        UPLOAD D'UNE PHOTO                                │
└──────────────────────────────────────────────────────────────────────────┘

    Client (Photographe)
           │
           │ POST /api/photographer/events/{event_id}/upload-photos
           ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │ 1. ENDPOINT UPLOAD                                                  │
    │    ├── Créer entrée Photo en DB (status = PENDING)                  │
    │    ├── Upload image vers S3 (raw/event_{id}/{photo_id}.jpg)        │
    │    ├── Mettre à jour Photo.s3_key                                   │
    │    ├── Envoyer message SQS {photo_id, event_id, s3_key}            │
    │    └── Retourner 200 OK                                             │
    └─────────────────────────────────────────────────────────────────────┘
           │
           │ Message SQS
           ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │ 2. WORKER SQS (thread daemon)                                       │
    │    ├── receive_message (long polling 20s)                           │
    │    ├── Mettre Photo.status = PROCESSING                             │
    │    ├── Télécharger image depuis S3                                  │
    │    ├── Appeler AwsFaceRecognizer.process_photo_from_bytes()        │
    │    │      ├── Optimiser l'image (compression JPEG)                  │
    │    │      ├── Détecter les visages (DetectFaces)                    │
    │    │      ├── Indexer les visages (IndexFaces)                      │
    │    │      ├── Rechercher correspondances (SearchFaces)              │
    │    │      └── Créer/mettre à jour FaceMatch en DB                   │
    │    ├── Mettre Photo.status = DONE (ou FAILED)                       │
    │    └── delete_message SQS (si succès)                               │
    └─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Workflow Legacy (Fallback)

Utilisé si S3/SQS ne sont pas configurés. **Non recommandé en production.**

```
    Client
       │
       │ POST /api/photographer/events/{event_id}/upload-photos
       ▼
    ┌────────────────────────────────────────────────────────────────┐
    │ ENDPOINT UPLOAD                                                │
    │    ├── Écrire fichier temporaire ./temp_{uuid}.jpg            │
    │    ├── Créer PhotoJob et l'ajouter à la queue en mémoire      │
    │    └── Retourner 200 OK                                        │
    └────────────────────────────────────────────────────────────────┘
       │
       │ Queue en mémoire (volatile!)
       ▼
    ┌────────────────────────────────────────────────────────────────┐
    │ PHOTO WORKER (threads)                                         │
    │    ├── Récupérer job de la queue                               │
    │    ├── Lire fichier temporaire                                 │
    │    ├── Traiter avec AwsFaceRecognizer                          │
    │    └── Supprimer fichier temporaire                            │
    └────────────────────────────────────────────────────────────────┘

    ⚠️  PROBLÈMES :
    - Jobs perdus si le worker redémarre (max_requests Gunicorn)
    - Jobs perdus si l'instance App Runner redémarre
    - FileNotFoundError si le fichier temp est supprimé avant traitement
```

---

## 5. AWS Rekognition - Reconnaissance faciale

### 5.1 Architecture des collections

Une **collection Rekognition** est créée par événement :

```
Collection: event_{event_id}
│
├── Faces "user:{user_id}"     # Selfies des participants
│   └── Indexés lors de l'inscription
│
└── Faces "photo:{photo_id}"   # Visages détectés sur les photos
    └── Indexés lors de l'upload
```

### 5.2 Flux de matching

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INSCRIPTION D'UN UTILISATEUR                         │
└─────────────────────────────────────────────────────────────────────────┘

    1. Utilisateur soumet son selfie
    2. ensure_collection(event_id)      # Créer la collection si nécessaire
    3. IndexFaces(selfie)               # Indexer le selfie
       └── ExternalImageId = "user:{user_id}"
    4. Stocker le FaceId dans UserEvent.rekognition_face_id

┌─────────────────────────────────────────────────────────────────────────┐
│                       UPLOAD D'UNE PHOTO                                │
└─────────────────────────────────────────────────────────────────────────┘

    1. ensure_event_users_indexed(event_id)  # Indexer tous les selfies
    2. DetectFaces(photo)                     # Détecter les visages
    3. Pour chaque visage détecté :
       a. Crop du visage avec padding
       b. IndexFaces(crop)
          └── ExternalImageId = "photo:{photo_id}"
       c. SearchFaces(FaceId)
          └── Trouver les correspondances avec les selfies
    4. Créer FaceMatch pour chaque correspondance

┌─────────────────────────────────────────────────────────────────────────┐
│                    MISE À JOUR D'UN SELFIE                              │
└─────────────────────────────────────────────────────────────────────────┘

    1. index_user_selfie(event_id, user)      # Ré-indexer le selfie
    2. SearchFaces(new_FaceId)                # Trouver les photos
       └── Parmi les "photo:{photo_id}"
    3. Mettre à jour les FaceMatch
```

### 5.3 Seuils et paramètres

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `AWS_REKOGNITION_FACE_THRESHOLD` | 60% | Seuil minimum de similarité |
| `AWS_MATCH_MIN_SIMILARITY` | 70% | Seuil pour créer un FaceMatch |
| `AWS_REKOGNITION_SEARCH_MAXFACES` | 10 | Max faces par recherche |
| `AWS_REKOGNITION_SELFIE_SEARCH_MAXFACES` | 500 | Max pour recherche selfie |
| `AWS_REKOGNITION_DETECT_MIN_CONF` | 70% | Confiance min détection |

---

## 6. Configuration

### 6.1 Sources de configuration (ordre de priorité)

```
1. AWS SSM Parameter Store    # Priorité maximale (production)
       ↓
2. Variables d'environnement  # Via Dockerfile, App Runner, etc.
       ↓
3. Fichier .env               # Développement local
       ↓
4. Valeurs par défaut         # Définies dans settings.py
```

### 6.2 Variables d'environnement principales

#### Configuration SSM
```bash
APP_CONFIG_PREFIX=/findme/prod     # Préfixe des paramètres SSM
AWS_REGION=eu-west-3               # Région AWS (Paris) pour S3, SQS, SSM
REKOGNITION_REGION=eu-west-1       # Région pour Rekognition (Irlande)
```

#### Base de données
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
```

#### Stockage S3 et Queue SQS
```bash
PHOTO_BUCKET_NAME=findme-photos
PHOTO_SQS_QUEUE_URL=https://sqs.eu-west-1.amazonaws.com/xxx/photo-queue
PHOTO_WORKER_ENABLED=true
```

#### AWS Rekognition
```bash
FACE_RECOGNIZER_PROVIDER=aws       # aws | azure | local
REKOGNITION_REGION=eu-west-1       # Région Rekognition (Irlande, non disponible à Paris)
AWS_REKOGNITION_FACE_THRESHOLD=60
AWS_MATCH_MIN_SIMILARITY=70
```

#### Sécurité
```bash
SECRET_KEY=your-secret-key-change-in-production
BCRYPT_ROUNDS=12                   # 4 pour dev, 12 pour prod
```

---

## 7. API REST - Endpoints principaux

### 7.1 Authentification

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/register` | Inscription (avec selfie) |
| POST | `/api/token` | Connexion (JWT) |
| GET | `/api/users/me` | Profil utilisateur |
| POST | `/api/password-reset-request` | Demande de reset |
| POST | `/api/password-reset` | Reset du mot de passe |

### 7.2 Événements

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/photographer/events` | Créer un événement |
| GET | `/api/photographer/events` | Lister ses événements |
| GET | `/api/events/{code}` | Rejoindre par code |
| POST | `/api/events/{id}/join` | S'inscrire à un événement |

### 7.3 Photos

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/photographer/events/{id}/upload-photos` | Upload de photos |
| GET | `/api/events/{id}/photos` | Photos d'un événement |
| GET | `/api/my-photos` | Mes photos (FaceMatch) |
| GET | `/api/photos/{id}/image` | Télécharger une photo |

### 7.4 Administration

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/admin/queue/stats` | Stats des queues |
| GET | `/api/admin/config/ssm-status` | Statut SSM |
| GET | `/api/admin/aws-metrics` | Métriques AWS |

---

## 8. Sécurité

### 8.1 Authentification JWT

```python
# Création du token
token = create_access_token(
    data={"sub": username, "user_id": user_id},
    expires_delta=timedelta(minutes=30)
)

# Vérification du token
user = verify_token(token)  # Decode + requête DB
```

### 8.2 Hachage des mots de passe

```python
# Configuration bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=BCRYPT_ROUNDS  # 4 dev, 12 prod
)

# Hachage
hashed = get_password_hash(password)

# Vérification
is_valid = verify_password(plain_password, hashed_password)
```

### 8.3 Isolation par événement

- Un utilisateur ne peut accéder qu'aux photos de son événement
- Un photographe ne peut gérer que ses propres événements
- Les admins ont accès à tout

---

## 9. Optimisation des performances

### 9.1 Pool de connexions DB

```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Vérifie la connexion avant utilisation
    pool_size=10,            # Connexions permanentes
    max_overflow=20,         # Connexions additionnelles
    pool_recycle=1800,       # Recycle après 30 min
    pool_timeout=30,         # Timeout d'attente
)
```

### 9.2 Compression des images

```python
PhotoOptimizer.optimize_image(
    image_data=bytes,
    quality_profile='high',  # 85% JPEG, max 1920x1080
    retention_days=30
)
```

### 9.3 Thread pool pour le matching

```python
_MATCHING_THREAD_POOL = ThreadPoolExecutor(
    max_workers=10,
    thread_name_prefix="MatchingWorker"
)
```

### 9.4 Sémaphores pour dlib

```python
_FACE_RECOGNITION_SEMAPHORE = threading.Semaphore(1)
_DLIB_OPERATIONS_SEMAPHORE = threading.Semaphore(1)
```

---

## 10. Déploiement

### 10.1 Architecture AWS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud                                     │
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │  App Runner     │────▶│    RDS          │     │  SSM Parameter  │   │
│  │  (Container)    │     │  (PostgreSQL)   │     │     Store       │   │
│  └────────┬────────┘     └─────────────────┘     └─────────────────┘   │
│           │                                                              │
│           │                                                              │
│  ┌────────┴────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │       S3        │     │      SQS        │     │   Rekognition   │   │
│  │  (Photo bucket) │────▶│  (Job queue)    │────▶│  (Face matching)│   │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Commandes de démarrage

```bash
# Développement local
uvicorn main:app --reload --port 8000

# Production (via Gunicorn)
gunicorn main:app -c gunicorn_config.py

# Docker
docker build -t findme .
docker run -p 8000:8000 --env-file .env findme
```

### 10.3 Variables Gunicorn

```python
workers = 1                 # 1 worker pour App Runner
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 0            # Désactivé (S3+SQS robuste)
timeout = 120               # 2 min pour uploads longs
```

---

## 11. Monitoring et observabilité

### 11.1 Logs structurés

```
[SSM] Chargement des paramètres depuis /findme/prod
[DB] SQLAlchemy pool config -> size=10, max_overflow=20
[FaceRecognition][AWS] Using region: eu-west-1
[Startup] SQS Photo worker started
[PhotoWorkerSQS] Processing photo_id=123 event_id=1
[AWS-MATCH][photo->123] user_best={5: 92, 12: 87}
```

### 11.2 Métriques AWS

```python
aws_metrics.snapshot()
# Retourne :
{
    "counts": {"IndexFaces": 150, "SearchFaces": 500},
    "costs": {"IndexFaces": 0.15, "SearchFaces": 0.50},
    "total_cost_usd": 0.65
}
```

### 11.3 Endpoint de santé

```
GET /api/admin/queue/stats

{
    "workflow": "s3_sqs",
    "ssm": {"loaded": true, "prefix": "/findme/prod"},
    "sqs_worker": {"running": true, "total_processed": 150},
    "photos_by_status": {"pending": 0, "processing": 2, "failed": 1}
}
```

---

## 12. Évolutions futures

### Court terme
- [ ] Dead Letter Queue (DLQ) pour les messages SQS en échec
- [ ] CloudWatch Metrics pour le monitoring
- [ ] Retry automatique avec backoff exponentiel

### Moyen terme
- [ ] CDN CloudFront pour servir les photos
- [ ] Lambda pour le traitement (au lieu du worker intégré)
- [ ] ElastiCache Redis pour le cache de sessions

### Long terme
- [ ] Multi-région avec réplication S3
- [ ] API GraphQL en complément de REST
- [ ] Application mobile native

---

## Annexes

### A. Permissions IAM requises

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParametersByPath",
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/findme/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::findme-photos/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage"
      ],
      "Resource": "arn:aws:sqs:*:*:findme-photo-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:CreateCollection",
        "rekognition:IndexFaces",
        "rekognition:SearchFaces",
        "rekognition:SearchFacesByImage",
        "rekognition:DetectFaces",
        "rekognition:ListFaces",
        "rekognition:DeleteFaces"
      ],
      "Resource": "*"
    }
  ]
}
```

### B. Structure SSM Parameter Store

```
/findme/prod/
├── DATABASE_URL                    # String (SecureString)
├── SECRET_KEY                      # SecureString
├── PHOTO_BUCKET_NAME               # String
├── PHOTO_SQS_QUEUE_URL             # String
├── AWS_REKOGNITION_FACE_THRESHOLD  # String ("60")
├── BCRYPT_ROUNDS                   # String ("12")
└── ...
```

---

*Document généré le 4 février 2026*
*Version de l'application : avec workflow S3+SQS prod-ready*
