"""
Rate limiter simple basé sur des buckets en mémoire.
Permet de limiter le nombre de requêtes par utilisateur/IP sur une fenêtre de temps.
"""
import time
import threading
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import HTTPException, Request
from functools import wraps


class RateLimiter:
    """
    Rate limiter basé sur le token bucket algorithm.
    """
    
    def __init__(self):
        # Structure: {key: (tokens, last_update_time)}
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.RLock()
    
    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """
        Vérifie si une requête est autorisée.
        
        Args:
            key: Clé unique (user_id, IP, etc.)
            max_requests: Nombre max de requêtes autorisées
            window_seconds: Fenêtre de temps en secondes
        
        Returns:
            (allowed, remaining): allowed=True si autorisé, remaining=nombre de requêtes restantes
        """
        with self._lock:
            now = time.time()
            
            # Récupérer ou initialiser le bucket
            if key not in self._buckets:
                self._buckets[key] = (max_requests, now)
            
            tokens, last_update = self._buckets[key]
            
            # Calculer le nombre de tokens à ajouter depuis la dernière mise à jour
            time_passed = now - last_update
            tokens_to_add = (time_passed / window_seconds) * max_requests
            tokens = min(max_requests, tokens + tokens_to_add)
            
            # Vérifier si on peut consommer un token
            if tokens >= 1:
                tokens -= 1
                self._buckets[key] = (tokens, now)
                return True, int(tokens)
            else:
                self._buckets[key] = (tokens, now)
                return False, 0
    
    def reset(self, key: str):
        """Réinitialise le bucket pour une clé."""
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Nettoie les vieux buckets pour libérer la mémoire."""
        with self._lock:
            now = time.time()
            keys_to_delete = [
                k for k, (_, last_update) in self._buckets.items()
                if now - last_update > max_age_seconds
            ]
            for k in keys_to_delete:
                del self._buckets[k]


# Instance globale
_rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 100, window_seconds: int = 60, key_func=None):
    """
    Décorateur pour limiter le taux de requêtes.
    
    Args:
        max_requests: Nombre max de requêtes autorisées
        window_seconds: Fenêtre de temps en secondes
        key_func: Fonction pour extraire la clé (prend request et current_user)
                  Par défaut utilise user_id ou IP
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraire la requête et l'utilisateur des kwargs
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            # Générer la clé
            if key_func:
                key = key_func(request, current_user)
            elif current_user:
                key = f"user:{current_user.id}"
            elif request:
                # Fallback sur l'IP
                client_host = request.client.host if request.client else "unknown"
                key = f"ip:{client_host}"
            else:
                # Si on ne peut pas identifier, on laisse passer
                return await func(*args, **kwargs)
            
            # Vérifier la limite
            allowed, remaining = _rate_limiter.is_allowed(
                key, max_requests, window_seconds
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Trop de requêtes. Limite: {max_requests} requêtes par {window_seconds}s"
                )
            
            # Exécuter la fonction
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_rate_limiter() -> RateLimiter:
    """Récupère l'instance globale du rate limiter."""
    return _rate_limiter


# Nettoyage périodique des vieux buckets (optionnel, peut être appelé par un worker)
def cleanup_old_buckets():
    """Nettoie les vieux buckets pour libérer la mémoire."""
    _rate_limiter.cleanup_old_buckets()

