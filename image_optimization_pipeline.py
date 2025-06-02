"""
Pipeline d'optimisation automatique des images
Compression, redimensionnement et conversion de formats
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageOps
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class ImageOptimizer:
    """Optimiseur d'images avec compression et redimensionnement automatiques"""
    
    def __init__(self, base_dir="static/optimized"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurations d'optimisation
        self.size_presets = {
            'thumbnail': (150, 150),
            'small': (300, 300),
            'medium': (600, 600),
            'large': (1200, 1200),
            'xl': (1920, 1920)
        }
        
        self.quality_settings = {
            'low': 60,
            'medium': 75,
            'high': 85,
            'max': 95
        }
        
        # Formats supportés
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        
    def calculate_image_hash(self, image_path: Path) -> str:
        """Calcule un hash unique pour une image"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    
    def optimize_image(self, 
                      input_path: Path, 
                      output_dir: Path = None,
                      sizes: List[str] = None,
                      quality: str = 'high',
                      format_output: str = 'webp') -> Dict:
        """
        Optimise une image en créant plusieurs variantes
        
        Args:
            input_path: Chemin de l'image source
            output_dir: Répertoire de sortie (optionnel)
            sizes: Liste des tailles à générer
            quality: Qualité de compression
            format_output: Format de sortie
            
        Returns:
            Dict contenant les chemins des images optimisées
        """
        if not input_path.exists() or input_path.suffix.lower() not in self.supported_formats:
            logger.error(f"Image non supportée: {input_path}")
            return {"success": False, "error": "Format non supporté"}
        
        try:
            # Ouvrir l'image
            with Image.open(input_path) as img:
                # Corriger l'orientation EXIF
                img = ImageOps.exif_transpose(img)
                
                # Convertir en RGB si nécessaire
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Générer hash pour le nom de fichier
                image_hash = self.calculate_image_hash(input_path)
                
                # Déterminer le répertoire de sortie
                if output_dir is None:
                    output_dir = self.base_dir / "images"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Tailles à générer
                if sizes is None:
                    sizes = ['thumbnail', 'small', 'medium', 'large']
                
                # Qualité de compression
                quality_value = self.quality_settings.get(quality, 85)
                
                results = {
                    "success": True,
                    "original": {
                        "path": str(input_path),
                        "size": img.size,
                        "format": img.format
                    },
                    "optimized": {},
                    "metadata": {
                        "hash": image_hash,
                        "generated_at": datetime.now().isoformat(),
                        "quality": quality,
                        "output_format": format_output
                    }
                }
                
                # Générer les variantes
                for size_name in sizes:
                    if size_name not in self.size_presets:
                        logger.warning(f"Taille inconnue: {size_name}")
                        continue
                    
                    target_size = self.size_presets[size_name]
                    
                    # Redimensionner en gardant les proportions
                    img_resized = img.copy()
                    img_resized.thumbnail(target_size, Image.Resampling.LANCZOS)
                    
                    # Nom du fichier optimisé
                    output_filename = f"{image_hash}_{size_name}.{format_output}"
                    output_path = output_dir / output_filename
                    
                    # Sauvegarder avec optimisation
                    save_kwargs = {'optimize': True, 'quality': quality_value}
                    if format_output.lower() == 'webp':
                        save_kwargs['method'] = 6  # Méthode de compression WebP
                    
                    img_resized.save(output_path, format=format_output.upper(), **save_kwargs)
                    
                    # Calculer le taux de compression
                    original_size = input_path.stat().st_size
                    optimized_size = output_path.stat().st_size
                    compression_ratio = (1 - optimized_size / original_size) * 100
                    
                    results["optimized"][size_name] = {
                        "path": str(output_path),
                        "url": f"/static/optimized/images/{output_filename}",
                        "size": img_resized.size,
                        "file_size": optimized_size,
                        "compression_ratio": round(compression_ratio, 2)
                    }
                
                return results
                
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de {input_path}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def optimize_directory(self, input_dir: Path, recursive: bool = True) -> Dict:
        """Optimise toutes les images d'un répertoire"""
        if not input_dir.exists():
            return {"success": False, "error": "Répertoire introuvable"}
        
        results = {
            "success": True,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        # Chercher les images
        pattern = "**/*" if recursive else "*"
        for image_path in input_dir.glob(pattern):
            if image_path.is_file() and image_path.suffix.lower() in self.supported_formats:
                result = self.optimize_image(image_path)
                
                if result.get("success"):
                    results["processed"] += 1
                else:
                    results["errors"] += 1
                
                results["details"].append({
                    "file": str(image_path),
                    "result": result
                })
            else:
                results["skipped"] += 1
        
        return results
    
    def create_responsive_html(self, image_variants: Dict, alt_text: str = "") -> str:
        """Génère du HTML responsive pour les images optimisées"""
        if not image_variants.get("optimized"):
            return f'<img src="{image_variants.get("original", {}).get("path", "")}" alt="{alt_text}">'
        
        optimized = image_variants["optimized"]
        
        # Source sets pour différentes résolutions
        srcset_parts = []
        for size_name, variant in optimized.items():
            width = variant["size"][0]
            srcset_parts.append(f"{variant['url']} {width}w")
        
        srcset = ", ".join(srcset_parts)
        
        # Image par défaut (medium ou la première disponible)
        default_src = optimized.get("medium", {}).get("url") or list(optimized.values())[0]["url"]
        
        # Sizes attribute pour un design responsive
        sizes = "(max-width: 300px) 300px, (max-width: 600px) 600px, (max-width: 1200px) 1200px, 1920px"
        
        return f'''<img 
            src="{default_src}" 
            srcset="{srcset}" 
            sizes="{sizes}" 
            alt="{alt_text}"
            loading="lazy"
            style="width: 100%; height: auto; max-width: 100%;"
        >'''
    
    def get_optimization_stats(self) -> Dict:
        """Retourne les statistiques d'optimisation"""
        if not self.base_dir.exists():
            return {"total_files": 0, "total_size": 0}
        
        total_files = 0
        total_size = 0
        
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_path": str(self.base_dir)
        }
    
    def cleanup_old_optimized(self, days_old: int = 30) -> int:
        """Nettoie les images optimisées anciennes"""
        if not self.base_dir.exists():
            return 0
        
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Erreur suppression {file_path}: {str(e)}")
        
        return deleted_count

# Instance globale
image_optimizer = ImageOptimizer()