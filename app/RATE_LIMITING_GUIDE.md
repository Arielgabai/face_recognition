# Guide d'implémentation du Rate Limiting

## Module créé: `rate_limiter.py`

Un système de limitation de taux thread-safe basé sur le token bucket algorithm a été créé. Il est prêt à être utilisé mais n'est pas encore appliqué aux endpoints pour éviter de casser le code existant.

## Comment appliquer le rate limiting

### 1. Importer le décorateur

Ajoutez en haut de `main.py`:

```python
from rate_limiter import rate_limit
```

### 2. Appliquer aux endpoints critiques

#### Endpoint d'upload de photos

```python
@app.post("/api/photographer/events/{event_id}/upload-photos")
@rate_limit(max_requests=100, window_seconds=60)  # 100 uploads/minute
async def upload_photos_to_event(
    event_id: int,
    files: List[UploadFile] = File(...),
    watcher_id: int | None = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    ...
```

**Note importante:** Il faut aussi ajouter `request: Request` dans les paramètres pour que le rate limiter puisse extraire l'IP si nécessaire:

```python
async def upload_photos_to_event(
    request: Request,  # AJOUTER
    event_id: int,
    files: List[UploadFile] = File(...),
    ...
):
```

#### Endpoint de galerie utilisateur

```python
@app.get("/api/my-photos", response_model=List[PhotoSchema])
@rate_limit(max_requests=60, window_seconds=60)  # 60 requêtes/minute
async def get_my_photos(
    request: Request,  # AJOUTER
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ...
```

#### Endpoint de toutes les photos

```python
@app.get("/api/all-photos", response_model=List[PhotoSchema])
@rate_limit(max_requests=60, window_seconds=60)  # 60 requêtes/minute
async def get_all_photos(
    request: Request,  # AJOUTER
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ...
```

#### Endpoint de login

```python
@app.post("/api/login")
@rate_limit(max_requests=10, window_seconds=60)  # 10 tentatives/minute
async def login(
    request: Request,  # AJOUTER
    user_credentials: UserLogin,
    db: Session = Depends(get_current_user)
):
    ...
```

## Limites recommandées par endpoint

| Endpoint | Limite recommandée | Raison |
|----------|-------------------|--------|
| `/api/login` | 10/minute | Prévenir brute force |
| `/api/photographer/events/{id}/upload-photos` | 100/minute | Permettre uploads massifs mais limiter les abus |
| `/api/my-photos` | 60/minute | Usage normal d'un utilisateur |
| `/api/all-photos` | 60/minute | Usage normal d'un utilisateur |
| `/api/search-photos` | 30/minute | Requête coûteuse |
| `/api/admin/*` | 120/minute | Admin peut faire plus de requêtes |

## Rate limiter personnalisé

Pour créer une clé de rate limiting personnalisée:

```python
def custom_key(request, current_user):
    # Exemple: limiter par event_id pour les photographes
    event_id = request.path_params.get('event_id')
    return f"photographer:{current_user.id}:event:{event_id}"

@app.post("/api/photographer/events/{event_id}/upload-photos")
@rate_limit(max_requests=100, window_seconds=60, key_func=custom_key)
async def upload_photos_to_event(...):
    ...
```

## Réponse en cas de dépassement

Quand la limite est atteinte, l'endpoint retourne:

```json
{
    "detail": "Trop de requêtes. Limite: 100 requêtes par 60s"
}
```

Avec le statut HTTP `429 Too Many Requests`.

## Monitoring

### Nettoyer les vieux buckets

Pour libérer la mémoire, ajoutez un job périodique:

```python
from rate_limiter import cleanup_old_buckets

# Dans un worker ou scheduler
cleanup_old_buckets()  # Nettoie les buckets de plus d'1 heure
```

### Endpoint de monitoring (à créer)

```python
@app.get("/api/admin/rate-limiter/stats")
async def get_rate_limiter_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé")
    
    from rate_limiter import get_rate_limiter
    limiter = get_rate_limiter()
    
    return {
        "active_buckets": len(limiter._buckets),
        "buckets": {
            k: {"tokens": tokens, "last_update": last_update}
            for k, (tokens, last_update) in list(limiter._buckets.items())[:10]
        }
    }
```

## Désactiver le rate limiting (développement)

Pour désactiver temporairement pendant le développement, créez un wrapper:

```python
import os

def rate_limit_if_prod(*args, **kwargs):
    if os.environ.get("DISABLE_RATE_LIMITING") == "1":
        # Ne pas appliquer le rate limiting
        def decorator(func):
            return func
        return decorator
    else:
        # Appliquer le rate limiting
        from rate_limiter import rate_limit
        return rate_limit(*args, **kwargs)

# Utilisation
@app.post("/api/photographer/events/{event_id}/upload-photos")
@rate_limit_if_prod(max_requests=100, window_seconds=60)
async def upload_photos_to_event(...):
    ...
```

Puis dans .env:

```bash
# En développement
DISABLE_RATE_LIMITING=1

# En production
# DISABLE_RATE_LIMITING=0  (ou ne pas définir)
```

## Tests

Pour tester le rate limiting:

```python
import pytest
from rate_limiter import RateLimiter

def test_rate_limiter():
    limiter = RateLimiter()
    
    # Première requête: OK
    allowed, remaining = limiter.is_allowed("test_key", max_requests=5, window_seconds=60)
    assert allowed == True
    assert remaining == 4
    
    # 5 requêtes: OK
    for i in range(4):
        allowed, remaining = limiter.is_allowed("test_key", max_requests=5, window_seconds=60)
        assert allowed == True
    
    # 6ème requête: BLOCKED
    allowed, remaining = limiter.is_allowed("test_key", max_requests=5, window_seconds=60)
    assert allowed == False
    assert remaining == 0
```

## Conclusion

Le module de rate limiting est prêt à être utilisé. Il suffit de:
1. Ajouter `request: Request` aux paramètres des endpoints
2. Ajouter le décorateur `@rate_limit(...)` au-dessus des endpoints
3. Ajuster les limites selon vos besoins

Le rate limiting est **optionnel** mais fortement recommandé pour la production.

