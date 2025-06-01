"""
Optimiseur d'assets pour NinjaLead.ai
Compression, minification et gestion des ressources statiques
"""

import os
import gzip
import hashlib
import mimetypes
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AssetOptimizer:
    """Optimiseur pour les assets statiques (CSS, JS, images)"""
    
    def __init__(self, static_folder='static'):
        self.static_folder = static_folder
        self.compressed_files = {}
        
    def compress_static_files(self):
        """Compresse tous les fichiers statiques éligibles"""
        compressible_types = {
            '.css', '.js', '.html', '.json', '.xml', '.txt', '.svg'
        }
        
        compressed_count = 0
        static_path = Path(self.static_folder)
        
        if not static_path.exists():
            logger.warning(f"Static folder {self.static_folder} not found")
            return 0
            
        for file_path in static_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in compressible_types:
                try:
                    compressed_file = self._compress_file(file_path)
                    if compressed_file:
                        self.compressed_files[str(file_path)] = compressed_file
                        compressed_count += 1
                        logger.info(f"Compressed: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to compress {file_path}: {e}")
                    
        logger.info(f"Compressed {compressed_count} static files")
        return compressed_count
    
    def _compress_file(self, file_path):
        """Compresse un fichier individuel avec gzip"""
        try:
            with open(file_path, 'rb') as f_in:
                content = f_in.read()
                
            # Compresse seulement si le fichier fait plus de 1KB
            if len(content) < 1024:
                return None
                
            compressed_path = str(file_path) + '.gz'
            
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.write(content)
                
            # Vérifie que la compression est efficace (au moins 10% de gain)
            original_size = len(content)
            compressed_size = os.path.getsize(compressed_path)
            
            if compressed_size >= original_size * 0.9:
                os.remove(compressed_path)
                return None
                
            compression_ratio = (1 - compressed_size / original_size) * 100
            logger.info(f"Compressed {file_path.name}: {compression_ratio:.1f}% reduction")
            
            return {
                'path': compressed_path,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'ratio': compression_ratio
            }
            
        except Exception as e:
            logger.error(f"Compression error for {file_path}: {e}")
            return None
    
    def generate_file_hashes(self):
        """Génère des hashes pour le cache busting"""
        hashes = {}
        static_path = Path(self.static_folder)
        
        for file_path in static_path.rglob('*'):
            if file_path.is_file() and not file_path.name.endswith('.gz'):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        file_hash = hashlib.md5(content).hexdigest()[:8]
                        relative_path = file_path.relative_to(static_path)
                        hashes[str(relative_path)] = file_hash
                except Exception as e:
                    logger.warning(f"Failed to hash {file_path}: {e}")
                    
        return hashes
    
    def get_optimization_stats(self):
        """Retourne les statistiques d'optimisation"""
        total_original = sum(f['original_size'] for f in self.compressed_files.values())
        total_compressed = sum(f['compressed_size'] for f in self.compressed_files.values())
        
        if total_original == 0:
            return {"message": "No files compressed yet"}
            
        total_savings = total_original - total_compressed
        savings_percentage = (total_savings / total_original) * 100
        
        return {
            'files_compressed': len(self.compressed_files),
            'total_original_size': self._format_bytes(total_original),
            'total_compressed_size': self._format_bytes(total_compressed),
            'total_savings': self._format_bytes(total_savings),
            'savings_percentage': round(savings_percentage, 1)
        }
    
    def _format_bytes(self, bytes_count):
        """Formate les octets en unités lisibles"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

def optimize_css_delivery():
    """Optimise le chargement CSS critique"""
    css_optimizations = {
        'critical_css': [
            'css/markeasy-theme.css',
            'css/dashboard-improvements.css'
        ],
        'defer_css': [
            'css/custom.css',
            'css/orange-theme.css',
            'css/brand-ai-fix.css'
        ]
    }
    return css_optimizations

def setup_asset_headers():
    """Configuration des en-têtes pour l'optimisation des assets"""
    return {
        'Cache-Control': {
            '.css': 'public, max-age=31536000',  # 1 an
            '.js': 'public, max-age=31536000',   # 1 an
            '.png': 'public, max-age=31536000',  # 1 an
            '.jpg': 'public, max-age=31536000',  # 1 an
            '.svg': 'public, max-age=31536000',  # 1 an
            '.woff2': 'public, max-age=31536000', # 1 an
        },
        'Content-Encoding': 'gzip',
        'Vary': 'Accept-Encoding'
    }

def preload_critical_resources():
    """Liste des ressources critiques à précharger"""
    return [
        {'href': '/static/css/markeasy-theme.css', 'as': 'style'},
        {'href': '/static/js/markeasy-animations.js', 'as': 'script'},
        {'href': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600&family=Poppins:wght@700&display=swap', 'as': 'style'},
    ]

# Instance globale de l'optimiseur
asset_optimizer = AssetOptimizer()