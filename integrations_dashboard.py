"""
Tableau de bord unifié pour gérer toutes les intégrations
Configuration et monitoring des services externes
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

class IntegrationsDashboard:
    """Gestionnaire du tableau de bord des intégrations"""
    
    def __init__(self):
        self.integrations = {
            'stripe': {
                'name': 'Stripe',
                'description': 'Paiements et abonnements',
                'required_keys': ['STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY'],
                'optional_keys': ['STRIPE_WEBHOOK_SECRET'],
                'status': 'not_configured',
                'features': ['Paiements', 'Abonnements', 'Webhooks', 'Portail client']
            },
            'sendgrid': {
                'name': 'SendGrid',
                'description': 'Email marketing',
                'required_keys': ['SENDGRID_API_KEY'],
                'optional_keys': ['FROM_EMAIL', 'FROM_NAME'],
                'status': 'not_configured',
                'features': ['Emails transactionnels', 'Campagnes', 'Listes de contacts', 'Analytics']
            },
            'facebook': {
                'name': 'Facebook/Instagram',
                'description': 'Publication sur réseaux sociaux',
                'required_keys': ['FACEBOOK_ACCESS_TOKEN', 'FACEBOOK_PAGE_ID'],
                'optional_keys': ['INSTAGRAM_ACCOUNT_ID'],
                'status': 'not_configured',
                'features': ['Publication Facebook', 'Publication Instagram', 'Analytics']
            },
            'linkedin': {
                'name': 'LinkedIn',
                'description': 'Réseau professionnel',
                'required_keys': ['LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_PERSON_ID'],
                'optional_keys': [],
                'status': 'not_configured',
                'features': ['Publication entreprise', 'Partage d\'articles']
            },
            'twitter': {
                'name': 'Twitter/X',
                'description': 'Microblogging',
                'required_keys': ['TWITTER_BEARER_TOKEN'],
                'optional_keys': ['TWITTER_API_KEY', 'TWITTER_API_SECRET'],
                'status': 'not_configured',
                'features': ['Tweets', 'Analytics de base']
            },
            'google_analytics': {
                'name': 'Google Analytics 4',
                'description': 'Analytics et tracking',
                'required_keys': ['GA4_PROPERTY_ID'],
                'optional_keys': ['GA4_SERVICE_ACCOUNT_KEY', 'GA4_CREDENTIALS_PATH', 'GA4_API_SECRET'],
                'status': 'not_configured',
                'features': ['Métriques', 'Conversions', 'Sources de trafic', 'Events personnalisés']
            }
        }
        
        self.update_integration_status()
    
    def update_integration_status(self):
        """Met à jour le statut de toutes les intégrations"""
        for integration_key, config in self.integrations.items():
            required_keys = config['required_keys']
            configured_keys = [key for key in required_keys if os.environ.get(key)]
            
            if len(configured_keys) == len(required_keys):
                config['status'] = 'active'
                config['configured_keys'] = len(configured_keys)
                config['total_keys'] = len(required_keys + config.get('optional_keys', []))
            elif len(configured_keys) > 0:
                config['status'] = 'partial'
                config['configured_keys'] = len(configured_keys)
                config['total_keys'] = len(required_keys + config.get('optional_keys', []))
            else:
                config['status'] = 'not_configured'
                config['configured_keys'] = 0
                config['total_keys'] = len(required_keys + config.get('optional_keys', []))
    
    def get_integration_status(self, integration_key: str) -> Dict[str, Any]:
        """Récupère le statut détaillé d'une intégration"""
        if integration_key not in self.integrations:
            return {'error': 'Integration not found'}
        
        config = self.integrations[integration_key]
        
        # Vérifier chaque clé
        key_status = {}
        for key in config['required_keys'] + config.get('optional_keys', []):
            key_status[key] = {
                'configured': bool(os.environ.get(key)),
                'required': key in config['required_keys'],
                'masked_value': self._mask_key_value(os.environ.get(key)) if os.environ.get(key) else None
            }
        
        return {
            'name': config['name'],
            'description': config['description'],
            'status': config['status'],
            'features': config['features'],
            'keys': key_status,
            'test_available': integration_key in ['stripe', 'sendgrid', 'google_analytics']
        }
    
    def _mask_key_value(self, value: str) -> str:
        """Masque une clé API pour l'affichage"""
        if not value:
            return ''
        
        if len(value) <= 8:
            return '*' * len(value)
        
        return value[:4] + '*' * (len(value) - 8) + value[-4:]
    
    def test_integration(self, integration_key: str) -> Dict[str, Any]:
        """Teste une intégration spécifique"""
        if integration_key == 'stripe':
            return self._test_stripe()
        elif integration_key == 'sendgrid':
            return self._test_sendgrid()
        elif integration_key == 'google_analytics':
            return self._test_google_analytics()
        elif integration_key == 'facebook':
            return self._test_facebook()
        elif integration_key == 'linkedin':
            return self._test_linkedin()
        elif integration_key == 'twitter':
            return self._test_twitter()
        else:
            return {'success': False, 'error': 'Test non disponible pour cette intégration'}
    
    def _test_stripe(self) -> Dict[str, Any]:
        """Test de l'intégration Stripe"""
        try:
            from stripe_integration import stripe_manager
            
            if not stripe_manager.enabled:
                return {'success': False, 'error': 'Stripe non configuré'}
            
            # Test simple : récupérer les informations du compte
            import stripe
            account = stripe.Account.retrieve()
            
            return {
                'success': True,
                'message': f'Connexion réussie - Compte: {account.display_name or account.id}',
                'details': {
                    'account_id': account.id,
                    'country': account.country,
                    'currency': account.default_currency
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Erreur test Stripe: {str(e)}'}
    
    def _test_sendgrid(self) -> Dict[str, Any]:
        """Test de l'intégration SendGrid"""
        try:
            from email_marketing_integration import email_marketing
            
            if not email_marketing.enabled:
                return {'success': False, 'error': 'SendGrid non configuré'}
            
            # Test simple : vérifier l'API
            import requests
            
            response = requests.get(
                f"{email_marketing.base_url}/user/profile",
                headers=email_marketing.headers
            )
            
            if response.status_code == 200:
                profile = response.json()
                return {
                    'success': True,
                    'message': 'Connexion SendGrid réussie',
                    'details': {
                        'email': profile.get('email'),
                        'username': profile.get('username')
                    }
                }
            else:
                return {'success': False, 'error': f'Erreur API SendGrid: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Erreur test SendGrid: {str(e)}'}
    
    def _test_google_analytics(self) -> Dict[str, Any]:
        """Test de l'intégration Google Analytics"""
        try:
            from analytics_integration import analytics_manager
            
            if not analytics_manager.enabled:
                return {'success': False, 'error': 'Google Analytics non configuré'}
            
            # Test simple : récupérer les métriques de base
            metrics = analytics_manager.get_basic_metrics("7daysAgo", "today")
            
            if metrics:
                return {
                    'success': True,
                    'message': 'Connexion Google Analytics réussie',
                    'details': {
                        'property_id': analytics_manager.property_id,
                        'sessions_7_days': metrics['totals']['total_sessions']
                    }
                }
            else:
                return {'success': False, 'error': 'Impossible de récupérer les données'}
                
        except Exception as e:
            return {'success': False, 'error': f'Erreur test Google Analytics: {str(e)}'}
    
    def _test_facebook(self) -> Dict[str, Any]:
        """Test de l'intégration Facebook"""
        try:
            from social_media_integration import social_media
            
            if 'facebook' not in social_media.enabled_platforms:
                return {'success': False, 'error': 'Facebook non configuré'}
            
            # Test simple : vérifier les permissions de la page
            import requests
            
            url = f"https://graph.facebook.com/v18.0/{social_media.facebook_page_id}"
            params = {
                'fields': 'name,id',
                'access_token': social_media.facebook_access_token
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                page_data = response.json()
                return {
                    'success': True,
                    'message': 'Connexion Facebook réussie',
                    'details': {
                        'page_name': page_data.get('name'),
                        'page_id': page_data.get('id')
                    }
                }
            else:
                return {'success': False, 'error': f'Erreur API Facebook: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Erreur test Facebook: {str(e)}'}
    
    def _test_linkedin(self) -> Dict[str, Any]:
        """Test de l'intégration LinkedIn"""
        try:
            from social_media_integration import social_media
            
            if 'linkedin' not in social_media.enabled_platforms:
                return {'success': False, 'error': 'LinkedIn non configuré'}
            
            # Test simple : récupérer le profil
            import requests
            
            url = "https://api.linkedin.com/v2/people/(id:me)"
            headers = {
                'Authorization': f'Bearer {social_media.linkedin_access_token}'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Connexion LinkedIn réussie'
                }
            else:
                return {'success': False, 'error': f'Erreur API LinkedIn: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Erreur test LinkedIn: {str(e)}'}
    
    def _test_twitter(self) -> Dict[str, Any]:
        """Test de l'intégration Twitter"""
        try:
            from social_media_integration import social_media
            
            if 'twitter' not in social_media.enabled_platforms:
                return {'success': False, 'error': 'Twitter non configuré'}
            
            # Test simple : vérifier le token
            import requests
            
            url = "https://api.twitter.com/2/users/me"
            headers = {
                'Authorization': f'Bearer {social_media.twitter_bearer_token}'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'message': 'Connexion Twitter réussie',
                    'details': {
                        'username': user_data.get('data', {}).get('username')
                    }
                }
            else:
                return {'success': False, 'error': f'Erreur API Twitter: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Erreur test Twitter: {str(e)}'}
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Génère un résumé pour le tableau de bord"""
        self.update_integration_status()
        
        total_integrations = len(self.integrations)
        active_integrations = len([i for i in self.integrations.values() if i['status'] == 'active'])
        partial_integrations = len([i for i in self.integrations.values() if i['status'] == 'partial'])
        
        return {
            'total_integrations': total_integrations,
            'active_integrations': active_integrations,
            'partial_integrations': partial_integrations,
            'not_configured': total_integrations - active_integrations - partial_integrations,
            'integrations': self.integrations,
            'recommendations': self._get_recommendations()
        }
    
    def _get_recommendations(self) -> List[Dict[str, str]]:
        """Génère des recommandations de configuration"""
        recommendations = []
        
        if self.integrations['stripe']['status'] != 'active':
            recommendations.append({
                'title': 'Configurez Stripe',
                'description': 'Activez les paiements pour monétiser votre plateforme',
                'priority': 'high',
                'integration': 'stripe'
            })
        
        if self.integrations['sendgrid']['status'] != 'active':
            recommendations.append({
                'title': 'Configurez SendGrid',
                'description': 'Automatisez vos campagnes email marketing',
                'priority': 'medium',
                'integration': 'sendgrid'
            })
        
        if self.integrations['google_analytics']['status'] != 'active':
            recommendations.append({
                'title': 'Configurez Google Analytics',
                'description': 'Suivez les performances de votre plateforme',
                'priority': 'medium',
                'integration': 'google_analytics'
            })
        
        social_configured = any(
            self.integrations[key]['status'] == 'active' 
            for key in ['facebook', 'linkedin', 'twitter']
        )
        
        if not social_configured:
            recommendations.append({
                'title': 'Configurez les réseaux sociaux',
                'description': 'Automatisez vos publications marketing',
                'priority': 'low',
                'integration': 'facebook'
            })
        
        return recommendations

# Instance globale
integrations_dashboard = IntegrationsDashboard()