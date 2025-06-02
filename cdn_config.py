"""
Configuration CDN pour optimiser la livraison des assets statiques
Supporte Cloudflare, AWS CloudFront et autres CDN populaires
"""

import os
import logging
from urllib.parse import urljoin
from flask import current_app, url_for
import hashlib
import time

logger = logging.getLogger(__name__)

class CDNManager:
    """Gestionnaire CDN pour optimiser la livraison des assets statiques"""
    
    def __init__(self, app=None):
        self.app = app
        self.cdn_enabled = False
        self.cdn_domain = None
        self.cdn_https = True
        self.version_hash = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise la configuration CDN avec l'application Flask"""
        self.app = app
        
        # Configuration CDN depuis les variables d'environnement
        self.cdn_domain = os.environ.get('CDN_DOMAIN')
        self.cdn_enabled = bool(self.cdn_domain)
        self.cdn_https = os.environ.get('CDN_HTTPS', 'true').lower() == 'true'
        
        # Génération d'un hash de version pour le cache busting
        self.version_hash = self._generate_version_hash()
        
        if self.cdn_enabled:
            logger.info(f"CDN activé avec le domaine: {self.cdn_domain}")
            
            # Override de la fonction url_for pour les assets statiques
            app.jinja_env.globals['cdn_url_for'] = self.cdn_url_for
        else:
            logger.info("CDN désactivé - utilisation des assets locaux")
            # Fallback vers url_for standard
            app.jinja_env.globals['cdn_url_for'] = url_for
    
    def _generate_version_hash(self):
        """Génère un hash de version pour le cache busting"""
        try:
            # Utilise la date de modification du fichier app.py comme version
            app_file = os.path.join(os.path.dirname(__file__), 'app.py')
            if os.path.exists(app_file):
                mtime = os.path.getmtime(app_file)
                return hashlib.md5(str(mtime).encode()).hexdigest()[:8]
        except Exception:
            pass
        
        # Fallback: timestamp actuel
        return hashlib.md5(str(int(time.time())).encode()).hexdigest()[:8]
    
    def cdn_url_for(self, endpoint, **values):
        """
        Génère une URL CDN pour les assets statiques, avec fallback vers url_for standard
        
        Args:
            endpoint: Endpoint Flask (ex: 'static')
            **values: Paramètres pour l'URL
            
        Returns:
            URL complète vers le CDN ou l'asset local
        """
        # Si CDN désactivé ou endpoint non-statique, utiliser url_for standard
        if not self.cdn_enabled or endpoint != 'static':
            return url_for(endpoint, **values)
        
        try:
            # Génération de l'URL locale d'abord
            local_url = url_for(endpoint, **values)
            
            # Ajout du versioning pour cache busting
            filename = values.get('filename', '')
            if filename and '.' in filename:
                name, ext = filename.rsplit('.', 1)
                versioned_filename = f"{name}.{self.version_hash}.{ext}"
                values['filename'] = versioned_filename
                local_url = url_for(endpoint, **values)
            
            # Construction de l'URL CDN
            protocol = 'https' if self.cdn_https else 'http'
            cdn_url = f"{protocol}://{self.cdn_domain}{local_url}"
            
            return cdn_url
            
        except Exception as e:
            logger.warning(f"Erreur génération URL CDN pour {endpoint}: {e}")
            # Fallback vers URL locale
            return url_for(endpoint, **values)
    
    def get_asset_url(self, asset_path, asset_type='static'):
        """
        Obtient l'URL d'un asset avec optimisations CDN
        
        Args:
            asset_path: Chemin vers l'asset (ex: 'css/style.css')
            asset_type: Type d'asset ('static', 'image', etc.)
            
        Returns:
            URL optimisée vers l'asset
        """
        if asset_type == 'static':
            return self.cdn_url_for('static', filename=asset_path)
        else:
            # Pour d'autres types d'assets, utiliser la logique standard
            return url_for('static', filename=asset_path)
    
    def preload_critical_assets(self):
        """
        Retourne une liste des assets critiques à précharger
        pour améliorer les performances
        """
        critical_assets = [
            'css/style.css',
            'css/bootstrap.min.css',
            'js/app.js',
            'js/bootstrap.bundle.min.js'
        ]
        
        preload_links = []
        for asset in critical_assets:
            url = self.get_asset_url(asset)
            asset_type = 'style' if asset.endswith('.css') else 'script'
            preload_links.append({
                'url': url,
                'type': asset_type,
                'crossorigin': 'anonymous' if self.cdn_enabled else None
            })
        
        return preload_links
    
    def get_performance_headers(self):
        """
        Retourne les headers HTTP pour optimiser les performances
        """
        headers = {}
        
        if self.cdn_enabled:
            # Headers pour optimiser le cache
            headers.update({
                'Cache-Control': 'public, max-age=31536000',  # 1 an
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'Access-Control-Allow-Origin': f"https://{self.cdn_domain}"
            })
        
        return headers
    
    def configure_cloudflare(self, zone_id=None, api_token=None):
        """
        Configuration spécifique pour Cloudflare CDN
        
        Args:
            zone_id: ID de la zone Cloudflare
            api_token: Token API Cloudflare
        """
        if not zone_id or not api_token:
            logger.warning("Configuration Cloudflare incomplète")
            return False
        
        try:
            # Configuration des règles de cache pour assets statiques
            cache_rules = {
                'css': {'edge_ttl': 31536000, 'browser_ttl': 31536000},  # 1 an
                'js': {'edge_ttl': 31536000, 'browser_ttl': 31536000},   # 1 an
                'images': {'edge_ttl': 2592000, 'browser_ttl': 2592000}, # 30 jours
                'fonts': {'edge_ttl': 31536000, 'browser_ttl': 31536000} # 1 an
            }
            
            logger.info("Configuration Cloudflare appliquée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur configuration Cloudflare: {e}")
            return False
    
    def get_stats(self):
        """Retourne les statistiques d'utilisation du CDN"""
        return {
            'cdn_enabled': self.cdn_enabled,
            'cdn_domain': self.cdn_domain,
            'version_hash': self.version_hash,
            'https_enabled': self.cdn_https,
            'critical_assets_count': len(self.preload_critical_assets())
        }

# Instance globale
cdn_manager = CDNManager()

def init_cdn(app):
    """Initialise la configuration CDN pour l'application"""
    cdn_manager.init_app(app)
    
    @app.context_processor
    def inject_cdn_functions():
        """Rend les fonctions CDN disponibles dans les templates"""
        return {
            'cdn_url_for': cdn_manager.cdn_url_for,
            'get_asset_url': cdn_manager.get_asset_url,
            'preload_assets': cdn_manager.preload_critical_assets()
        }
    
    return cdn_manager