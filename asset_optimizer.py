"""
Module d'optimisation des assets statiques
Implémente la minification, compression et optimisation des ressources
"""

import os
import json
import hashlib
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

class AssetOptimizer:
    """Optimiseur d'assets statiques pour améliorer les performances"""
    
    def __init__(self, static_folder: str = "static"):
        self.static_folder = static_folder
        self.cache_manifest = {}
        self.load_cache_manifest()
    
    def load_cache_manifest(self):
        """Charge le manifeste du cache des assets"""
        manifest_path = os.path.join(self.static_folder, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    self.cache_manifest = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache manifest: {e}")
                self.cache_manifest = {}
    
    def save_cache_manifest(self):
        """Sauvegarde le manifeste du cache des assets"""
        try:
            os.makedirs(self.static_folder, exist_ok=True)
            manifest_path = os.path.join(self.static_folder, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(self.cache_manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache manifest: {e}")
    
    def minify_css(self, css_content: str) -> str:
        """Minifie le contenu CSS"""
        try:
            # Supprime les commentaires
            css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
            
            # Supprime les espaces superflus
            css_content = re.sub(r'\s+', ' ', css_content)
            css_content = re.sub(r';\s*}', '}', css_content)
            css_content = re.sub(r'{\s*', '{', css_content)
            css_content = re.sub(r'}\s*', '}', css_content)
            css_content = re.sub(r':\s*', ':', css_content)
            css_content = re.sub(r';\s*', ';', css_content)
            
            return css_content.strip()
        except Exception as e:
            logger.error(f"CSS minification failed: {e}")
            return css_content
    
    def minify_js(self, js_content: str) -> str:
        """Minifie basiquement le contenu JavaScript"""
        try:
            # Supprime les commentaires sur une ligne
            js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
            
            # Supprime les commentaires multilignes
            js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
            
            # Supprime les espaces superflus
            js_content = re.sub(r'\s+', ' ', js_content)
            js_content = re.sub(r';\s*', ';', js_content)
            js_content = re.sub(r'{\s*', '{', js_content)
            js_content = re.sub(r'}\s*', '}', js_content)
            
            return js_content.strip()
        except Exception as e:
            logger.error(f"JS minification failed: {e}")
            return js_content
    
    def generate_file_hash(self, file_path: str) -> str:
        """Génère un hash pour versioning des fichiers"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()[:8]
        except Exception as e:
            logger.error(f"Failed to generate hash for {file_path}: {e}")
            return "default"
    
    def compress_file(self, file_path: str) -> bool:
        """Compresse un fichier avec gzip"""
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                    f_out.writelines(f_in)
            return True
        except Exception as e:
            logger.error(f"Failed to compress {file_path}: {e}")
            return False
    
    def optimize_css_files(self) -> Dict[str, str]:
        """Optimise tous les fichiers CSS"""
        results = {}
        css_dir = os.path.join(self.static_folder, "css")
        
        if not os.path.exists(css_dir):
            logger.info("CSS directory not found, creating basic structure")
            os.makedirs(css_dir, exist_ok=True)
            return results
        
        for css_file in Path(css_dir).glob("*.css"):
            if css_file.name.endswith(".min.css"):
                continue
                
            try:
                with open(css_file, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                minified_content = self.minify_css(original_content)
                file_hash = hashlib.md5(minified_content.encode()).hexdigest()[:8]
                
                # Nom du fichier minifié avec hash
                min_filename = f"{css_file.stem}.{file_hash}.min.css"
                min_filepath = css_file.parent / min_filename
                
                with open(min_filepath, 'w', encoding='utf-8') as f:
                    f.write(minified_content)
                
                # Compression gzip
                self.compress_file(str(min_filepath))
                
                # Mise à jour du manifeste
                self.cache_manifest[str(css_file.name)] = min_filename
                
                results[css_file.name] = {
                    'original_size': len(original_content),
                    'minified_size': len(minified_content),
                    'compression_ratio': round((1 - len(minified_content) / len(original_content)) * 100, 2),
                    'minified_file': min_filename
                }
                
                logger.info(f"Optimized CSS: {css_file.name} -> {min_filename}")
                
            except Exception as e:
                logger.error(f"Failed to optimize CSS file {css_file}: {e}")
                results[css_file.name] = {'error': str(e)}
        
        return results
    
    def optimize_js_files(self) -> Dict[str, str]:
        """Optimise tous les fichiers JavaScript"""
        results = {}
        js_dir = os.path.join(self.static_folder, "js")
        
        if not os.path.exists(js_dir):
            logger.info("JS directory not found, creating basic structure")
            os.makedirs(js_dir, exist_ok=True)
            return results
        
        for js_file in Path(js_dir).glob("*.js"):
            if js_file.name.endswith(".min.js"):
                continue
                
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                minified_content = self.minify_js(original_content)
                file_hash = hashlib.md5(minified_content.encode()).hexdigest()[:8]
                
                # Nom du fichier minifié avec hash
                min_filename = f"{js_file.stem}.{file_hash}.min.js"
                min_filepath = js_file.parent / min_filename
                
                with open(min_filepath, 'w', encoding='utf-8') as f:
                    f.write(minified_content)
                
                # Compression gzip
                self.compress_file(str(min_filepath))
                
                # Mise à jour du manifeste
                self.cache_manifest[str(js_file.name)] = min_filename
                
                results[js_file.name] = {
                    'original_size': len(original_content),
                    'minified_size': len(minified_content),
                    'compression_ratio': round((1 - len(minified_content) / len(original_content)) * 100, 2),
                    'minified_file': min_filename
                }
                
                logger.info(f"Optimized JS: {js_file.name} -> {min_filename}")
                
            except Exception as e:
                logger.error(f"Failed to optimize JS file {js_file}: {e}")
                results[js_file.name] = {'error': str(e)}
        
        return results
    
    def generate_critical_css(self, html_content: str) -> str:
        """Génère le CSS critique pour le rendu above-the-fold"""
        try:
            # CSS de base critique pour NinjaLeads
            critical_css = """
            body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
            .navbar{background:#fff;box-shadow:0 2px 4px rgba(0,0,0,.1)}
            .container{max-width:1200px;margin:0 auto;padding:0 15px}
            .btn{padding:8px 16px;border:none;border-radius:4px;cursor:pointer}
            .btn-primary{background:#007bff;color:#fff}
            .hero{padding:60px 0;text-align:center}
            .card{background:#fff;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.1);margin-bottom:20px}
            """
            
            return critical_css.strip()
        except Exception as e:
            logger.error(f"Failed to generate critical CSS: {e}")
            return ""
    
    def optimize_all_assets(self) -> Dict[str, any]:
        """Optimise tous les assets statiques"""
        results = {
            'css_optimization': self.optimize_css_files(),
            'js_optimization': self.optimize_js_files(),
            'critical_css': self.generate_critical_css(""),
            'timestamp': os.path.getmtime(__file__) if os.path.exists(__file__) else 0
        }
        
        # Sauvegarde du manifeste
        self.save_cache_manifest()
        
        return results
    
    def get_asset_url(self, asset_name: str) -> str:
        """Retourne l'URL optimisée d'un asset"""
        if asset_name in self.cache_manifest:
            return f"/static/{self.cache_manifest[asset_name]}"
        return f"/static/{asset_name}"
    
    def get_optimization_stats(self) -> Dict[str, any]:
        """Retourne les statistiques d'optimisation"""
        return {
            'manifest_entries': len(self.cache_manifest),
            'static_folder': self.static_folder,
            'manifest': self.cache_manifest
        }

# Instance globale
asset_optimizer = AssetOptimizer()