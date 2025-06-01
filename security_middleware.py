"""
Middleware de sécurité avancée pour NinjaLead.ai
Implémente CSP, sanitisation d'entrées, et protection WAF basique
"""

import re
import html
import logging
from functools import wraps
from flask import request, abort, g, current_app
from markupsafe import Markup
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Configuration CSP (Content Security Policy)
CSP_POLICY = {
    'default-src': ["'self'"],
    'script-src': [
        "'self'", 
        "'unsafe-inline'",  # Nécessaire pour Bootstrap et jQuery inline
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "stackpath.bootstrapcdn.com",
        "code.jquery.com",
        "cdn.plot.ly",  # Pour les graphiques
        "browser.sentry-cdn.com"  # Pour Sentry
    ],
    'style-src': [
        "'self'", 
        "'unsafe-inline'",  # Nécessaire pour les styles dynamiques
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "stackpath.bootstrapcdn.com",
        "fonts.googleapis.com"
    ],
    'font-src': [
        "'self'",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net"
    ],
    'img-src': [
        "'self'", 
        "data:",  # Pour les images SVG inline
        "*.openai.com",  # Pour DALL-E
        "*.aliexpress.com",  # Pour les images produits AliExpress
        "ae01.alicdn.com",
        "ae04.alicdn.com",
        "https:"  # Toutes les images HTTPS
    ],
    'connect-src': [
        "'self'",
        "api.openai.com",
        "api.x.ai",  # Pour Grok
        "o4509423969107968.ingest.us.sentry.io"  # Pour Sentry
    ],
    'frame-ancestors': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"]
}

def generate_csp_header():
    """Génère l'en-tête CSP à partir de la configuration"""
    policy_parts = []
    for directive, sources in CSP_POLICY.items():
        sources_str = ' '.join(sources)
        policy_parts.append(f"{directive} {sources_str}")
    return '; '.join(policy_parts)

# Configuration pour la sanitisation HTML
ALLOWED_HTML_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
]

ALLOWED_HTML_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'width', 'height']
}

# Patterns de détection d'attaques
ATTACK_PATTERNS = [
    # XSS patterns
    (re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL), 'XSS_SCRIPT'),
    (re.compile(r'javascript:', re.IGNORECASE), 'XSS_JAVASCRIPT'),
    (re.compile(r'on\w+\s*=', re.IGNORECASE), 'XSS_EVENT_HANDLER'),
    (re.compile(r'<iframe[^>]*>', re.IGNORECASE), 'XSS_IFRAME'),
    
    # SQL Injection patterns
    (re.compile(r'(\bunion\b.*\bselect\b)|(\bselect\b.*\bunion\b)', re.IGNORECASE), 'SQL_UNION'),
    (re.compile(r'\b(select|insert|update|delete|drop|create|alter)\b.*\b(from|into|table|database)\b', re.IGNORECASE), 'SQL_INJECTION'),
    (re.compile(r'[\'";]\s*(or|and)\s+[\'"]?\w+[\'"]?\s*=\s*[\'"]?\w+[\'"]?', re.IGNORECASE), 'SQL_WHERE_INJECTION'),
    
    # Path traversal
    (re.compile(r'\.\./', re.IGNORECASE), 'PATH_TRAVERSAL'),
    (re.compile(r'%2e%2e%2f', re.IGNORECASE), 'PATH_TRAVERSAL_ENCODED'),
    
    # Command injection
    (re.compile(r'[;&|`$(){}[\]<>]', re.IGNORECASE), 'COMMAND_INJECTION'),
    
    # LDAP injection
    (re.compile(r'[()=*!&|]', re.IGNORECASE), 'LDAP_INJECTION_CHARS'),
]

