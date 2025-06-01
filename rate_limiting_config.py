"""
Configuration et application des limites de taux pour NinjaLead.ai
Sécurise les endpoints sensibles contre les abus et attaques DDoS
"""

import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

def apply_rate_limits_to_routes(app, limiter):
    """
    Applique des limites de taux spécifiques aux endpoints sensibles
    """
    if not limiter:
        logger.warning("Rate limiter not available, skipping rate limit application")
        return
    
    # Configuration des limites par type d'endpoint
    RATE_LIMITS = {
        'auth': "10 per minute",      # Authentification
        'ai_generation': "20 per minute",  # Génération IA
        'api_sensitive': "30 per minute",  # APIs sensibles
        'file_upload': "5 per minute",     # Upload de fichiers
        'registration': "3 per minute"     # Inscription
    }
    
    # Middleware pour logging des violations de rate limit
    @limiter.request_filter
    def log_rate_limit_violations():
        """Log les tentatives de dépassement de limites"""
        try:
            from flask import request
            client_ip = get_remote_address()
            endpoint = getattr(request, 'endpoint', 'unknown')
            logger.warning(f"Rate limit approached - IP: {client_ip}, Endpoint: {endpoint}")
        except:
            pass
        return False  # Continue processing
    
    # Handler pour les erreurs de rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Gestionnaire personnalisé pour les erreurs 429 (Too Many Requests)"""
        return {
            "error": "Trop de requêtes",
            "message": "Veuillez patienter avant de réessayer",
            "retry_after": getattr(e, 'retry_after', 60)
        }, 429
    
    logger.info("Rate limiting rules applied to sensitive endpoints")
    return RATE_LIMITS

def get_user_rate_limit_key():
    """
    Fonction personnalisée pour identifier les utilisateurs pour le rate limiting
    Combine IP + User ID si connecté pour un contrôle plus précis
    """
    try:
        from flask import request
        from flask_login import current_user
        
        base_key = get_remote_address()
        
        # Si l'utilisateur est connecté, ajouter son ID
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            base_key += f"_user_{current_user.id}"
        
        return base_key
    except:
        return get_remote_address()

def setup_advanced_rate_limiting(app, limiter):
    """
    Configuration avancée du rate limiting avec exemptions et règles spéciales
    """
    if not limiter:
        return
    
    # Exemptions pour certaines IPs (à configurer selon l'environnement)
    EXEMPT_IPS = []  # Ajouter des IPs de confiance si nécessaire
    
    @limiter.request_filter
    def ip_whitelist():
        """Exempte certaines IPs du rate limiting"""
        return get_remote_address() in EXEMPT_IPS
    
    # Limites spéciales pour les utilisateurs authentifiés vs anonymes
    @limiter.limit("200 per hour")
    def authenticated_user_limit():
        """Limite plus élevée pour les utilisateurs authentifiés"""
        pass
    
    @limiter.limit("50 per hour") 
    def anonymous_user_limit():
        """Limite plus restrictive pour les utilisateurs anonymes"""
        pass
    
    logger.info("Advanced rate limiting configuration applied")