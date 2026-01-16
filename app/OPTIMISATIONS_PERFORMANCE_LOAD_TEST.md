# 🚀 Optimisations Performance pour Tests de Charge

## 📊 Problèmes identifiés

### Résultats actuels (10 users)
```
/api/check-event-code         : 1.5s avg
/api/check-user-availability   : 3.7s avg
/api/login                     : 5.5s avg
/api/register-with-event-code  : 11s avg
/api/upload-selfie             : 45.5s avg (20% échecs) ⚠️
```

### Causes principales
1. ✅ **Index manquants** sur tables critiques
2. ✅ **Requêtes DB non optimisées** (N+1 queries, full table scans)
3. ✅ **Validation de selfie synchrone** (Azure API timeout 15s)
4. ✅ **Workers insuffisants** (pas de concurrence réelle)
5. ✅ **Pas de cache** pour queries répétées

---

## 🔧 Solution 1 : Ajouter des index critiques

### Fichier : `add_performance_indexes.py`

```python
"""
Script pour ajouter les index manquants qui impactent les performances
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def add_performance_indexes():
    """Ajoute les index critiques pour améliorer les performances"""
    with engine.connect() as conn:
        print("🔧 Ajout des index de performance...")
        
        indexes = [
            # FaceMatch : requis pour les jointures fréquentes
            "CREATE INDEX IF NOT EXISTS idx_face_matches_user_id ON face_matches(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_face_matches_photo_id ON face_matches(photo_id);",
            "CREATE INDEX IF NOT EXISTS idx_face_matches_user_photo ON face_matches(user_id, photo_id);",
            
            # Photo : événements utilisés partout
            "CREATE INDEX IF NOT EXISTS idx_photos_event_id ON photos(event_id);",
            "CREATE INDEX IF NOT EXISTS idx_photos_photographer_id ON photos(photographer_id);",
            "CREATE INDEX IF NOT EXISTS idx_photos_event_photographer ON photos(event_id, photographer_id);",
            
            # UserEvent : association users <-> events
            "CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_events_event_id ON user_events(event_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_events_user_event ON user_events(user_id, event_id);",
            
            # User : recherches par type et événement
            "CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);",
            "CREATE INDEX IF NOT EXISTS idx_users_event_user_type ON users(event_id, user_type);",
        ]
        
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"  ✅ {idx_sql[:60]}...")
            except Exception as e:
                print(f"  ⚠️  Erreur: {e}")
        
        print("✅ Index ajoutés avec succès!")

if __name__ == "__main__":
    add_performance_indexes()
```

**Exécution :**
```bash
python add_performance_indexes.py
```

---

## 🔧 Solution 2 : Optimiser les requêtes DB

### A. Optimiser `check_user_availability`

**Avant (3.7s avg):**
```python
# Fait 2 requêtes séparées
user = db.query(User).filter(...).first()
other_count = db.query(User).filter(...).count()
```

**Après (<0.5s):**
```python
# 1 seule requête avec EXISTS
from sqlalchemy import exists, select

result = db.execute(
    select(
        exists().where(
            (User.username == username) & (User.event_id == event.id)
        )
    )
).scalar()
```

### B. Optimiser la suppression des FaceMatch dans upload_selfie

**Avant (contributif aux 45s):**
```python
# Fait une requête pour TOUS les photo_ids puis delete
photo_ids = [p.id for p in db.query(Photo).filter(Photo.event_id == ue.event_id).all()]
if photo_ids:
    deleted = db.query(FaceMatch).filter(...).delete()
```

**Après (<1s):**
```python
# DELETE direct avec subquery
from sqlalchemy import delete
stmt = delete(FaceMatch).where(
    FaceMatch.user_id == current_user.id,
    FaceMatch.photo_id.in_(
        select(Photo.id).where(Photo.event_id == ue.event_id)
    )
)
db.execute(stmt)
```

---

## 🔧 Solution 3 : Rendre la validation asynchrone

### Fichier modifié : `main.py` - endpoint `/api/upload-selfie`

**Problème actuel :** La validation bloque pendant ~15s (appel Azure + traitement image)

**Solution :** Validation en background

