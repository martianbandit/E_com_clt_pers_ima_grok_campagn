"""
Pipeline d'optimisation d'images avec redimensionnement,
compression et génération de formats modernes (WebP)
"""

import os
import logging
from PIL import Image, ImageOps
import hashlib
import json
from pathlib import Path
from flask import current_app
import time

logger = logging.getLogger(__name__)

class ImageOptimizer:
    """Optimiseur d'images avec support multi-format et cache intelligent"""
    
    def __init__(self, app=None):
        self.app = app
        self.cache_dir = None
        self.optimization_enabled = True
        self.webp_enabled = True
        self.quality_settings = {
            'high': 85,
            'medium': 75,
            'low': 60
        }
        self.size_presets = {
            'thumbnail': (150, 150),
            'small': (300, 300),
            'medium': (600, 600),
            'large': (1200, 1200),
            'xlarge': (1920, 1920)
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise l'optimiseur avec l'application Flask"""
        self.app = app
        
        # Configuration du cache d'images optimisées
        if app and hasattr(app, 'instance_path'):
            self.cache_dir = os.path.join(app.instance_path, 'optimized_images')
        else:
            self.cache_dir = os.path.join(os.getcwd(), 'optimized_images')
        
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Configuration depuis l'environnement
        self.optimization_enabled = os.environ.get('IMAGE_OPTIMIZATION', 'true').lower() == 'true'
        self.webp_enabled = os.environ.get('WEBP_SUPPORT', 'true').lower() == 'true'
        
        logger.info(f"Optimiseur d'images initialisé - Cache: {self.cache_dir}")
        
        # Enregistrement des routes
        self._register_routes()
    
    def _register_routes(self):
        """Enregistre les routes pour servir les images optimisées"""
        
        @self.app.route('/optimized-images/<path:filename>')
        def serve_optimized_image(filename):
            """Sert une image optimisée"""
            return self.serve_optimized_image(filename)
    
    def optimize_image(self, image_path, size_preset='medium', quality='medium', format_output=None):
        """
        Optimise une image selon les paramètres spécifiés
        
        Args:
            image_path: Chemin vers l'image source
            size_preset: Taille cible ('thumbnail', 'small', 'medium', 'large', 'xlarge')
            quality: Qualité de compression ('high', 'medium', 'low')
            format_output: Format de sortie ('webp', 'jpeg', 'png', None pour auto)
            
        Returns:
            dict: Informations sur l'image optimisée
        """
        if not self.optimization_enabled:
            return {'error': 'Optimisation désactivée'}
        
        if not os.path.exists(image_path):
            return {'error': 'Image source introuvable'}
        
        try:
            # Génération du hash pour le cache
            file_hash = self._get_file_hash(image_path)
            cache_key = f"{file_hash}_{size_preset}_{quality}_{format_output or 'auto'}"
            
            # Vérification du cache
            cached_info = self._get_cached_image(cache_key)
            if cached_info:
                return cached_info
            
            # Ouverture et analyse de l'image
            with Image.open(image_path) as img:
                original_format = img.format
                original_size = img.size
                original_file_size = os.path.getsize(image_path)
                
                # Correction de l'orientation EXIF
                img = ImageOps.exif_transpose(img)
                
                # Redimensionnement selon le preset
                target_size = self.size_presets.get(size_preset, self.size_presets['medium'])
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Détermination du format de sortie
                if format_output is None:
                    if self.webp_enabled and original_format in ['JPEG', 'PNG']:
                        output_format = 'WEBP'
                        file_extension = '.webp'
                    else:
                        output_format = original_format or 'JPEG'
                        file_extension = f".{output_format.lower()}"
                else:
                    output_format = format_output.upper()
                    file_extension = f".{format_output.lower()}"
                
                # Conversion en RGB si nécessaire pour JPEG/WebP
                if output_format in ['JPEG', 'WEBP'] and img.mode in ['RGBA', 'P']:
                    # Création d'un fond blanc pour la transparence
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Sauvegarde de l'image optimisée
                optimized_filename = f"{cache_key}{file_extension}"
                optimized_path = os.path.join(self.cache_dir, optimized_filename)
                
                save_kwargs = {
                    'format': output_format,
                    'optimize': True
                }
                
                if output_format in ['JPEG', 'WEBP']:
                    save_kwargs['quality'] = self.quality_settings[quality]
                
                if output_format == 'PNG':
                    save_kwargs['compress_level'] = 9
                
                img.save(optimized_path, **save_kwargs)
                
                # Calcul des métriques
                optimized_file_size = os.path.getsize(optimized_path)
                compression_ratio = round((1 - optimized_file_size / original_file_size) * 100, 2)
                
                # Informations de l'image optimisée
                optimization_info = {
                    'original_path': image_path,
                    'optimized_filename': optimized_filename,
                    'optimized_path': optimized_path,
                    'original_format': original_format,
                    'output_format': output_format,
                    'original_size': original_size,
                    'optimized_size': img.size,
                    'original_file_size': original_file_size,
                    'optimized_file_size': optimized_file_size,
                    'compression_ratio': compression_ratio,
                    'size_preset': size_preset,
                    'quality': quality,
                    'timestamp': int(time.time()),
                    'cache_key': cache_key
                }
                
                # Sauvegarde dans le cache
                self._save_to_cache(cache_key, optimization_info)
                
                logger.info(f"Image optimisée: {image_path} -> {compression_ratio}% de réduction")
                return optimization_info
                
        except Exception as e:
            logger.error(f"Erreur optimisation image {image_path}: {e}")
            return {'error': str(e)}
    
    def generate_responsive_images(self, image_path, quality='medium'):
        """
        Génère toutes les tailles responsives d'une image
        
        Args:
            image_path: Chemin vers l'image source
            quality: Qualité de compression
            
        Returns:
            dict: Ensemble des images générées
        """
        results = {}
        
        for preset_name in self.size_presets.keys():
            # Génération en format original optimisé
            result = self.optimize_image(image_path, preset_name, quality)
            if 'error' not in result:
                results[f"{preset_name}"] = result
            
            # Génération en WebP si supporté
            if self.webp_enabled:
                webp_result = self.optimize_image(image_path, preset_name, quality, 'webp')
                if 'error' not in webp_result:
                    results[f"{preset_name}_webp"] = webp_result
        
        return results
    
    def get_optimized_url(self, image_path, size_preset='medium', quality='medium', format_output=None):
        """
        Retourne l'URL d'une image optimisée, en la générant si nécessaire
        
        Args:
            image_path: Chemin vers l'image source
            size_preset: Taille cible
            quality: Qualité de compression
            format_output: Format de sortie
            
        Returns:
            str: URL vers l'image optimisée
        """
        optimization_info = self.optimize_image(image_path, size_preset, quality, format_output)
        
        if 'error' in optimization_info:
            # Fallback vers l'image originale
            return f"/static/{os.path.basename(image_path)}"
        
        return f"/optimized-images/{optimization_info['optimized_filename']}"
    
    def serve_optimized_image(self, filename):
        """Sert une image optimisée avec les bons headers"""
        try:
            file_path = os.path.join(self.cache_dir, filename)
            
            if not os.path.exists(file_path):
                return "Image not found", 404
            
            # Headers de cache pour les images
            from flask import send_file
            return send_file(
                file_path,
                as_attachment=False,
                download_name=filename,
                max_age=2592000  # 30 jours
            )
            
        except Exception as e:
            logger.error(f"Erreur service image optimisée {filename}: {e}")
            return "Internal error", 500
    
    def _get_file_hash(self, filepath):
        """Génère un hash du fichier pour le cache"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()[:12]
        except Exception:
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
    
    def _get_cached_image(self, cache_key):
        """Récupère une image du cache si elle existe"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cached_info = json.load(f)
                
                # Vérification que le fichier optimisé existe toujours
                if os.path.exists(cached_info.get('optimized_path', '')):
                    return cached_info
        except Exception:
            pass
        
        return None
    
    def _save_to_cache(self, cache_key, optimization_info):
        """Sauvegarde les informations d'optimisation en cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(optimization_info, f, indent=2)
        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache image: {e}")
    
    def get_optimization_stats(self):
        """Retourne les statistiques d'optimisation"""
        stats = {
            'total_optimized': 0,
            'total_original_size': 0,
            'total_optimized_size': 0,
            'total_savings_mb': 0,
            'avg_compression_ratio': 0,
            'cache_dir': self.cache_dir,
            'optimization_enabled': self.optimization_enabled,
            'webp_enabled': self.webp_enabled
        }
        
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            
            for cache_file in cache_files:
                try:
                    with open(os.path.join(self.cache_dir, cache_file), 'r') as f:
                        info = json.load(f)
                    
                    stats['total_optimized'] += 1
                    stats['total_original_size'] += info.get('original_file_size', 0)
                    stats['total_optimized_size'] += info.get('optimized_file_size', 0)
                    
                except Exception:
                    continue
            
            if stats['total_original_size'] > 0:
                total_savings = stats['total_original_size'] - stats['total_optimized_size']
                stats['total_savings_mb'] = round(total_savings / (1024 * 1024), 2)
                stats['avg_compression_ratio'] = round((total_savings / stats['total_original_size']) * 100, 2)
            
        except Exception as e:
            logger.error(f"Erreur calcul stats optimisation: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def clear_cache(self):
        """Vide le cache d'optimisation"""
        try:
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
            
            logger.info("Cache d'optimisation d'images vidé")
            return True
        except Exception as e:
            logger.error(f"Erreur vidage cache images: {e}")
            return False

# Instance globale
image_optimizer = ImageOptimizer()

def init_image_optimization(app):
    """Initialise l'optimisation d'images pour l'application"""
    try:
        image_optimizer.init_app(app)
        
        # Injection des fonctions dans les templates
        @app.context_processor
        def inject_image_functions():
            return {
                'optimized_image_url': image_optimizer.get_optimized_url,
                'responsive_images': image_optimizer.generate_responsive_images
            }
        
        logger.info("Système d'optimisation d'images initialisé")
        return image_optimizer
        
    except Exception as e:
        logger.error(f"Erreur initialisation optimisation images: {e}")
        return None