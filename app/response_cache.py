"""
Cache en mémoire pour les réponses des endpoints utilisateur.
Réduit la charge sur la DB et AWS pendant les uploads massifs.
"""
import time
import threading
from typing import Any, Optional, Dict, Callable
from functools import wraps
from collections import OrderedDict


class LRUCache:
    """
    Cache LRU (Least Recently Used) thread-safe avec expiration par TTL.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 60.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Vérifier l'expiration
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Déplacer à la fin (plus récemment utilisé)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Ajoute ou met à jour une valeur dans le cache."""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # Supprimer l'ancienne entrée si elle existe
            if key in self._cache:
                del self._cache[key]
            
            # Ajouter la nouvelle entrée
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }
            
            # Déplacer à la fin
            self._cache.move_to_end(key)
            
            # Éviction LRU si nécessaire
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    def invalidate(self, key: str):
        """Invalide une entrée du cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def invalidate_pattern(self, pattern: str):
        """Invalide toutes les entrées dont la clé contient le pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
    
    def clear(self):
        """Vide le cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du cache."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
            }


# Caches globaux pour différents types de données
user_photos_cache = LRUCache(max_size=500, default_ttl=30.0)  # Cache court pour les photos
event_cache = LRUCache(max_size=200, default_ttl=120.0)  # Cache plus long pour les événements
user_cache = LRUCache(max_size=1000, default_ttl=60.0)  # Cache pour les infos utilisateur


def cache_response(
    cache: LRUCache,
    key_prefix: str = "",
    ttl: Optional[float] = None,
    skip_if: Optional[Callable] = None,
):
    """
    Décorateur pour mettre en cache les réponses d'un endpoint.
    
    Args:
        cache: Instance de LRUCache à utiliser
        key_prefix: Préfixe pour la clé du cache
        ttl: Durée de vie du cache (None = utiliser default_ttl)
        skip_if: Fonction qui prend les kwargs et retourne True si le cache doit être ignoré
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Générer la clé du cache basée sur les arguments
            # Filtrer les arguments non-sérialisables (comme db, current_user objects)
            cache_key_parts = [key_prefix, func.__name__]
            
            for k, v in kwargs.items():
                # Ignorer certains arguments
                if k in ("db", "current_user", "background_tasks"):
                    continue
                # Extraire l'ID si c'est un objet User
                if hasattr(v, "id"):
                    cache_key_parts.append(f"{k}={v.id}")
                elif isinstance(v, (str, int, float, bool)):
                    cache_key_parts.append(f"{k}={v}")
            
            cache_key = ":".join(str(p) for p in cache_key_parts)
            
            # Vérifier si on doit ignorer le cache
            if skip_if and skip_if(**kwargs):
                return await func(*args, **kwargs)
            
            # Chercher dans le cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Exécuter la fonction
            result = await func(*args, **kwargs)
            
            # Mettre en cache
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_user_photos_cache(user_id: int, event_id: Optional[int] = None):
    """Invalide le cache des photos d'un utilisateur."""
    user_photos_cache.invalidate_pattern(f"user_id={user_id}")
    if event_id:
        user_photos_cache.invalidate_pattern(f"event_id={event_id}")


def invalidate_event_cache(event_id: int):
    """Invalide le cache d'un événement."""
    event_cache.invalidate_pattern(f"event_id={event_id}")
    user_photos_cache.invalidate_pattern(f"event_id={event_id}")


def get_cache_stats() -> Dict[str, Any]:
    """Récupère les statistiques de tous les caches."""
    return {
        "user_photos_cache": user_photos_cache.get_stats(),
        "event_cache": event_cache.get_stats(),
        "user_cache": user_cache.get_stats(),
    }