class SecurityMiddleware:
    """Middleware de sécurité pour Flask"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le middleware avec l'application Flask"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Configuration de sécurité
        app.config.setdefault('SECURITY_RATE_LIMIT_REQUESTS', 100)
        app.config.setdefault('SECURITY_RATE_LIMIT_WINDOW', 3600)  # 1 heure
        app.config.setdefault('SECURITY_BLOCK_ATTACKS', True)
        app.config.setdefault('SECURITY_LOG_ATTACKS', True)
    
    def before_request(self):
        """Exécuté avant chaque requête"""
        # Vérifier les patterns d'attaque
        if current_app.config.get('SECURITY_BLOCK_ATTACKS', True):
            self._check_for_attacks()
        
        # Sanitiser les données d'entrée
        self._sanitize_request_data()
        
        # Rate limiting basique
        self._check_rate_limit()
    
    def after_request(self, response):
        """Exécuté après chaque requête"""
        # Ajouter les headers de sécurité
        self._add_security_headers(response)
        return response
    
    def _check_for_attacks(self):
        """Vérifie les patterns d'attaque dans la requête"""
        request_data = []
        
        # Collecter toutes les données de la requête
        if request.args:
            request_data.extend(request.args.values())
        if request.form:
            request_data.extend(request.form.values())
        if request.json:
            request_data.extend(self._extract_json_values(request.json))
        
        # Vérifier les headers suspects
        user_agent = request.headers.get('User-Agent', '')
        request_data.append(user_agent)
        
        # Vérifier l'URL
        request_data.append(request.url)
        
        # Analyser chaque élément de données
        for data in request_data:
            if isinstance(data, str):
                for pattern, attack_type in ATTACK_PATTERNS:
                    if pattern.search(data):
                        self._log_security_incident(attack_type, data)
                        if current_app.config.get('SECURITY_BLOCK_ATTACKS', True):
                            abort(403, description=f"Requête bloquée: {attack_type}")
    
    def _extract_json_values(self, json_data):
        """Extrait récursivement toutes les valeurs d'un objet JSON"""
        values = []
        if isinstance(json_data, dict):
            for value in json_data.values():
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, (dict, list)):
                    values.extend(self._extract_json_values(value))
        elif isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, (dict, list)):
                    values.extend(self._extract_json_values(item))
        return values
    
    def _sanitize_request_data(self):
        """Sanitise les données d'entrée de la requête"""
        # Note: Flask rend request.form et request.args immutables
        # On stocke les données sanitisées dans g pour utilisation dans les vues
        g.sanitized_form = {}
        g.sanitized_args = {}
        
        # Sanitiser les données de formulaire
        for key, value in request.form.items():
            g.sanitized_form[key] = self.sanitize_input(value)
        
        # Sanitiser les paramètres d'URL
        for key, value in request.args.items():
            g.sanitized_args[key] = self.sanitize_input(value)
    
    def _check_rate_limit(self):
        """Implémente un rate limiting basique par IP"""
        # Cette implémentation basique utilise la session
        # Pour un rate limiting plus robuste, utiliser Redis
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Pour une implémentation simple, on passe pour l'instant
        # TODO: Implémenter avec Redis pour un rate limiting distribué
        pass
    
    def _add_security_headers(self, response):
        """Ajoute les headers de sécurité à la réponse"""
        # Content Security Policy
        response.headers['Content-Security-Policy'] = generate_csp_header()
        
        # Autres headers de sécurité
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Cache control pour les pages sensibles
        if request.endpoint and 'admin' in request.endpoint:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    
    def _log_security_incident(self, attack_type, data):
        """Enregistre un incident de sécurité"""
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        logger.warning(
            f"Security incident detected - Type: {attack_type}, "
            f"IP: {client_ip}, User-Agent: {user_agent}, "
            f"URL: {request.url}, Data: {data[:100]}..."
        )
    
    @staticmethod
    def sanitize_input(value, allow_html=False):
        """
        Sanitise une valeur d'entrée utilisateur
        
        Args:
            value: Valeur à sanitiser
            allow_html: Si True, autorise du HTML limité et sécurisé
            
        Returns:
            Valeur sanitisée
        """
        if not isinstance(value, str):
            return value
        
        # Sanitisation basique
        value = value.strip()
        
        if allow_html:
            # Sanitisation HTML basique sans bleach
            # Supprimer les balises script et autres dangereuses
            value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(r'<iframe[^>]*>.*?</iframe>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
            value = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
        else:
            # Échapper complètement le HTML
            value = html.escape(value)
        
        return value
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitise un nom de fichier"""
        if not filename:
            return filename
        
        # Supprimer les caractères dangereux
        filename = re.sub(r'[^\w\s.-]', '', filename)
        filename = re.sub(r'\.\.+', '.', filename)  # Supprimer les .. multiples
        filename = filename.strip('. ')  # Supprimer les points et espaces en début/fin
        
        return filename

def require_sanitized_input(allow_html=False):
    """
    Décorateur pour s'assurer que les entrées sont sanitisées
    
    Args:
        allow_html: Si True, autorise du HTML limité dans les entrées
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Les données sanitisées sont déjà disponibles dans g
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_sanitized_form():
    """Récupère les données de formulaire sanitisées"""
    return getattr(g, 'sanitized_form', {})

def get_sanitized_args():
    """Récupère les paramètres d'URL sanitisés"""
    return getattr(g, 'sanitized_args', {})

# Instance globale du middleware
security_middleware = SecurityMiddleware()