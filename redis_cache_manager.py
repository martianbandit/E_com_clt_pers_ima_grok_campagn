"""
Gestionnaire de cache Redis pour NinjaLead.ai
Implémente la mise en cache des sessions et données pour améliorer les performances
"""

import os
import json
import redis
import logging
from typing import Any, Optional, Dict, List, Union
from functools import wraps
import pickle
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Gestionnaire centralisé pour le cache Redis"""
    
    def __init__(self, redis_url: str = None):
        """
        Initialise le gestionnaire de cache Redis
        
        Args:
            redis_url: URL de connexion Redis
        """
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client = None
        self.is_connected = False
        self._connect()
        
    def _connect(self) -> None:
        """Établit la connexion Redis avec gestion d'erreur"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test de connexion
            self.redis_client.ping()
            self.is_connected = True
            logger.info("Connexion Redis établie avec succès")
            
        except redis.ConnectionError as e:
            logger.warning(f"Redis non disponible: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Erreur lors de la connexion Redis: {e}")
            self.is_connected = False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé de cache
            default: Valeur par défaut si non trouvée
            
        Returns:
            Valeur du cache ou valeur par défaut
        """
        if not self.is_connected:
            return default
            
        try:
            value = self.redis_client.get(key)
            if value is None:
                return default
                
            # Tente de désérialiser JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du cache {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Stocke une valeur dans le cache
        
        Args:
            key: Clé de cache
            value: Valeur à stocker
            ttl: Durée de vie en secondes (défaut: 1 heure)
            
        Returns:
            True si le stockage a réussi
        """
        if not self.is_connected:
            return False
            
        try:
            # Sérialise la valeur
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)
                
            return self.redis_client.setex(key, ttl, serialized_value)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du cache {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Supprime une clé du cache
        
        Args:
            key: Clé à supprimer
            
        Returns:
            True si la suppression a réussi
        """
        if not self.is_connected:
            return False
            
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Vérifie si une clé existe dans le cache
        
        Args:
            key: Clé à vérifier
            
        Returns:
            True si la clé existe
        """
        if not self.is_connected:
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du cache {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1, ttl: int = 3600) -> Optional[int]:
        """
        Incrémente une valeur numérique
        
        Args:
            key: Clé à incrémenter
            amount: Montant d'incrémentation
            ttl: Durée de vie si nouvelle clé
            
        Returns:
            Nouvelle valeur ou None en cas d'erreur
        """
        if not self.is_connected:
            return None
            
        try:
            new_value = self.redis_client.incr(key, amount)
            if new_value == amount:  # Nouvelle clé créée
                self.redis_client.expire(key, ttl)
            return new_value
        except Exception as e:
            logger.error(f"Erreur lors de l'incrémentation {key}: {e}")
            return None
    
    def get_keys_pattern(self, pattern: str) -> List[str]:
        """
        Récupère les clés correspondant à un pattern
        
        Args:
            pattern: Pattern de recherche (ex: "user:*")
            
        Returns:
            Liste des clés correspondantes
        """
        if not self.is_connected:
            return []
            
        try:
            return list(self.redis_client.keys(pattern))
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de clés {pattern}: {e}")
            return []
    
    def flush_pattern(self, pattern: str) -> int:
        """
        Supprime toutes les clés correspondant à un pattern
        
        Args:
            pattern: Pattern de suppression
            
        Returns:
            Nombre de clés supprimées
        """
        if not self.is_connected:
            return 0
            
        try:
            keys = self.get_keys_pattern(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache Redis
        
        Returns:
            Dictionnaire avec les statistiques
        """
        if not self.is_connected:
            return {
                'status': 'disconnected',
                'error': 'Redis non disponible'
            }
            
        try:
            info = self.redis_client.info()
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'uptime_in_seconds': info.get('uptime_in_seconds')
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calcule le taux de hit du cache"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        return round((hits / total * 100), 2) if total > 0 else 0.0

# Instance globale du gestionnaire de cache
cache_manager = RedisCacheManager()

# Décorateur pour la mise en cache automatique
def cache_result(ttl: int = 3600, key_prefix: str = "cache"):
    """
    Décorateur pour mettre en cache le résultat d'une fonction
    
    Args:
        ttl: Durée de vie du cache en secondes
        key_prefix: Préfixe pour la clé de cache
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Génère une clé de cache unique basée sur la fonction et ses arguments
            func_name = f"{func.__module__}.{func.__name__}"
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}:{func_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Tente de récupérer depuis le cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Exécute la fonction et met en cache le résultat
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
            
        return wrapper
    return decorator

# Fonctions utilitaires pour la gestion des sessions
class SessionManager:
    """Gestionnaire de sessions avec cache Redis"""
    
    @staticmethod
    def store_session(session_id: str, user_data: Dict, ttl: int = 86400) -> bool:
        """
        Stocke les données de session utilisateur
        
        Args:
            session_id: ID de session
            user_data: Données utilisateur
            ttl: Durée de vie (défaut: 24h)
        """
        key = f"session:{session_id}"
        return cache_manager.set(key, user_data, ttl)
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict]:
        """
        Récupère les données de session
        
        Args:
            session_id: ID de session
            
        Returns:
            Données utilisateur ou None
        """
        key = f"session:{session_id}"
        return cache_manager.get(key)
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Supprime une session
        
        Args:
            session_id: ID de session
        """
        key = f"session:{session_id}"
        return cache_manager.delete(key)
    
    @staticmethod
    def refresh_session(session_id: str, ttl: int = 86400) -> bool:
        """
        Prolonge la durée de vie d'une session
        
        Args:
            session_id: ID de session
            ttl: Nouvelle durée de vie
        """
        key = f"session:{session_id}"
        if cache_manager.exists(key):
            data = cache_manager.get(key)
            return cache_manager.set(key, data, ttl)
        return False

# Fonctions utilitaires pour les données métier
class BusinessDataCache:
    """Cache pour les données métier critiques"""
    
    @staticmethod
    def cache_user_campaigns(user_id: str, campaigns: List[Dict], ttl: int = 1800) -> bool:
        """Cache les campagnes d'un utilisateur"""
        key = f"user_campaigns:{user_id}"
        return cache_manager.set(key, campaigns, ttl)
    
    @staticmethod
    def get_user_campaigns(user_id: str) -> Optional[List[Dict]]:
        """Récupère les campagnes en cache"""
        key = f"user_campaigns:{user_id}"
        return cache_manager.get(key)
    
    @staticmethod
    def cache_user_products(user_id: str, products: List[Dict], ttl: int = 1800) -> bool:
        """Cache les produits d'un utilisateur"""
        key = f"user_products:{user_id}"
        return cache_manager.set(key, products, ttl)
    
    @staticmethod
    def get_user_products(user_id: str) -> Optional[List[Dict]]:
        """Récupère les produits en cache"""
        key = f"user_products:{user_id}"
        return cache_manager.get(key)
    
    @staticmethod
    def cache_ai_generation(prompt_hash: str, result: Dict, ttl: int = 7200) -> bool:
        """Cache les résultats de génération IA"""
        key = f"ai_generation:{prompt_hash}"
        return cache_manager.set(key, result, ttl)
    
    @staticmethod
    def get_ai_generation(prompt_hash: str) -> Optional[Dict]:
        """Récupère un résultat de génération IA en cache"""
        key = f"ai_generation:{prompt_hash}"
        return cache_manager.get(key)
    
    @staticmethod
    def invalidate_user_cache(user_id: str) -> int:
        """Invalide tout le cache d'un utilisateur"""
        return cache_manager.flush_pattern(f"user_*:{user_id}")

# Fonctions de maintenance du cache
def cleanup_expired_cache() -> Dict[str, int]:
    """Nettoie le cache expiré et retourne les statistiques"""
    stats = {
        'sessions_cleaned': 0,
        'ai_cache_cleaned': 0,
        'user_cache_cleaned': 0
    }
    
    # Nettoyage automatique géré par Redis TTL
    # Cette fonction peut être étendue pour des nettoyages personnalisés
    
    return stats

def warm_up_cache() -> bool:
    """Préchauffe le cache avec des données fréquemment utilisées"""
    try:
        # Logique de préchauffage à implémenter selon les besoins
        logger.info("Cache préchauffé avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du préchauffage du cache: {e}")
        return False

if __name__ == "__main__":
    # Test du système de cache
    print("Test du gestionnaire de cache Redis...")
    
    stats = cache_manager.get_stats()
    print(f"Statut Redis: {stats.get('status')}")
    
    if stats.get('status') == 'connected':
        print(f"Version Redis: {stats.get('redis_version')}")
        print(f"Mémoire utilisée: {stats.get('used_memory')}")
        print(f"Taux de hit: {stats.get('hit_rate')}%")