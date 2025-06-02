"""
Gestionnaire de stockage persistant pour les images générées par IA
Combine base de données, cache Redis et stockage fichier pour une gestion robuste
"""

import os
import hashlib
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse
import uuid

from redis_cache_manager import cache_manager

logger = logging.getLogger(__name__)

class ImageStorageManager:
    """Gestionnaire centralisé pour le stockage d'images IA"""
    
    def __init__(self, storage_dir="generated_images"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Créer les sous-dossiers par type
        self.avatar_dir = self.storage_dir / "avatars"
        self.campaign_dir = self.storage_dir / "campaigns" 
        self.product_dir = self.storage_dir / "products"
        
        for dir_path in [self.avatar_dir, self.campaign_dir, self.product_dir]:
            dir_path.mkdir(exist_ok=True)
            
    def generate_image_hash(self, prompt: str, model: str, size: str = "1024x1024") -> str:
        """Génère un hash unique pour une combinaison prompt/modèle/taille"""
        content = f"{prompt}:{model}:{size}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def download_and_store_image(self, 
                                url: str, 
                                prompt: str,
                                model: str,
                                image_type: str = "general",
                                user_id: int = None,
                                entity_id: int = None,
                                size: str = "1024x1024") -> Optional[Dict]:
        """
        Télécharge une image depuis une URL et la stocke localement
        
        Args:
            url: URL de l'image à télécharger
            prompt: Prompt utilisé pour générer l'image
            model: Modèle IA utilisé
            image_type: Type d'image (avatar, campaign, product)
            user_id: ID utilisateur propriétaire
            entity_id: ID de l'entité associée (campaign_id, customer_id, etc.)
            size: Taille de l'image
            
        Returns:
            Dict contenant les informations de l'image stockée
        """
        try:
            # Vérifier si l'image existe déjà en cache
            image_hash = self.generate_image_hash(prompt, model, size)
            cached_image = self.get_cached_image(image_hash)
            if cached_image:
                logger.info(f"Image trouvée en cache: {image_hash}")
                return cached_image
            
            # Télécharger l'image
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Déterminer l'extension du fichier
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                extension = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                extension = '.jpg'
            elif 'webp' in content_type:
                extension = '.webp'
            else:
                extension = '.png'  # Par défaut
            
            # Générer le nom de fichier unique
            filename = f"{image_hash}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
            
            # Déterminer le répertoire de stockage
            if image_type == "avatar":
                storage_path = self.avatar_dir / filename
            elif image_type == "campaign":
                storage_path = self.campaign_dir / filename
            elif image_type == "product":
                storage_path = self.product_dir / filename
            else:
                storage_path = self.storage_dir / filename
            
            # Sauvegarder le fichier
            with open(storage_path, 'wb') as f:
                f.write(response.content)
            
            # Créer l'entrée en base de données
            stored_image = StoredImage(
                hash=image_hash,
                original_url=url,
                local_path=str(storage_path),
                filename=filename,
                prompt=prompt,
                model=model,
                size=size,
                image_type=image_type,
                user_id=user_id,
                entity_id=entity_id,
                file_size=len(response.content),
                content_type=content_type
            )
            
            db.session.add(stored_image)
            db.session.commit()
            
            # Mettre en cache
            image_data = stored_image.to_dict()
            self.cache_image(image_hash, image_data)
            
            logger.info(f"Image stockée avec succès: {filename} ({len(response.content)} bytes)")
            return image_data
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage de l'image: {str(e)}")
            return None
    
    def get_cached_image(self, image_hash: str) -> Optional[Dict]:
        """Récupère une image depuis le cache Redis"""
        cache_key = f"stored_image:{image_hash}"
        return cache_manager.get(cache_key)
    
    def cache_image(self, image_hash: str, image_data: Dict, ttl: int = 86400) -> bool:
        """Met en cache les données d'une image"""
        cache_key = f"stored_image:{image_hash}"
        return cache_manager.set(cache_key, image_data, ttl)
    
    def get_image_by_hash(self, image_hash: str) -> Optional[Dict]:
        """Récupère une image par son hash (cache + DB)"""
        # Essayer le cache d'abord
        cached = self.get_cached_image(image_hash)
        if cached:
            return cached
        
        # Sinon, chercher en base
        stored_image = StoredImage.query.filter_by(hash=image_hash).first()
        if stored_image:
            image_data = stored_image.to_dict()
            self.cache_image(image_hash, image_data)
            return image_data
        
        return None
    
    def get_user_images(self, user_id: int, image_type: str = None, limit: int = 50) -> List[Dict]:
        """Récupère les images d'un utilisateur"""
        query = StoredImage.query.filter_by(user_id=user_id)
        
        if image_type:
            query = query.filter_by(image_type=image_type)
        
        images = query.order_by(StoredImage.created_at.desc()).limit(limit).all()
        return [img.to_dict() for img in images]
    
    def cleanup_old_images(self, days_old: int = 30) -> int:
        """Nettoie les images anciennes non utilisées"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        old_images = StoredImage.query.filter(
            StoredImage.created_at < cutoff_date,
            StoredImage.is_permanent == False
        ).all()
        
        deleted_count = 0
        for image in old_images:
            try:
                # Supprimer le fichier
                file_path = Path(image.local_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Supprimer de la base
                db.session.delete(image)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de l'image {image.filename}: {str(e)}")
        
        if deleted_count > 0:
            db.session.commit()
            logger.info(f"{deleted_count} images anciennes supprimées")
        
        return deleted_count
    
    def mark_as_permanent(self, image_hash: str) -> bool:
        """Marque une image comme permanente (ne sera pas supprimée)"""
        stored_image = StoredImage.query.filter_by(hash=image_hash).first()
        if stored_image:
            stored_image.is_permanent = True
            db.session.commit()
            return True
        return False
    
    def get_storage_stats(self) -> Dict:
        """Retourne les statistiques de stockage"""
        total_images = StoredImage.query.count()
        total_size = db.session.query(db.func.sum(StoredImage.file_size)).scalar() or 0
        
        # Statistiques par type
        type_stats = db.session.query(
            StoredImage.image_type,
            db.func.count(StoredImage.id),
            db.func.sum(StoredImage.file_size)
        ).group_by(StoredImage.image_type).all()
        
        # Statistiques par modèle IA
        model_stats = db.session.query(
            StoredImage.model,
            db.func.count(StoredImage.id)
        ).group_by(StoredImage.model).all()
        
        return {
            "total_images": total_images,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": {stat[0]: {"count": stat[1], "size_bytes": stat[2] or 0} for stat in type_stats},
            "by_model": {stat[0]: stat[1] for stat in model_stats},
            "storage_directory": str(self.storage_dir)
        }

# Instance globale du gestionnaire
image_storage = ImageStorageManager()