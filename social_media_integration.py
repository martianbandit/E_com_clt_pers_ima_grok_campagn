"""
Intégration complète des réseaux sociaux pour NinjaLead.ai
Gestion des publications automatiques sur Facebook, Instagram, LinkedIn, Twitter
"""

import os
import requests
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from models import User, Campaign, SocialMediaAccount, SocialMediaPost
import hashlib
import hmac

logger = logging.getLogger(__name__)

# Blueprint pour les réseaux sociaux
social_bp = Blueprint('social_media', __name__, url_prefix='/social')

# Configuration des APIs
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
INSTAGRAM_CLIENT_ID = os.environ.get('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.environ.get('INSTAGRAM_CLIENT_SECRET')
LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET')
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')

class SocialMediaManager:
    """Gestionnaire centralisé pour les intégrations réseaux sociaux"""
    
    def __init__(self):
        self.platforms = {
            'facebook': {
                'name': 'Facebook',
                'auth_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'api_base': 'https://graph.facebook.com/v18.0',
                'available': bool(FACEBOOK_APP_ID and FACEBOOK_APP_SECRET)
            },
            'instagram': {
                'name': 'Instagram Business',
                'auth_url': 'https://api.instagram.com/oauth/authorize',
                'token_url': 'https://api.instagram.com/oauth/access_token',
                'api_base': 'https://graph.instagram.com',
                'available': bool(INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET)
            },
            'linkedin': {
                'name': 'LinkedIn',
                'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'api_base': 'https://api.linkedin.com/v2',
                'available': bool(LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET)
            },
            'twitter': {
                'name': 'Twitter/X',
                'auth_url': 'https://api.twitter.com/2/oauth2/authorize',
                'token_url': 'https://api.twitter.com/2/oauth2/token',
                'api_base': 'https://api.twitter.com/2',
                'available': bool(TWITTER_API_KEY and TWITTER_API_SECRET)
            }
        }
    
    def get_auth_url(self, platform, redirect_uri):
        """
        Génère l'URL d'authentification pour un réseau social
        
        Args:
            platform: Nom de la plateforme (facebook, instagram, etc.)
            redirect_uri: URL de retour après authentification
            
        Returns:
            str: URL d'authentification
        """
        if platform not in self.platforms:
            return None
        
        platform_config = self.platforms[platform]
        if not platform_config['available']:
            return None
        
        # Générer un state unique pour la sécurité
        state = hashlib.sha256(f"{current_user.id}{platform}{datetime.utcnow()}".encode()).hexdigest()
        session[f'oauth_state_{platform}'] = state
        
        if platform == 'facebook':
            params = {
                'client_id': FACEBOOK_APP_ID,
                'redirect_uri': redirect_uri,
                'scope': 'pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish',
                'response_type': 'code',
                'state': state
            }
        elif platform == 'instagram':
            params = {
                'client_id': INSTAGRAM_CLIENT_ID,
                'redirect_uri': redirect_uri,
                'scope': 'user_profile,user_media',
                'response_type': 'code',
                'state': state
            }
        elif platform == 'linkedin':
            params = {
                'client_id': LINKEDIN_CLIENT_ID,
                'redirect_uri': redirect_uri,
                'scope': 'w_member_social,r_basicprofile',
                'response_type': 'code',
                'state': state
            }
        elif platform == 'twitter':
            params = {
                'client_id': TWITTER_API_KEY,
                'redirect_uri': redirect_uri,
                'scope': 'tweet.read tweet.write users.read',
                'response_type': 'code',
                'state': state,
                'code_challenge_method': 'plain',
                'code_challenge': state
            }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{platform_config['auth_url']}?{query_string}"
    
    def exchange_code_for_token(self, platform, code, redirect_uri):
        """
        Échange le code d'autorisation contre un token d'accès
        
        Args:
            platform: Nom de la plateforme
            code: Code d'autorisation reçu
            redirect_uri: URL de retour
            
        Returns:
            dict: Token d'accès et informations utilisateur
        """
        if platform not in self.platforms:
            return {'success': False, 'error': 'Plateforme non supportée'}
        
        platform_config = self.platforms[platform]
        
        try:
            if platform == 'facebook':
                response = requests.post(platform_config['token_url'], {
                    'client_id': FACEBOOK_APP_ID,
                    'client_secret': FACEBOOK_APP_SECRET,
                    'redirect_uri': redirect_uri,
                    'code': code
                })
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data['access_token']
                    
                    # Récupérer les informations utilisateur
                    user_response = requests.get(f"{platform_config['api_base']}/me", {
                        'access_token': access_token,
                        'fields': 'id,name,email'
                    })
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        return {
                            'success': True,
                            'access_token': access_token,
                            'user_data': user_data,
                            'expires_in': token_data.get('expires_in')
                        }
            
            elif platform == 'linkedin':
                response = requests.post(platform_config['token_url'], {
                    'grant_type': 'authorization_code',
                    'client_id': LINKEDIN_CLIENT_ID,
                    'client_secret': LINKEDIN_CLIENT_SECRET,
                    'redirect_uri': redirect_uri,
                    'code': code
                }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data['access_token']
                    
                    # Récupérer les informations utilisateur
                    user_response = requests.get(f"{platform_config['api_base']}/people/~", {
                        'oauth2_access_token': access_token
                    })
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        return {
                            'success': True,
                            'access_token': access_token,
                            'user_data': user_data,
                            'expires_in': token_data.get('expires_in')
                        }
            
            return {'success': False, 'error': 'Erreur lors de l\'échange du token'}
            
        except Exception as e:
            logger.error(f"Erreur échange token {platform}: {e}")
            return {'success': False, 'error': str(e)}
    
    def save_social_account(self, platform, token_data, user_data):
        """
        Sauvegarde un compte réseau social en base de données
        
        Args:
            platform: Nom de la plateforme
            token_data: Données du token
            user_data: Données utilisateur
            
        Returns:
            bool: Succès de la sauvegarde
        """
        try:
            # Vérifier si le compte existe déjà
            existing_account = SocialMediaAccount.query.filter_by(
                user_id=current_user.id,
                platform=platform,
                platform_user_id=user_data['id']
            ).first()
            
            if existing_account:
                # Mettre à jour le token
                existing_account.access_token = token_data['access_token']
                existing_account.expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                existing_account.updated_at = datetime.utcnow()
            else:
                # Créer un nouveau compte
                new_account = SocialMediaAccount(
                    user_id=current_user.id,
                    platform=platform,
                    platform_user_id=user_data['id'],
                    username=user_data.get('name', user_data.get('username', '')),
                    access_token=token_data['access_token'],
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600)),
                    created_at=datetime.utcnow()
                )
                db.session.add(new_account)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde compte {platform}: {e}")
            db.session.rollback()
            return False
    
    def publish_post(self, platform, account_id, content, image_url=None):
        """
        Publie un post sur un réseau social
        
        Args:
            platform: Nom de la plateforme
            account_id: ID du compte en base
            content: Contenu du post
            image_url: URL de l'image (optionnel)
            
        Returns:
            dict: Résultat de la publication
        """
        # Récupérer le compte
        account = SocialMediaAccount.query.get(account_id)
        if not account or account.user_id != current_user.id:
            return {'success': False, 'error': 'Compte non trouvé'}
        
        # Vérifier l'expiration du token
        if account.expires_at and account.expires_at < datetime.utcnow():
            return {'success': False, 'error': 'Token expiré - Reconnectez-vous'}
        
        try:
            if platform == 'facebook':
                # Publication sur Facebook
                post_data = {
                    'message': content,
                    'access_token': account.access_token
                }
                
                if image_url:
                    post_data['link'] = image_url
                
                response = requests.post(
                    f"https://graph.facebook.com/v18.0/me/feed",
                    data=post_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Enregistrer le post en base
                    social_post = SocialMediaPost(
                        account_id=account_id,
                        platform=platform,
                        content=content,
                        image_url=image_url,
                        platform_post_id=result['id'],
                        status='published',
                        published_at=datetime.utcnow()
                    )
                    db.session.add(social_post)
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'post_id': result['id'],
                        'platform': platform
                    }
            
            elif platform == 'linkedin':
                # Publication sur LinkedIn
                post_data = {
                    'author': f'urn:li:person:{account.platform_user_id}',
                    'lifecycleState': 'PUBLISHED',
                    'specificContent': {
                        'com.linkedin.ugc.ShareContent': {
                            'shareCommentary': {
                                'text': content
                            },
                            'shareMediaCategory': 'NONE'
                        }
                    },
                    'visibility': {
                        'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
                    }
                }
                
                if image_url:
                    post_data['specificContent']['com.linkedin.ugc.ShareContent']['shareMediaCategory'] = 'IMAGE'
                    post_data['specificContent']['com.linkedin.ugc.ShareContent']['media'] = [
                        {
                            'status': 'READY',
                            'description': {
                                'text': content
                            },
                            'media': image_url
                        }
                    ]
                
                response = requests.post(
                    'https://api.linkedin.com/v2/ugcPosts',
                    headers={
                        'Authorization': f'Bearer {account.access_token}',
                        'Content-Type': 'application/json'
                    },
                    json=post_data
                )
                
                if response.status_code == 201:
                    result = response.json()
                    
                    social_post = SocialMediaPost(
                        account_id=account_id,
                        platform=platform,
                        content=content,
                        image_url=image_url,
                        platform_post_id=result['id'],
                        status='published',
                        published_at=datetime.utcnow()
                    )
                    db.session.add(social_post)
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'post_id': result['id'],
                        'platform': platform
                    }
            
            return {'success': False, 'error': f'Publication non implémentée pour {platform}'}
            
        except Exception as e:
            logger.error(f"Erreur publication {platform}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_accounts(self, user_id):
        """Récupère tous les comptes sociaux d'un utilisateur"""
        return SocialMediaAccount.query.filter_by(user_id=user_id).all()
    
    def disconnect_account(self, account_id):
        """Déconnecte un compte réseau social"""
        try:
            account = SocialMediaAccount.query.get(account_id)
            if account and account.user_id == current_user.id:
                db.session.delete(account)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur déconnexion compte: {e}")
            db.session.rollback()
            return False

# Instance globale du gestionnaire
social_manager = SocialMediaManager()

@social_bp.route('/')
@login_required
def dashboard():
    """Dashboard des réseaux sociaux"""
    user_accounts = social_manager.get_user_accounts(current_user.id)
    available_platforms = {k: v for k, v in social_manager.platforms.items() if v['available']}
    
    return render_template('social/dashboard.html', 
                         user_accounts=user_accounts,
                         available_platforms=available_platforms)

@social_bp.route('/connect/<platform>')
@login_required
def connect_platform(platform):
    """Initie la connexion à un réseau social"""
    redirect_uri = url_for('social_media.callback', platform=platform, _external=True)
    auth_url = social_manager.get_auth_url(platform, redirect_uri)
    
    if auth_url:
        return redirect(auth_url)
    else:
        flash(f'Connexion à {platform} non disponible - Configuration manquante', 'danger')
        return redirect(url_for('social_media.dashboard'))

@social_bp.route('/callback/<platform>')
@login_required
def callback(platform):
    """Callback après authentification"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Vérifier le state pour la sécurité
    expected_state = session.get(f'oauth_state_{platform}')
    if not state or state != expected_state:
        flash('Erreur de sécurité lors de la connexion', 'danger')
        return redirect(url_for('social_media.dashboard'))
    
    if code:
        redirect_uri = url_for('social_media.callback', platform=platform, _external=True)
        result = social_manager.exchange_code_for_token(platform, code, redirect_uri)
        
        if result['success']:
            # Sauvegarder le compte
            if social_manager.save_social_account(platform, result, result['user_data']):
                flash(f'Compte {platform} connecté avec succès', 'success')
            else:
                flash('Erreur lors de la sauvegarde du compte', 'danger')
        else:
            flash(f'Erreur de connexion: {result["error"]}', 'danger')
    else:
        flash('Connexion annulée', 'info')
    
    return redirect(url_for('social_media.dashboard'))

@social_bp.route('/publish', methods=['POST'])
@login_required
def publish():
    """Publie un post sur les réseaux sociaux sélectionnés"""
    content = request.form.get('content')
    image_url = request.form.get('image_url')
    selected_accounts = request.form.getlist('accounts')
    
    if not content:
        return jsonify({'success': False, 'error': 'Contenu requis'}), 400
    
    results = []
    
    for account_id in selected_accounts:
        account = SocialMediaAccount.query.get(account_id)
        if account and account.user_id == current_user.id:
            result = social_manager.publish_post(
                account.platform, 
                account_id, 
                content, 
                image_url
            )
            results.append({
                'platform': account.platform,
                'result': result
            })
    
    return jsonify({
        'success': True,
        'results': results
    })

@social_bp.route('/disconnect/<int:account_id>', methods=['POST'])
@login_required
def disconnect(account_id):
    """Déconnecte un compte réseau social"""
    if social_manager.disconnect_account(account_id):
        flash('Compte déconnecté avec succès', 'success')
    else:
        flash('Erreur lors de la déconnexion', 'danger')
    
    return redirect(url_for('social_media.dashboard'))

@social_bp.route('/api/accounts')
@login_required
def api_accounts():
    """API pour récupérer les comptes connectés"""
    accounts = social_manager.get_user_accounts(current_user.id)
    return jsonify([{
        'id': account.id,
        'platform': account.platform,
        'username': account.username,
        'connected_at': account.created_at.isoformat(),
        'expires_at': account.expires_at.isoformat() if account.expires_at else None
    } for account in accounts])

def init_social_media_integration(app):
    """Initialise l'intégration des réseaux sociaux"""
    app.register_blueprint(social_bp)
    
    # Vérifier les configurations
    missing_configs = []
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        missing_configs.append('Facebook')
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        missing_configs.append('LinkedIn')
    
    if missing_configs:
        logger.warning(f"Configurations manquantes pour: {', '.join(missing_configs)}")
    
    logger.info("Intégration réseaux sociaux initialisée")
    return social_manager