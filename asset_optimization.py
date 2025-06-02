"""
Optimisation automatique des assets statiques (CSS, JS, images)
avec compression, minification et cache intelligent
"""

import os
import gzip
import hashlib
import json
import logging
from pathlib import Path
import mimetypes
from flask import current_app, send_file, request
import time

logger = logging.getLogger(__name__)

class AssetOptimizer:
    """Optimiseur d'assets avec compression et cache"""
    
    def __init__(self, app=None):
        self.app = app
        self.cache_dir = None
        self.compression_enabled = True
        self.minification_enabled = True
        self.cache_manifest = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise l'optimiseur avec l'application Flask"""
        self.app = app
        
        # Configuration du cache
        if app and hasattr(app, 'instance_path'):
            self.cache_dir = os.path.join(app.instance_path, 'asset_cache')
        else:
            self.cache_dir = os.path.join(os.getcwd(), 'asset_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Chargement du manifeste de cache existant
        self._load_cache_manifest()
        
        # Configuration depuis l'environnement
        self.compression_enabled = os.environ.get('ASSET_COMPRESSION', 'true').lower() == 'true'
        self.minification_enabled = os.environ.get('ASSET_MINIFICATION', 'true').lower() == 'true'
        
        logger.info(f"Asset optimizer initialisé - Compression: {self.compression_enabled}, Minification: {self.minification_enabled}")
        
        # Enregistrement des routes d'optimisation
        self._register_routes()
    
    def _load_cache_manifest(self):
        """Charge le manifeste de cache depuis le disque"""
        manifest_path = os.path.join(self.cache_dir, 'manifest.json')
        try:
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    self.cache_manifest = json.load(f)
        except Exception as e:
            logger.warning(f"Erreur chargement manifeste cache: {e}")
            self.cache_manifest = {}
    
    def _save_cache_manifest(self):
        """Sauvegarde le manifeste de cache sur le disque"""
        manifest_path = os.path.join(self.cache_dir, 'manifest.json')
        try:
            with open(manifest_path, 'w') as f:
                json.dump(self.cache_manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde manifeste cache: {e}")
    
    def _register_routes(self):
        """Enregistre les routes d'optimisation d'assets"""
        
        @self.app.route('/optimized-assets/<path:filename>')
        def serve_optimized_asset(filename):
            """Sert un asset optimisé avec compression et cache"""
            return self.serve_optimized_asset(filename)
    
    def get_file_hash(self, filepath):
        """Génère un hash du contenu d'un fichier"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return None
    
    def compress_file(self, source_path, target_path):
        """Compresse un fichier avec gzip"""
        try:
            with open(source_path, 'rb') as f_in:
                with gzip.open(target_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            return True
        except Exception as e:
            logger.error(f"Erreur compression {source_path}: {e}")
            return False
    
    def minify_css(self, css_content):
        """Minification CSS basique"""
        if not self.minification_enabled:
            return css_content
        
        try:
            # Suppression des commentaires CSS
            import re
            css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
            
            # Suppression des espaces multiples et retours à la ligne
            css_content = re.sub(r'\s+', ' ', css_content)
            css_content = re.sub(r';\s*}', '}', css_content)
            css_content = re.sub(r'{\s*', '{', css_content)
            css_content = re.sub(r';\s*', ';', css_content)
            
            return css_content.strip()
        except Exception as e:
            logger.warning(f"Erreur minification CSS: {e}")
            return css_content
    
    def minify_js(self, js_content):
        """Minification JavaScript basique"""
        if not self.minification_enabled:
            return js_content
        
        try:
            import re
            # Suppression des commentaires simples
            js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
            
            # Suppression des commentaires multi-lignes
            js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
            
            # Suppression des espaces multiples
            js_content = re.sub(r'\s+', ' ', js_content)
            
            return js_content.strip()
        except Exception as e:
            logger.warning(f"Erreur minification JS: {e}")
            return js_content
    
    def optimize_asset(self, asset_path):
        """
        Optimise un asset (minification + compression)
        
        Args:
            asset_path: Chemin vers l'asset à optimiser
            
        Returns:
            dict: Informations sur l'asset optimisé
        """
        static_dir = os.path.join(self.app.root_path, 'static')
        source_file = os.path.join(static_dir, asset_path)
        
        if not os.path.exists(source_file):
            return None
        
        # Vérification du cache
        file_hash = self.get_file_hash(source_file)
        cache_key = f"{asset_path}_{file_hash}"
        
        if cache_key in self.cache_manifest:
            cached_info = self.cache_manifest[cache_key]
            cached_file = os.path.join(self.cache_dir, cached_info['filename'])
            if os.path.exists(cached_file):
                return cached_info
        
        # Optimisation nécessaire
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Minification selon le type de fichier
            file_ext = Path(asset_path).suffix.lower()
            optimized_content = content
            
            if file_ext == '.css':
                optimized_content = self.minify_css(content)
            elif file_ext == '.js':
                optimized_content = self.minify_js(content)
            
            # Écriture du fichier optimisé
            optimized_filename = f"{file_hash}_{Path(asset_path).name}"
            optimized_path = os.path.join(self.cache_dir, optimized_filename)
            
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
            
            # Compression gzip si activée
            compressed_path = None
            if self.compression_enabled:
                compressed_filename = f"{optimized_filename}.gz"
                compressed_path = os.path.join(self.cache_dir, compressed_filename)
                with open(optimized_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            # Calcul des tailles
            original_size = os.path.getsize(source_file)
            optimized_size = os.path.getsize(optimized_path)
            compressed_size = os.path.getsize(compressed_path) if compressed_path else None
            
            # Mise à jour du cache
            asset_info = {
                'original_path': asset_path,
                'filename': optimized_filename,
                'compressed_filename': f"{optimized_filename}.gz" if compressed_path else None,
                'original_size': original_size,
                'optimized_size': optimized_size,
                'compressed_size': compressed_size,
                'compression_ratio': round((1 - optimized_size / original_size) * 100, 2),
                'timestamp': int(time.time()),
                'hash': file_hash
            }
            
            self.cache_manifest[cache_key] = asset_info
            self._save_cache_manifest()
            
            logger.info(f"Asset optimisé: {asset_path} - Réduction: {asset_info['compression_ratio']}%")
            return asset_info
            
        except Exception as e:
            logger.error(f"Erreur optimisation asset {asset_path}: {e}")
            return None
    
    def serve_optimized_asset(self, filename):
        """Sert un asset optimisé avec les bons headers de cache"""
        try:
            # Recherche de l'asset dans le manifeste
            asset_info = None
            for key, info in self.cache_manifest.items():
                if info['filename'] == filename:
                    asset_info = info
                    break
            
            if not asset_info:
                return "Asset not found", 404
            
            # Détermine quel fichier servir (compressé ou non)
            accept_encoding = request.headers.get('Accept-Encoding', '')
            
            if 'gzip' in accept_encoding and asset_info['compressed_filename']:
                file_path = os.path.join(self.cache_dir, asset_info['compressed_filename'])
                headers = {'Content-Encoding': 'gzip'}
            else:
                file_path = os.path.join(self.cache_dir, asset_info['filename'])
                headers = {}
            
            if not os.path.exists(file_path):
                return "Asset file not found", 404
            
            # Headers de cache agressif
            headers.update({
                'Cache-Control': 'public, max-age=31536000',  # 1 an
                'ETag': asset_info['hash'],
                'X-Compression-Ratio': str(asset_info['compression_ratio']),
                'X-Original-Size': str(asset_info['original_size']),
                'X-Optimized-Size': str(asset_info['optimized_size'])
            })
            
            # Détection du type MIME
            mimetype, _ = mimetypes.guess_type(asset_info['original_path'])
            
            return send_file(file_path, mimetype=mimetype, as_attachment=False, download_name=filename, headers=headers)
            
        except Exception as e:
            logger.error(f"Erreur service asset optimisé {filename}: {e}")
            return "Internal error", 500
    
    def optimize_all_assets(self):
        """Optimise tous les assets statiques du projet"""
        static_dir = os.path.join(self.app.root_path, 'static')
        if not os.path.exists(static_dir):
            return []
        
        optimized_assets = []
        
        # Parcours récursif des fichiers CSS et JS
        for root, dirs, files in os.walk(static_dir):
            for file in files:
                if file.endswith(('.css', '.js')):
                    rel_path = os.path.relpath(os.path.join(root, file), static_dir)
                    asset_info = self.optimize_asset(rel_path)
                    if asset_info:
                        optimized_assets.append(asset_info)
        
        return optimized_assets
    
    def get_optimization_stats(self):
        """Retourne les statistiques d'optimisation"""
        total_assets = len(self.cache_manifest)
        total_original_size = sum(info['original_size'] for info in self.cache_manifest.values())
        total_optimized_size = sum(info['optimized_size'] for info in self.cache_manifest.values())
        
        avg_compression = 0
        if total_original_size > 0:
            avg_compression = round((1 - total_optimized_size / total_original_size) * 100, 2)
        
        return {
            'total_assets': total_assets,
            'total_original_size_mb': round(total_original_size / (1024 * 1024), 2),
            'total_optimized_size_mb': round(total_optimized_size / (1024 * 1024), 2),
            'total_saved_mb': round((total_original_size - total_optimized_size) / (1024 * 1024), 2),
            'average_compression_ratio': avg_compression,
            'compression_enabled': self.compression_enabled,
            'minification_enabled': self.minification_enabled
        }
    
    def clear_cache(self):
        """Vide le cache d'optimisation"""
        try:
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
            
            self.cache_manifest = {}
            self._save_cache_manifest()
            
            logger.info("Cache d'optimisation vidé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
            return False

# Instance globale
asset_optimizer = AssetOptimizer()

def init_asset_optimization(app):
    """Initialise l'optimisation d'assets pour l'application"""
    asset_optimizer.init_app(app)
    return asset_optimizer