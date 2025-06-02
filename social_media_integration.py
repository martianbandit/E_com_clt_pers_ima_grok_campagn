"""
Intégration réseaux sociaux pour publication automatisée
Facebook, Instagram, LinkedIn, Twitter
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class SocialMediaManager:
    """Gestionnaire des publications sur réseaux sociaux"""
    
    def __init__(self):
        # Configuration Facebook/Instagram
        self.facebook_access_token = os.environ.get('FACEBOOK_ACCESS_TOKEN')
        self.facebook_page_id = os.environ.get('FACEBOOK_PAGE_ID')
        self.instagram_account_id = os.environ.get('INSTAGRAM_ACCOUNT_ID')
        
        # Configuration LinkedIn
        self.linkedin_access_token = os.environ.get('LINKEDIN_ACCESS_TOKEN')
        self.linkedin_person_id = os.environ.get('LINKEDIN_PERSON_ID')
        
        # Configuration Twitter
        self.twitter_bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        self.twitter_api_key = os.environ.get('TWITTER_API_KEY')
        self.twitter_api_secret = os.environ.get('TWITTER_API_SECRET')
        self.twitter_access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        self.enabled_platforms = []
        
        if self.facebook_access_token and self.facebook_page_id:
            self.enabled_platforms.append('facebook')
        
        if self.instagram_account_id:
            self.enabled_platforms.append('instagram')
            
        if self.linkedin_access_token:
            self.enabled_platforms.append('linkedin')
            
        if self.twitter_bearer_token:
            self.enabled_platforms.append('twitter')
        
        logger.info(f"Réseaux sociaux configurés: {', '.join(self.enabled_platforms)}")
    
    def publish_to_facebook(self, 
                           message: str,
                           image_url: str = None,
                           link: str = None) -> Optional[str]:
        """Publier sur Facebook"""
        if 'facebook' not in self.enabled_platforms:
            logger.warning("Facebook non configuré")
            return None
        
        try:
            url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/posts"
            
            params = {
                'message': message,
                'access_token': self.facebook_access_token
            }
            
            if link:
                params['link'] = link
            
            if image_url:
                # Pour les images, utiliser l'endpoint photos
                url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/photos"
                params['url'] = image_url
                params['caption'] = message
                del params['message']
            
            response = requests.post(url, data=params)
            
            if response.status_code == 200:
                post_data = response.json()
                logger.info(f"Publication Facebook réussie: {post_data.get('id')}")
                return post_data.get('id')
            else:
                logger.error(f"Erreur publication Facebook: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception publication Facebook: {str(e)}")
            return None
    
    def publish_to_instagram(self, 
                            image_url: str,
                            caption: str) -> Optional[str]:
        """Publier sur Instagram"""
        if 'instagram' not in self.enabled_platforms:
            logger.warning("Instagram non configuré")
            return None
        
        try:
            # Étape 1: Créer le conteneur média
            create_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media"
            
            create_params = {
                'image_url': image_url,
                'caption': caption,
                'access_token': self.facebook_access_token
            }
            
            create_response = requests.post(create_url, data=create_params)
            
            if create_response.status_code != 200:
                logger.error(f"Erreur création média Instagram: {create_response.text}")
                return None
            
            container_id = create_response.json().get('id')
            
            # Étape 2: Publier le conteneur
            publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media_publish"
            
            publish_params = {
                'creation_id': container_id,
                'access_token': self.facebook_access_token
            }
            
            publish_response = requests.post(publish_url, data=publish_params)
            
            if publish_response.status_code == 200:
                post_data = publish_response.json()
                logger.info(f"Publication Instagram réussie: {post_data.get('id')}")
                return post_data.get('id')
            else:
                logger.error(f"Erreur publication Instagram: {publish_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception publication Instagram: {str(e)}")
            return None
    
    def publish_to_linkedin(self, 
                           text: str,
                           image_url: str = None,
                           article_url: str = None) -> Optional[str]:
        """Publier sur LinkedIn"""
        if 'linkedin' not in self.enabled_platforms:
            logger.warning("LinkedIn non configuré")
            return None
        
        try:
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            headers = {
                'Authorization': f'Bearer {self.linkedin_access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            post_data = {
                "author": f"urn:li:person:{self.linkedin_person_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Ajouter un article/lien si fourni
            if article_url:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "originalUrl": article_url
                }]
            
            response = requests.post(url, headers=headers, json=post_data)
            
            if response.status_code == 201:
                post_id = response.headers.get('x-restli-id')
                logger.info(f"Publication LinkedIn réussie: {post_id}")
                return post_id
            else:
                logger.error(f"Erreur publication LinkedIn: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception publication LinkedIn: {str(e)}")
            return None
    
    def publish_to_twitter(self, text: str, image_url: str = None) -> Optional[str]:
        """Publier sur Twitter (X)"""
        if 'twitter' not in self.enabled_platforms:
            logger.warning("Twitter non configuré")
            return None
        
        try:
            # Twitter API v2
            url = "https://api.twitter.com/2/tweets"
            
            headers = {
                'Authorization': f'Bearer {self.twitter_bearer_token}',
                'Content-Type': 'application/json'
            }
            
            tweet_data = {
                "text": text
            }
            
            # Pour les images, il faudrait d'abord les uploader
            # Ce qui nécessite une implémentation plus complexe avec OAuth 1.0a
            
            response = requests.post(url, headers=headers, json=tweet_data)
            
            if response.status_code == 201:
                tweet_data = response.json()
                logger.info(f"Publication Twitter réussie: {tweet_data['data']['id']}")
                return tweet_data['data']['id']
            else:
                logger.error(f"Erreur publication Twitter: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception publication Twitter: {str(e)}")
            return None
    
    def schedule_post(self, 
                     platforms: List[str],
                     content: Dict[str, Any],
                     publish_time: datetime = None) -> Dict[str, Any]:
        """Programmer une publication sur plusieurs plateformes"""
        results = {}
        
        for platform in platforms:
            if platform not in self.enabled_platforms:
                results[platform] = {
                    'success': False,
                    'error': 'Plateforme non configurée'
                }
                continue
            
            try:
                if platform == 'facebook':
                    post_id = self.publish_to_facebook(
                        content.get('text', ''),
                        content.get('image_url'),
                        content.get('link')
                    )
                elif platform == 'instagram':
                    if not content.get('image_url'):
                        results[platform] = {
                            'success': False,
                            'error': 'Image requise pour Instagram'
                        }
                        continue
                    post_id = self.publish_to_instagram(
                        content['image_url'],
                        content.get('text', '')
                    )
                elif platform == 'linkedin':
                    post_id = self.publish_to_linkedin(
                        content.get('text', ''),
                        content.get('image_url'),
                        content.get('link')
                    )
                elif platform == 'twitter':
                    post_id = self.publish_to_twitter(
                        content.get('text', ''),
                        content.get('image_url')
                    )
                else:
                    post_id = None
                
                results[platform] = {
                    'success': post_id is not None,
                    'post_id': post_id,
                    'published_at': datetime.now().isoformat()
                }
                
            except Exception as e:
                results[platform] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def get_post_analytics(self, platform: str, post_id: str) -> Optional[Dict]:
        """Récupérer les analytics d'une publication"""
        if platform not in self.enabled_platforms:
            return None
        
        try:
            if platform == 'facebook':
                url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
                params = {
                    'metric': 'post_impressions,post_engaged_users,post_clicks',
                    'access_token': self.facebook_access_token
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
            
            elif platform == 'linkedin':
                # LinkedIn analytics nécessitent des permissions spéciales
                pass
            
            elif platform == 'twitter':
                # Twitter analytics via API v2
                pass
                
        except Exception as e:
            logger.error(f"Erreur récupération analytics {platform}: {str(e)}")
        
        return None
    
    def create_campaign_content(self, campaign_data: Dict) -> Dict[str, str]:
        """Adapter le contenu d'une campagne pour chaque plateforme"""
        base_text = campaign_data.get('content', '')
        title = campaign_data.get('title', '')
        
        # Adapter le contenu selon les plateformes
        content_variations = {
            'facebook': {
                'text': f"{title}\n\n{base_text}",
                'max_length': 63206
            },
            'instagram': {
                'text': f"{title}\n\n{base_text[:2000]}...",  # Limite Instagram
                'max_length': 2200
            },
            'linkedin': {
                'text': f"{title}\n\n{base_text}",
                'max_length': 3000
            },
            'twitter': {
                'text': f"{title}\n\n{base_text[:200]}...",  # Limite Twitter
                'max_length': 280
            }
        }
        
        # Tronquer si nécessaire
        for platform, content in content_variations.items():
            if len(content['text']) > content['max_length']:
                content['text'] = content['text'][:content['max_length']-3] + '...'
        
        return {platform: data['text'] for platform, data in content_variations.items()}

# Instance globale
social_media = SocialMediaManager()

# Templates de contenu par plateforme
SOCIAL_TEMPLATES = {
    'product_launch': {
        'facebook': "🚀 Nouveau produit disponible !\n\n{description}\n\n👉 Découvrez-le maintenant : {link}",
        'instagram': "🚀 Nouveau produit !\n\n{description}\n\n#nouveauté #innovation #marketing",
        'linkedin': "Nous sommes fiers de vous présenter notre dernier produit :\n\n{description}\n\nPlus d'informations : {link}",
        'twitter': "🚀 Nouveau produit disponible !\n\n{description}\n\n{link}"
    },
    'blog_post': {
        'facebook': "📖 Nouvel article de blog :\n\n{title}\n\n{excerpt}\n\nLire l'article complet : {link}",
        'instagram': "📖 Nouvel article !\n\n{title}\n\n#blog #marketing #conseils",
        'linkedin': "Nouvel article sur notre blog :\n\n{title}\n\n{excerpt}\n\nLire la suite : {link}",
        'twitter': "📖 {title}\n\n{link}"
    },
    'promotion': {
        'facebook': "🎉 Offre spéciale !\n\n{offer_details}\n\n⏰ Jusqu'au {end_date}\n\n{link}",
        'instagram': "🎉 Offre spéciale !\n\n{offer_details}\n\n#promo #offre #limitée",
        'linkedin': "Offre promotionnelle :\n\n{offer_details}\n\nValable jusqu'au {end_date}\n\n{link}",
        'twitter': "🎉 {offer_details}\n\nJusqu'au {end_date} : {link}"
    }
}