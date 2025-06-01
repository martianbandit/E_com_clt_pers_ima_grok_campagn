"""
Système de cache avancé pour NinjaLead.ai
Optimisation des performances avec mise en cache intelligente
"""

import redis
import json
import hashlib
import time
from functools import wraps
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Cache haute performance avec Redis et stratégies adaptatives"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=0, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test de connexion
            self.redis_client.ping()
            self.cache_available = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using memory cache: {e}")
            self.cache_available = False
            self.memory_cache = {}
            self.memory_cache_ttl = {}
    
    def _generate_cache_key(self, prefix, *args, **kwargs):
        """Génère une clé de cache unique basée sur les paramètres"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return f"ninja_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, key):
        """Récupère une valeur du cache"""
        if self.cache_available:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        else:
            # Cache mémoire avec TTL
            if key in self.memory_cache:
                if key in self.memory_cache_ttl:
                    if time.time() < self.memory_cache_ttl[key]:
                        return self.memory_cache[key]
                    else:
                        del self.memory_cache[key]
                        del self.memory_cache_ttl[key]
        return None
    
    def set(self, key, value, ttl=3600):
        """Stocke une valeur dans le cache avec TTL"""
        if self.cache_available:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        else:
            # Cache mémoire
            self.memory_cache[key] = value
            self.memory_cache_ttl[key] = time.time() + ttl
            # Nettoyage automatique (garder max 1000 entrées)
            if len(self.memory_cache) > 1000:
                self._cleanup_memory_cache()
        return False
    
    def delete(self, key):
        """Supprime une entrée du cache"""
        if self.cache_available:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        else:
            self.memory_cache.pop(key, None)
            self.memory_cache_ttl.pop(key, None)
    
    def _cleanup_memory_cache(self):
        """Nettoie le cache mémoire des entrées expirées"""
        current_time = time.time()
        expired_keys = [
            key for key, ttl in self.memory_cache_ttl.items() 
            if current_time > ttl
        ]
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.memory_cache_ttl.pop(key, None)

# Instance globale du cache
cache = PerformanceCache()

def cached_ai_response(ttl=1800):
    """Décorateur pour mettre en cache les réponses IA"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Génère une clé basée sur la fonction et les paramètres
            cache_key = cache._generate_cache_key(f"ai_{func.__name__}", *args, **kwargs)
            
            # Vérifie le cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Exécute la fonction et met en cache
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Met en cache seulement si l'exécution a réussi
            if result:
                cache.set(cache_key, result, ttl)
                logger.info(f"Cached result for {func.__name__} (exec: {execution_time:.2f}s)")
            
            return result
        return wrapper
    return decorator

def cached_db_query(ttl=600):
    """Décorateur pour mettre en cache les requêtes de base de données"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache._generate_cache_key(f"db_{func.__name__}", *args, **kwargs)
            
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"DB Cache hit for {func.__name__}")
                return cached_result
            
            result = func(*args, **kwargs)
            if result:
                cache.set(cache_key, result, ttl)
                logger.info(f"DB result cached for {func.__name__}")
            
            return result
        return wrapper
    return decorator

def invalidate_user_cache(user_id):
    """Invalide le cache spécifique à un utilisateur"""
    if cache.cache_available:
        try:
            # Recherche et supprime toutes les clés liées à l'utilisateur
            pattern = f"ninja_cache:*user_{user_id}*"
            keys = cache.redis_client.keys(pattern)
            if keys:
                cache.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

def get_cache_stats():
    """Retourne les statistiques du cache"""
    if cache.cache_available:
        try:
            info = cache.redis_client.info()
            return {
                "type": "redis",
                "memory_usage": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
            }
        except Exception:
            pass
    
    return {
        "type": "memory",
        "cached_items": len(cache.memory_cache),
        "memory_usage": f"{len(str(cache.memory_cache))} bytes"
    }