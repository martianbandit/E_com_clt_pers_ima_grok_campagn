"""
Module de sécurité avancée pour NinjaLead
Implémente Flask-Talisman, rate limiting et headers de sécurité
"""

import os
from flask import request, jsonify
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

# Configuration Talisman pour headers de sécurité
TALISMAN_CONFIG = {
    'force_https': False,  # Désactivé pour dev local
    'strict_transport_security': True,
    'strict_transport_security_max_age': 31536000,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            'cdnjs.cloudflare.com',
            'cdn.jsdelivr.net',
            'code.jquery.com'
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'cdnjs.cloudflare.com',
            'fonts.googleapis.com'
        ],
        'font-src': [
            "'self'",
            'fonts.gstatic.com',
            'cdnjs.cloudflare.com'
        ],
        'img-src': [
            "'self'",
            'data:',
            'https:'
        ],
        'connect-src': "'self'"
    },
    'referrer_policy': 'strict-origin-when-cross-origin',
    'feature_policy': {
        'geolocation': "'none'",
        'camera': "'none'",
        'microphone': "'none'"
    }
}

def init_security_extensions(app):
    """Initialise les extensions de sécurité"""
    
    # Flask-Talisman pour les headers de sécurité
    talisman = Talisman(app, **TALISMAN_CONFIG)
    
    # Flask-Limiter pour le rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://",  # Utiliser Redis en production
        strategy="fixed-window"
    )
    limiter.init_app(app)
    
    # Configuration des sessions sécurisées
    app.config.update(
        SESSION_COOKIE_SECURE=True,  # HTTPS uniquement
        SESSION_COOKIE_HTTPONLY=True,  # Pas d'accès JavaScript
        SESSION_COOKIE_SAMESITE='Lax',  # Protection CSRF
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,  # 1 heure
        PERMANENT_SESSION_LIFETIME=86400  # 24 heures
    )
    
    logging.info("Security extensions initialized successfully")
    
    return talisman, limiter

def apply_rate_limits(app, limiter):
    """Applique des limites spécifiques aux endpoints sensibles"""
    
    @app.route('/api/auth/login', methods=['POST'])
    @limiter.limit("5 per minute")
    def secure_login():
        return jsonify({"message": "Login endpoint with rate limiting"})
    
    @app.route('/api/auth/register', methods=['POST'])
    @limiter.limit("3 per minute")
    def secure_register():
        return jsonify({"message": "Register endpoint with rate limiting"})
    
    @app.route('/api/generate', methods=['POST'])
    @limiter.limit("10 per minute")
    def secure_generate():
        return jsonify({"message": "AI generation endpoint with rate limiting"})

def add_security_headers(app):
    """Ajoute des headers de sécurité personnalisés"""
    
    @app.after_request
    def security_headers(response):
        # Headers de sécurité supplémentaires
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Header personnalisé pour identifier l'application
        response.headers['X-Powered-By'] = 'NinjaLead-Secure'
        
        return response

def setup_error_handlers(app):
    """Configure les gestionnaires d'erreur sécurisés"""
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(e, 'retry_after', 60)
        }), 429
    
    @app.errorhandler(403)
    def forbidden_handler(e):
        return jsonify({
            "error": "Access forbidden",
            "message": "You don't have permission to access this resource."
        }), 403
    
    @app.errorhandler(404)
    def not_found_handler(e):
        return jsonify({
            "error": "Resource not found",
            "message": "The requested resource could not be found."
        }), 404
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }), 500

def validate_input_security(data):
    """Valide et nettoie les données d'entrée"""
    
    if isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            # Nettoyer les clés et valeurs
            if isinstance(value, str):
                # Supprime les caractères potentiellement dangereux
                cleaned_value = value.replace('<', '&lt;').replace('>', '&gt;')
                cleaned_data[key] = cleaned_value
            else:
                cleaned_data[key] = value
        return cleaned_data
    
    return data

def log_security_event(event_type, details, request_info=None):
    """Enregistre les événements de sécurité"""
    
    if request_info is None:
        request_info = {
            'ip': get_remote_address(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'endpoint': request.endpoint
        }
    
    security_log = {
        'timestamp': os.popen('date -Iseconds').read().strip(),
        'event_type': event_type,
        'details': details,
        'request_info': request_info
    }
    
    logging.warning(f"SECURITY_EVENT: {security_log}")
    
    # En production, envoyer vers un système de monitoring dédié
    return security_log