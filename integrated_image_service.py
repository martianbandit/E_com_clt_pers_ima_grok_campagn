"""
Service intégré pour la génération et le stockage persistant des images IA
Combine ai_utils et image_storage_manager pour une gestion complète
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from ai_utils import AIManager
from flask import current_app

logger = logging.getLogger(__name__)

class IntegratedImageService:
    """Service complet pour génération et stockage d'images IA"""
    
    def __init__(self):
        self.ai_manager = AIManager()
        self._storage_manager = None
    
    @property
    def storage_manager(self):
        """Lazy loading du storage manager pour éviter les imports circulaires"""
        if self._storage_manager is None:
            from image_storage_manager import image_storage
            self._storage_manager = image_storage
        return self._storage_manager
    
    def generate_and_store_image(self, 
                               prompt: str,
                               image_type: str = "general",
                               user_id: str = None,
                               entity_id: int = None,
                               model: str = "dall-e-3",
                               size: str = "1024x1024") -> Dict[str, Any]:
        """
        Génère une image avec l'IA et la stocke de manière persistante
        
        Args:
            prompt: Description de l'image à générer
            image_type: Type d'image (avatar, campaign, product, general)
            user_id: ID de l'utilisateur
            entity_id: ID de l'entité associée (optionnel)
            model: Modèle IA à utiliser
            size: Taille de l'image
            
        Returns:
            Dict contenant les informations de l'image générée et stockée
        """
        try:
            # Vérifier si l'image existe déjà en cache
            image_hash = self.storage_manager.generate_image_hash(prompt, model, size)
            cached_image = self.storage_manager.get_image_by_hash(image_hash)
            
            if cached_image:
                logger.info(f"Image trouvée en cache pour le prompt: {prompt[:50]}...")
                return {
                    "success": True,
                    "from_cache": True,
                    "image_data": cached_image,
                    "local_url": f"/images/{cached_image['filename']}",
                    "prompt": prompt
                }
            
            # Générer l'image avec l'IA
            logger.info(f"Génération d'une nouvelle image: {image_type}")
            image_url = self.ai_manager.generate_image(
                prompt=prompt,
                model=model,
                size=size,
                metric_name=f"integrated_image_generation_{image_type}"
            )
            
            if not image_url:
                return {
                    "success": False,
                    "error": "Échec de la génération d'image par l'IA",
                    "prompt": prompt
                }
            
            # Stocker l'image localement
            stored_image = self.storage_manager.download_and_store_image(
                url=image_url,
                prompt=prompt,
                model=model,
                image_type=image_type,
                user_id=user_id,
                entity_id=entity_id,
                size=size
            )
            
            if not stored_image:
                return {
                    "success": False,
                    "error": "Échec du stockage de l'image",
                    "original_url": image_url,
                    "prompt": prompt
                }
            
            return {
                "success": True,
                "from_cache": False,
                "image_data": stored_image,
                "local_url": f"/images/{stored_image['filename']}",
                "original_url": image_url,
                "prompt": prompt
            }
            
        except Exception as e:
            logger.error(f"Erreur dans generate_and_store_image: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt
            }
    
    def get_user_image_gallery(self, user_id: str, image_type: str = None, limit: int = 20) -> Dict[str, Any]:
        """
        Récupère la galerie d'images d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            image_type: Type d'images à filtrer (optionnel)
            limit: Nombre maximum d'images à retourner
            
        Returns:
            Dict contenant les images et métadonnées
        """
        try:
            images = self.storage_manager.get_user_images(user_id, image_type, limit)
            
            # Enrichir avec des URLs locales
            for image in images:
                image['local_url'] = f"/images/{image['filename']}"
            
            return {
                "success": True,
                "images": images,
                "total_count": len(images),
                "image_type": image_type or "all"
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la galerie: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "images": []
            }
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de stockage d'images"""
        try:
            return {
                "success": True,
                "stats": self.storage_manager.get_storage_stats()
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_images(self, days_old: int = 30) -> Dict[str, Any]:
        """Nettoie les images anciennes"""
        try:
            deleted_count = self.storage_manager.cleanup_old_images(days_old)
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"{deleted_count} images anciennes supprimées"
            }
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Instance globale du service
integrated_image_service = IntegratedImageService()