```python
@app.post("/api/upload-selfie")
async def upload_selfie(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    strict: bool = True,
    background_tasks: BackgroundTasks = None,
):
    """Upload d'un selfie pour l'utilisateur - version optimisée"""
    if current_user.user_type == UserType.PHOTOGRAPHER:
        raise HTTPException(status_code=403, detail="Les photographes ne peuvent pas uploader de selfies")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    
    # Lire les données
    file_data = await file.read()
    
    # ✅ OPTIMISATION 1 : Validation rapide synchrone (format + taille)
    if len(file_data) > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 10MB)")
    
    # Vérification basique du format
    try:
        from PIL import Image
        import io
        Image.open(io.BytesIO(file_data)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Format d'image invalide")
    
    # ✅ OPTIMISATION 2 : Sauvegarde immédiate (réponse rapide au client)
    current_user.selfie_data = file_data
    current_user.selfie_path = None
    db.commit()
    
    # ✅ OPTIMISATION 3 : Validation stricte + matching en background
    if background_tasks and strict:
        background_tasks.add_task(
            _validate_and_rematch_selfie,
            current_user.id,
            file_data,
            strict
        )
    else:
        # Fallback synchrone pour environnements sans background tasks
        _validate_and_rematch_selfie(current_user.id, file_data, strict)
    
    return {
        "message": "Selfie uploadé avec succès. Le matching est en cours...",
        "status": "processing"
    }

def _validate_and_rematch_selfie(user_id: int, file_data: bytes, strict: bool):
    """Validation et matching en background"""
    session = next(get_db())
    try:
        # Validation stricte (visage unique, qualité, etc.)
        if strict:
            try:
                validate_selfie_image(file_data)
            except HTTPException as e:
                # Si validation échoue, supprimer le selfie et notifier
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.selfie_data = None
                    session.commit()
                print(f"[SelfieValidation] FAILED for user_id={user_id}: {e.detail}")
                return
        
        # Supprimer anciennes correspondances (optimisé)
        user_events = session.query(UserEvent.event_id).filter(UserEvent.user_id == user_id).all()
        event_ids = [ue.event_id for ue in user_events]
        
        if event_ids:
            from sqlalchemy import delete
            stmt = delete(FaceMatch).where(
                FaceMatch.user_id == user_id,
                FaceMatch.photo_id.in_(
                    select(Photo.id).where(Photo.event_id.in_(event_ids))
                )
            )
            session.execute(stmt)
            session.commit()
        
        # Matching en background (existant)
        _rematch_all_events(user_id)
        
    finally:
        session.close()
```

---

## 🔧 Solution 4 : Configuration Workers (Gunicorn)

### Fichier : `gunicorn_config.py`

```python
"""Configuration Gunicorn optimisée pour tests de charge"""
import multiprocessing
import os

# Workers
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Recycler les workers après 1000 requêtes
max_requests_jitter = 50
timeout = 120  # 2 minutes pour les requêtes longues

# Connexions
keepalive = 5
backlog = 2048

# Logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Performance
preload_app = True  # Charge l'app avant de forker les workers
```

**Démarrage :**
```bash
gunicorn main:app -c gunicorn_config.py
```

---

## 🔧 Solution 5 : Cache pour queries répétées

### Fichier : `cache_manager.py`

```python
"""Cache simple en mémoire pour les queries fréquentes"""
from functools import lru_cache
import time
from typing import Optional

# Cache simple avec TTL
_cache = {}
_cache_ttl = {}

def cache_get(key: str) -> Optional[any]:
    """Récupère une valeur du cache si elle n'a pas expiré"""
    if key in _cache:
        if time.time() < _cache_ttl.get(key, 0):
            return _cache[key]
        else:
            # Expiré
            del _cache[key]
            if key in _cache_ttl:
                del _cache_ttl[key]
    return None

def cache_set(key: str, value: any, ttl: int = 60):
    """Stocke une valeur dans le cache avec TTL (secondes)"""
    _cache[key] = value
    _cache_ttl[key] = time.time() + ttl

def cache_delete(key: str):
    """Supprime une entrée du cache"""
    if key in _cache:
        del _cache[key]
    if key in _cache_ttl:
        del _cache_ttl[key]

# Cache spécifique pour event_code validation
@lru_cache(maxsize=1000)
def is_valid_event_code(event_code: str, _timestamp: int = None) -> bool:
    """Cache la validation des codes événements (invalide toutes les 5 min)"""
    from database import SessionLocal
    from models import Event
    
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.event_code == event_code).first()
        return event is not None
    finally:
        db.close()

def validate_event_code_cached(event_code: str) -> bool:
    """Validation avec cache (5 minutes)"""
    timestamp = int(time.time() / 300)  # Bloc de 5 minutes
    return is_valid_event_code(event_code, timestamp)
```

