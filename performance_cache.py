"""
Module d'optimisation des performances avec cache Redis intégré
Implémente la mise en cache pour sessions, requêtes API et données fréquemment utilisées
"""

import functools
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import hashlib
import logging

from flask import current_app, request, session
try:
    from redis_cache_manager import RedisCacheManager as CacheManager
except ImportError:
    CacheManager = None

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Gestionnaire de cache haute performance pour l'application"""
    
    def __init__(self, app=None):
        self.cache_manager = None
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le cache avec l'application Flask"""
        self.app = app
        try:
            self.cache_manager = CacheManager()
            logger.info("Performance cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize performance cache: {e}")
            self.cache_manager = None
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Génère une clé de cache unique basée sur les paramètres"""
        key_data = {
            'args': args,
            'kwargs': kwargs,
            'timestamp': datetime.now().strftime('%Y-%m-%d-%H')  # Cache par heure
        }
        key_string = f"{prefix}:{json.dumps(key_data, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def cache_api_response(self, cache_key: str, ttl: int = 3600):
        """Décorateur pour mettre en cache les réponses API"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.cache_manager:
                    return func(*args, **kwargs)
                
                try:
                    # Génération de la clé complète
                    full_key = self._generate_cache_key(cache_key, *args, **kwargs)
                    
                    # Tentative de récupération du cache
                    cached_result = self.cache_manager.get(full_key)
                    if cached_result:
                        logger.debug(f"Cache hit for key: {full_key}")
                        return cached_result
                    
                    # Exécution de la fonction et mise en cache
                    result = func(*args, **kwargs)
                    self.cache_manager.set(full_key, result, ttl)
                    logger.debug(f"Cached result for key: {full_key}")
                    return result
                    
                except Exception as e:
                    logger.error(f"Cache error in {func.__name__}: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def cache_database_query(self, cache_key: str, ttl: int = 1800):
        """Décorateur spécialisé pour les requêtes de base de données"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.cache_manager:
                    return func(*args, **kwargs)
                
                try:
                    # Inclusion de l'utilisateur dans la clé pour l'isolation
                    user_id = getattr(session, 'user_id', 'anonymous')
                    full_key = self._generate_cache_key(f"db_{cache_key}_{user_id}", *args, **kwargs)
                    
                    cached_result = self.cache_manager.get(full_key)
                    if cached_result:
                        logger.debug(f"Database cache hit: {full_key}")
                        return cached_result
                    
                    result = func(*args, **kwargs)
                    # Sérialisation spéciale pour les objets SQLAlchemy
                    if hasattr(result, '__dict__'):
                        # Conversion en dictionnaire pour les objets modèles
                        serializable_result = self._serialize_model(result)
                    elif isinstance(result, list) and result and hasattr(result[0], '__dict__'):
                        # Liste d'objets modèles
                        serializable_result = [self._serialize_model(item) for item in result]
                    else:
                        serializable_result = result
                    
                    self.cache_manager.set(full_key, serializable_result, ttl)
                    logger.debug(f"Cached database result: {full_key}")
                    return result
                    
                except Exception as e:
                    logger.error(f"Database cache error in {func.__name__}: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _serialize_model(self, model) -> Dict:
        """Sérialise un modèle SQLAlchemy en dictionnaire"""
        if hasattr(model, '__table__'):
            return {c.name: getattr(model, c.name) for c in model.__table__.columns}
        return model.__dict__ if hasattr(model, '__dict__') else str(model)
    
    def cache_user_session(self, user_id: str, session_data: Dict, ttl: int = 7200):
        """Met en cache les données de session utilisateur"""
        if not self.cache_manager:
            return False
        
        try:
            session_key = f"session:{user_id}"
            return self.cache_manager.set(session_key, session_data, ttl)
        except Exception as e:
            logger.error(f"Failed to cache user session: {e}")
            return False
    
    def get_user_session(self, user_id: str) -> Optional[Dict]:
        """Récupère les données de session utilisateur depuis le cache"""
        if not self.cache_manager:
            return None
        
        try:
            session_key = f"session:{user_id}"
            return self.cache_manager.get(session_key)
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return None
    
    def invalidate_user_cache(self, user_id: str):
        """Invalide tout le cache associé à un utilisateur"""
        if not self.cache_manager:
            return
        
        try:
            patterns = [
                f"session:{user_id}",
                f"db_*_{user_id}:*",
                f"campaigns_{user_id}:*",
                f"products_{user_id}:*"
            ]
            
            for pattern in patterns:
                keys = self.cache_manager.get_keys_by_pattern(pattern)
                if keys:
                    self.cache_manager.delete_batch(keys)
                    logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
    
    def cache_ai_response(self, prompt_hash: str, response: Any, ttl: int = 86400):
        """Met en cache les réponses IA pour éviter les appels répétés"""
        if not self.cache_manager:
            return False
        
        try:
            ai_key = f"ai_response:{prompt_hash}"
            return self.cache_manager.set(ai_key, response, ttl)
        except Exception as e:
            logger.error(f"Failed to cache AI response: {e}")
            return False
    
    def get_cached_ai_response(self, prompt_hash: str) -> Optional[Any]:
        """Récupère une réponse IA mise en cache"""
        if not self.cache_manager:
            return None
        
        try:
            ai_key = f"ai_response:{prompt_hash}"
            return self.cache_manager.get(ai_key)
        except Exception as e:
            logger.error(f"Failed to get cached AI response: {e}")
            return None
    
    def get_cache_stats(self) -> Dict:
        """Retourne les statistiques du cache"""
        if not self.cache_manager:
            return {"status": "disabled", "message": "Cache manager not available"}
        
        try:
            return self.cache_manager.get_cache_stats()
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def clear_all_cache(self):
        """Vide complètement le cache (utilisation administrative)"""
        if not self.cache_manager:
            return False
        
        try:
            return self.cache_manager.clear_all_cache()
        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
            return False

# Instance globale
performance_cache = PerformanceCache()

# Décorateurs pratiques pour l'utilisation directe
def cache_for(duration: int = 3600, key_prefix: str = "default"):
    """Décorateur simple pour mettre en cache une fonction"""
    return performance_cache.cache_api_response(key_prefix, duration)

def cache_db_query(duration: int = 1800, key_prefix: str = "query"):
    """Décorateur simple pour mettre en cache une requête de base de données"""
    return performance_cache.cache_database_query(key_prefix, duration)

def cache_ai_call(duration: int = 86400, key_prefix: str = "ai"):
    """Décorateur simple pour mettre en cache un appel IA"""
    return performance_cache.cache_api_response(key_prefix, duration)