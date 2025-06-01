"""
Système de feedback utilisateur intégré avec Sentry.io
Collecte et gestion des retours utilisateurs avec assistance contextuelle
"""

import sentry_sdk
from sentry_sdk import capture_message
from flask import request, session, current_app
from datetime import datetime
import logging
import json
from enum import Enum

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    UI_UX_ISSUE = "ui_ux_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    ASSISTANCE_REQUEST = "assistance_request"

class FeedbackPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class UserFeedbackManager:
    """Gestionnaire principal pour le système de feedback utilisateur"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le système de feedback"""
        self.app = app
        app.config.setdefault('FEEDBACK_ENABLED', True)
        app.config.setdefault('FEEDBACK_RATE_LIMIT', 10)  # 10 feedbacks par heure par utilisateur
        
        logger.info("User feedback system initialized")
    
    def collect_feedback(self, user_id, feedback_type, message, context=None, priority=FeedbackPriority.MEDIUM):
        """
        Collecte un feedback utilisateur et l'envoie à Sentry
        
        Args:
            user_id: ID de l'utilisateur
            feedback_type: Type de feedback (FeedbackType)
            message: Message du feedback
            context: Contexte supplémentaire (dict)
            priority: Priorité du feedback
            
        Returns:
            dict: Résultat de l'envoi du feedback
        """
        try:
            # Prépare les données du feedback
            feedback_data = {
                'user_id': user_id,
                'type': feedback_type.value if isinstance(feedback_type, FeedbackType) else feedback_type,
                'message': message,
                'priority': priority.value if isinstance(priority, FeedbackPriority) else priority,
                'timestamp': datetime.utcnow().isoformat(),
                'page_url': request.url if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'context': context or {}
            }
            
            # Enrichit le contexte avec des informations système
            feedback_data['context'].update({
                'session_id': session.get('session_id'),
                'referrer': request.referrer if request else None,
                'ip_address': request.remote_addr if request else None
            })
            
            # Configure l'utilisateur dans Sentry
            sentry_sdk.set_user({
                "id": user_id,
                "feedback_type": feedback_data['type'],
                "priority": feedback_data['priority']
            })
            
            # Envoie le message à Sentry avec des tags appropriés
            sentry_sdk.set_tag("feedback_type", feedback_data['type'])
            sentry_sdk.set_tag("feedback_priority", feedback_data['priority'])
            sentry_sdk.set_context("feedback_context", feedback_data['context'])
            
            # Capture le feedback comme message Sentry
            event_id = capture_message(
                f"[FEEDBACK] {feedback_data['type'].upper()}: {message}",
                level="info"
            )
            
            # Note: Feedback utilisateur direct avec Sentry
            # (capture_user_feedback non disponible dans cette version)
            
            logger.info(f"Feedback collected: {feedback_data['type']} from user {user_id}")
            
            return {
                'success': True,
                'event_id': event_id,
                'feedback_id': feedback_data['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_contextual_help(self, page_route, user_role=None):
        """
        Retourne l'aide contextuelle pour une page donnée
        
        Args:
            page_route: Route de la page courante
            user_role: Rôle de l'utilisateur (optionnel)
            
        Returns:
            dict: Données d'aide contextuelle
        """
        help_content = {
            '/': {
                'title': 'Tableau de Bord Principal',
                'description': 'Vue d\'ensemble de vos campagnes et performances',
                'tips': [
                    'Utilisez les métriques pour suivre vos performances',
                    'Créez de nouvelles campagnes via le bouton "Nouvelle Campagne"',
                    'Consultez vos niches de marché pour mieux cibler'
                ]
            },
            '/campaigns': {
                'title': 'Gestion des Campagnes',
                'description': 'Créez et gérez vos campagnes marketing',
                'tips': [
                    'Définissez clairement votre audience cible',
                    'Utilisez des mots-clés pertinents',
                    'Suivez régulièrement les performances'
                ]
            },
            '/admin/performance': {
                'title': 'Tableau de Bord Performance',
                'description': 'Surveillez et optimisez les performances système',
                'tips': [
                    'Vérifiez régulièrement les métriques de cache',
                    'Surveillez les requêtes lentes de base de données',
                    'Optimisez vos assets pour de meilleures performances'
                ]
            },
            '/products': {
                'title': 'Gestion des Produits',
                'description': 'Gérez votre catalogue de produits',
                'tips': [
                    'Ajoutez des descriptions détaillées',
                    'Utilisez des images de qualité',
                    'Optimisez pour le SEO'
                ]
            }
        }
        
        return help_content.get(page_route, {
            'title': 'Aide',
            'description': 'Page d\'aide générale',
            'tips': ['Utilisez le formulaire de feedback pour toute question']
        })

# Instance globale du gestionnaire de feedback
feedback_manager = UserFeedbackManager()

def init_feedback_system(app):
    """Initialise le système de feedback pour l'application Flask"""
    feedback_manager.init_app(app)
    return feedback_manager