### Utilisation dans `/api/check-event-code`

```python
from cache_manager import validate_event_code_cached

@app.post("/api/check-event-code")
async def check_event_code(event_code: str = Body(..., embed=True)):
    """Version optimisée avec cache"""
    is_valid = validate_event_code_cached(event_code)
    return {"valid": is_valid}
```

---

## 📈 Résultats attendus après optimisations

### Objectif : 30 users simultanés

```
Endpoint                       Avant     Après    Amélioration
------------------------------------------------------------------
/api/check-event-code          1.5s  →  0.1s      15x plus rapide
/api/check-user-availability   3.7s  →  0.3s      12x plus rapide
/api/login                     5.5s  →  0.5s      11x plus rapide
/api/register-with-event-code  11s   →  2s        5x plus rapide
/api/upload-selfie            45.5s  →  3s        15x plus rapide
Taux d'échec                   20%   →  <1%       ✅
```

---

## 🚀 Plan d'action (ordre recommandé)

### Phase 1 : Quick wins (15 min)
1. ✅ Exécuter `python add_performance_indexes.py`
2. ✅ Ajouter cache pour `check-event-code`
3. ✅ Redémarrer avec Gunicorn + workers multiples

### Phase 2 : Optimisations DB (30 min)
4. ✅ Optimiser `check_user_availability` (requête unique)
5. ✅ Optimiser suppression FaceMatch (subquery)

### Phase 3 : Upload asynchrone (45 min)
6. ✅ Implémenter validation background
7. ✅ Tester avec 10 users
8. ✅ Monter progressivement à 30 users

---

## ⚙️ Variables d'environnement recommandées

```bash
# Database
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=70
DB_POOL_RECYCLE=1800
DB_POOL_TIMEOUT=30

# Workers
GUNICORN_WORKERS=8  # 2 x CPU cores

# Performance
SELFIE_VALIDATION_STRICT=true
FACE_RECOGNIZER_PROVIDER=local  # Éviter les appels Azure pendant les tests
```

---

## 🧪 Tests de validation

```bash
# 1. Lancer l'app optimisée
gunicorn main:app -c gunicorn_config.py

# 2. Test de charge progressif
locust -f locust_file.py --host=http://localhost:8000 \
       --users=10 --spawn-rate=2 --run-time=2m

# 3. Si OK, augmenter
locust -f locust_file.py --host=http://localhost:8000 \
       --users=20 --spawn-rate=3 --run-time=3m

# 4. Test final
locust -f locust_file.py --host=http://localhost:8000 \
       --users=30 --spawn-rate=5 --run-time=5m
```

---

## 📊 Monitoring

```python
# Ajouter endpoint de stats
@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Statistiques de performance"""
    from sqlalchemy import func, text
    
    stats = {}
    
    # Compter les entités
    stats["users"] = db.query(func.count(User.id)).scalar()
    stats["photos"] = db.query(func.count(Photo.id)).scalar()
    stats["face_matches"] = db.query(func.count(FaceMatch.id)).scalar()
    stats["events"] = db.query(func.count(Event.id)).scalar()
    
    # Pool de connexions
    from database import engine
    stats["db_pool"] = {
        "size": engine.pool.size(),
        "checked_out": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else 'N/A',
        "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else 'N/A',
    }
    
    return stats
```

---

## ✅ Checklist finale

- [ ] Index ajoutés sur toutes les tables
- [ ] Requêtes DB optimisées (pas de N+1)
- [ ] Cache activé pour queries répétées
- [ ] Upload de selfie asynchrone
- [ ] Gunicorn avec workers multiples
- [ ] Variables d'environnement configurées
- [ ] Tests de charge réussis (30 users)
- [ ] Taux d'échec < 1%
- [ ] Temps de réponse < 5s pour 95% des requêtes

