"""
Système CDN simplifié pour optimiser la livraison des assets statiques
avec compression et cache intelligent
"""

import os
import gzip
import hashlib
import logging
from flask import current_app, send_from_directory, request
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class StaticAssetsCDN:
    """Gestionnaire CDN simplifié pour assets statiques"""
    
    def __init__(self, app=None):
        self.app = app
        self.cdn_domain = None
        self.compression_enabled = True
        self.cache_enabled = True
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le CDN avec l'application Flask"""
        self.app = app
        
        # Configuration depuis les variables d'environnement
        self.cdn_domain = os.environ.get('CDN_DOMAIN')
        self.compression_enabled = os.environ.get('ASSET_COMPRESSION', 'true').lower() == 'true'
        self.cache_enabled = os.environ.get('ASSET_CACHE', 'true').lower() == 'true'
        
        logger.info(f"CDN initialisé - Domaine: {self.cdn_domain or 'local'}, Compression: {self.compression_enabled}")
        
        # Enregistrement des routes d'optimisation
        self._register_routes(app)
        
        # Injection des fonctions dans les templates
        @app.context_processor
        def inject_cdn_functions():
            return {
                'cdn_url': self.get_asset_url,
                'optimized_url': self.get_optimized_url
            }
    
    def _register_routes(self, app):
        """Enregistre les routes pour servir les assets optimisés"""
        
        @app.route('/assets/<path:filename>')
        def serve_optimized_static(filename):
            """Sert les assets statiques avec optimisations"""
            return self.serve_optimized_file(filename)
    
    def get_asset_url(self, filename):
        """
        Génère l'URL optimale pour un asset statique
        
        Args:
            filename: Nom du fichier dans le dossier static
            
        Returns:
            URL complète vers l'asset (CDN ou local optimisé)
        """
        if self.cdn_domain:
            # Utilisation du CDN externe
            return f"https://{self.cdn_domain}/static/{filename}"
        else:
            # Utilisation du serveur local optimisé
            return f"/assets/{filename}"
    
    def get_optimized_url(self, filename):
        """Alias pour get_asset_url pour compatibilité"""
        return self.get_asset_url(filename)
    
    def serve_optimized_file(self, filename):
        """
        Sert un fichier statique avec optimisations (compression, cache)
        
        Args:
            filename: Chemin relatif du fichier dans static/
            
        Returns:
            Réponse Flask avec le fichier optimisé
        """
        try:
            static_dir = os.path.join(self.app.root_path, 'static')
            file_path = os.path.join(static_dir, filename)
            
            # Vérification d'existence
            if not os.path.exists(file_path):
                return "Asset not found", 404
            
            # Vérification de sécurité pour éviter les directory traversal
            if not os.path.abspath(file_path).startswith(os.path.abspath(static_dir)):
                return "Access denied", 403
            
            # Headers de cache agressif
            headers = {}
            if self.cache_enabled:
                headers.update({
                    'Cache-Control': 'public, max-age=31536000',  # 1 an
                    'X-CDN-Cache': 'HIT',
                    'Vary': 'Accept-Encoding'
                })
            
            # Gestion de la compression gzip
            if self.compression_enabled and self._should_compress(filename):
                accept_encoding = request.headers.get('Accept-Encoding', '')
                if 'gzip' in accept_encoding:
                    compressed_content = self._get_compressed_content(file_path)
                    if compressed_content:
                        headers['Content-Encoding'] = 'gzip'
                        headers['Content-Length'] = str(len(compressed_content))
                        
                        # Retour du contenu compressé
                        from flask import Response
                        mimetype = self._get_mimetype(filename)
                        return Response(
                            compressed_content, 
                            mimetype=mimetype,
                            headers=headers
                        )
            
            # Retour du fichier standard avec headers optimisés
            return send_from_directory(
                static_dir, 
                filename, 
                as_attachment=False,
                mimetype=self._get_mimetype(filename),
                add_etags=True,
                last_modified=None,
                max_age=31536000 if self.cache_enabled else None
            )
            
        except Exception as e:
            logger.error(f"Erreur service asset {filename}: {e}")
            return "Internal server error", 500
    
    def _should_compress(self, filename):
        """Détermine si un fichier doit être compressé"""
        compress_extensions = {'.css', '.js', '.html', '.svg', '.json', '.xml'}
        return any(filename.lower().endswith(ext) for ext in compress_extensions)
    
    def _get_compressed_content(self, file_path):
        """
        Obtient le contenu compressé d'un fichier
        
        Args:
            file_path: Chemin complet vers le fichier
            
        Returns:
            Contenu compressé en bytes ou None si erreur
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Compression gzip en mémoire
            import io
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb') as gz_file:
                gz_file.write(content)
            
            compressed = buffer.getvalue()
            
            # Vérification que la compression est bénéfique
            if len(compressed) < len(content) * 0.9:  # Au moins 10% de gain
                return compressed
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur compression {file_path}: {e}")
            return None
    
    def _get_mimetype(self, filename):
        """Détermine le type MIME d'un fichier"""
        import mimetypes
        mimetype, _ = mimetypes.guess_type(filename)
        return mimetype or 'application/octet-stream'
    
    def get_compression_stats(self):
        """Retourne les statistiques de compression"""
        static_dir = os.path.join(self.app.root_path, 'static')
        if not os.path.exists(static_dir):
            return {'error': 'Static directory not found'}
        
        stats = {
            'total_files': 0,
            'compressible_files': 0,
            'total_size': 0,
            'potential_compressed_size': 0,
            'compression_enabled': self.compression_enabled,
            'cdn_domain': self.cdn_domain
        }
        
        try:
            for root, dirs, files in os.walk(static_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    
                    stats['total_files'] += 1
                    stats['total_size'] += file_size
                    
                    if self._should_compress(file):
                        stats['compressible_files'] += 1
                        # Estimation de compression (typiquement 60-70% pour CSS/JS)
                        stats['potential_compressed_size'] += int(file_size * 0.35)
                    else:
                        stats['potential_compressed_size'] += file_size
            
            # Calcul du gain potentiel
            if stats['total_size'] > 0:
                savings = stats['total_size'] - stats['potential_compressed_size']
                stats['potential_savings_mb'] = round(savings / (1024 * 1024), 2)
                stats['compression_ratio'] = round((savings / stats['total_size']) * 100, 2)
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def configure_headers_for_cdn(self):
        """Configure les headers HTTP pour optimiser avec un CDN"""
        
        @self.app.after_request
        def add_cdn_headers(response):
            # Headers pour tous les assets statiques
            if request.endpoint == 'static' or request.path.startswith('/assets/'):
                response.headers.update({
                    'Cache-Control': 'public, max-age=31536000',
                    'X-Content-Type-Options': 'nosniff',
                    'Access-Control-Allow-Origin': '*',
                    'Vary': 'Accept-Encoding'
                })
                
                # ETag basé sur le contenu
                if hasattr(response, 'data') and response.data:
                    etag = hashlib.md5(response.data).hexdigest()
                    response.headers['ETag'] = f'"{etag}"'
            
            return response

# Instance globale
static_cdn = StaticAssetsCDN()

def init_static_cdn(app):
    """Initialise le système CDN pour l'application"""
    static_cdn.init_app(app)
    static_cdn.configure_headers_for_cdn()
    
    logger.info("Système CDN pour assets statiques initialisé")
    return static_cdn