"""
Barrière de sécurité pour les paiements - Système de sandbox avec limitations
Permet de préparer tout le système de paiement mais avec des garde-fous stricts
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from functools import wraps
import hashlib
import hmac

logger = logging.getLogger(__name__)

# Blueprint pour la barrière de paiement
payment_security_bp = Blueprint('payment_security', __name__, url_prefix='/payment-security')

class PaymentSecurityBarrier:
    """Gestionnaire de la barrière de sécurité des paiements"""
    
    def __init__(self):
        self.sandbox_mode = True  # Toujours en sandbox par défaut
        self.max_test_amount = 100  # Maximum 100€ en test
        self.allowed_test_users = []  # Liste d'utilisateurs autorisés pour les tests
        self.payment_enabled = False  # Paiements désactivés par défaut
        self.admin_unlock_key = None
        self._load_security_config()
    
    def _load_security_config(self):
        """Charge la configuration de sécurité"""
        self.sandbox_mode = os.environ.get('PAYMENT_SANDBOX_MODE', 'true').lower() == 'true'
        self.payment_enabled = os.environ.get('PAYMENT_SYSTEM_ENABLED', 'false').lower() == 'true'
        self.admin_unlock_key = os.environ.get('PAYMENT_ADMIN_UNLOCK_KEY')
        
        # Utilisateurs autorisés pour les tests (emails)
        test_users_env = os.environ.get('PAYMENT_TEST_USERS', '')
        if test_users_env:
            self.allowed_test_users = [email.strip() for email in test_users_env.split(',')]
        
        logger.info(f"Barrière paiement - Sandbox: {self.sandbox_mode}, Enabled: {self.payment_enabled}")
    
    def is_payment_allowed(self, user_email, amount=0):
        """
        Vérifie si un paiement est autorisé selon les règles de sécurité
        
        Args:
            user_email: Email de l'utilisateur
            amount: Montant du paiement
            
        Returns:
            dict: Résultat de la vérification avec détails
        """
        checks = {
            'system_enabled': self.payment_enabled,
            'sandbox_mode': self.sandbox_mode,
            'user_authorized': user_email in self.allowed_test_users if self.sandbox_mode else True,
            'amount_valid': amount <= self.max_test_amount if self.sandbox_mode else True,
            'stripe_configured': bool(os.environ.get('STRIPE_SECRET_KEY')),
            'webhook_configured': bool(os.environ.get('STRIPE_WEBHOOK_SECRET'))
        }
        
        # Tous les checks doivent passer
        allowed = all(checks.values())
        
        return {
            'allowed': allowed,
            'checks': checks,
            'mode': 'sandbox' if self.sandbox_mode else 'production',
            'restrictions': self._get_current_restrictions()
        }
    
    def _get_current_restrictions(self):
        """Retourne les restrictions actuelles"""
        restrictions = []
        
        if not self.payment_enabled:
            restrictions.append("Système de paiement désactivé")
        
        if self.sandbox_mode:
            restrictions.append(f"Mode sandbox - Maximum {self.max_test_amount}€")
            restrictions.append(f"Utilisateurs autorisés uniquement: {len(self.allowed_test_users)}")
        
        if not os.environ.get('STRIPE_SECRET_KEY'):
            restrictions.append("Clé Stripe non configurée")
        
        if not os.environ.get('STRIPE_WEBHOOK_SECRET'):
            restrictions.append("Webhook Stripe non configuré")
        
        return restrictions
    
    def create_secure_payment_intent(self, amount, currency='eur', user_email=None):
        """
        Crée un PaymentIntent avec toutes les vérifications de sécurité
        
        Args:
            amount: Montant en centimes
            currency: Devise
            user_email: Email utilisateur
            
        Returns:
            dict: Résultat avec PaymentIntent ou erreur
        """
        # Vérifications préliminaires
        check_result = self.is_payment_allowed(user_email, amount / 100)
        
        if not check_result['allowed']:
            return {
                'success': False,
                'error': 'Paiement non autorisé',
                'restrictions': check_result['restrictions'],
                'checks': check_result['checks']
            }
        
        try:
            import stripe
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
            
            # Métadonnées de sécurité
            metadata = {
                'security_mode': 'sandbox' if self.sandbox_mode else 'production',
                'user_email': user_email,
                'created_via': 'security_barrier',
                'max_amount_check': str(amount <= self.max_test_amount * 100),
                'timestamp': str(int(datetime.utcnow().timestamp()))
            }
            
            # Créer le PaymentIntent avec limitations
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata,
                capture_method='manual' if self.sandbox_mode else 'automatic',  # Capture manuelle en sandbox
                description=f"NinjaLead.ai - {check_result['mode']} payment"
            )
            
            # Log de sécurité
            logger.info(f"PaymentIntent créé - Mode: {check_result['mode']}, "
                       f"User: {user_email}, Amount: {amount/100}€")
            
            return {
                'success': True,
                'payment_intent': payment_intent,
                'mode': check_result['mode'],
                'restrictions': check_result['restrictions']
            }
            
        except Exception as e:
            logger.error(f"Erreur création PaymentIntent sécurisé: {e}")
            return {
                'success': False,
                'error': f'Erreur technique: {str(e)}',
                'restrictions': check_result['restrictions']
            }
    
    def validate_webhook_security(self, payload, signature):
        """
        Valide la sécurité d'un webhook avec vérifications supplémentaires
        
        Args:
            payload: Contenu du webhook
            signature: Signature Stripe
            
        Returns:
            dict: Résultat de la validation
        """
        try:
            import stripe
            
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            if not webhook_secret:
                return {'valid': False, 'error': 'Webhook secret non configuré'}
            
            # Vérification standard Stripe
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            
            # Vérifications supplémentaires en sandbox
            if self.sandbox_mode:
                # Vérifier que l'événement contient les métadonnées de sécurité
                if event.get('data', {}).get('object', {}).get('metadata', {}).get('security_mode') != 'sandbox':
                    logger.warning("Webhook reçu sans métadonnées de sécurité sandbox")
                
                # Limiter les types d'événements en sandbox
                allowed_events = [
                    'payment_intent.succeeded',
                    'payment_intent.payment_failed',
                    'customer.subscription.created',
                    'customer.subscription.updated',
                    'invoice.payment_succeeded',
                    'invoice.payment_failed'
                ]
                
                if event['type'] not in allowed_events:
                    logger.warning(f"Type d'événement non autorisé en sandbox: {event['type']}")
                    return {'valid': False, 'error': f'Événement {event["type"]} non autorisé en sandbox'}
            
            return {
                'valid': True,
                'event': event,
                'mode': 'sandbox' if self.sandbox_mode else 'production'
            }
            
        except Exception as e:
            logger.error(f"Erreur validation webhook: {e}")
            return {'valid': False, 'error': str(e)}
    
    def emergency_disable_payments(self, reason=""):
        """
        Désactive immédiatement tous les paiements (arrêt d'urgence)
        
        Args:
            reason: Raison de la désactivation
        """
        self.payment_enabled = False
        logger.critical(f"ARRÊT D'URGENCE PAIEMENTS - Raison: {reason}")
        
        # Sauvegarder l'état d'urgence
        emergency_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'reason': reason,
            'disabled_by': 'emergency_system'
        }
        
        try:
            with open('payment_emergency.log', 'a') as f:
                f.write(json.dumps(emergency_log) + '\n')
        except Exception as e:
            logger.error(f"Erreur sauvegarde log urgence: {e}")
    
    def admin_unlock_production(self, unlock_key, admin_email):
        """
        Déverrouille le mode production avec clé admin
        
        Args:
            unlock_key: Clé de déverrouillage
            admin_email: Email de l'administrateur
            
        Returns:
            bool: Succès du déverrouillage
        """
        if not self.admin_unlock_key:
            logger.error("Clé de déverrouillage non configurée")
            return False
        
        # Vérifier la clé
        expected_key = hmac.new(
            self.admin_unlock_key.encode(),
            admin_email.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(unlock_key, expected_key):
            logger.error(f"Tentative de déverrouillage échouée pour {admin_email}")
            return False
        
        # Déverrouiller
        self.sandbox_mode = False
        self.payment_enabled = True
        
        logger.critical(f"PRODUCTION DÉVERROUILLÉE par {admin_email}")
        
        # Log de sécurité
        unlock_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'admin_email': admin_email,
            'action': 'production_unlocked'
        }
        
        try:
            with open('payment_security.log', 'a') as f:
                f.write(json.dumps(unlock_log) + '\n')
        except Exception as e:
            logger.error(f"Erreur sauvegarde log déverrouillage: {e}")
        
        return True

# Instance globale de la barrière
payment_barrier = PaymentSecurityBarrier()

def require_payment_security(f):
    """
    Décorateur pour vérifier la sécurité des paiements
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentification requise'}), 401
        
        check_result = payment_barrier.is_payment_allowed(current_user.email)
        
        if not check_result['allowed']:
            return jsonify({
                'error': 'Paiement non autorisé',
                'restrictions': check_result['restrictions'],
                'mode': check_result['mode']
            }), 403
        
        # Ajouter les infos de sécurité à la requête
        request.payment_security = check_result
        
        return f(*args, **kwargs)
    
    return decorated_function

@payment_security_bp.route('/status')
@login_required
def security_status():
    """Affiche le statut de la barrière de sécurité"""
    check_result = payment_barrier.is_payment_allowed(current_user.email)
    
    return jsonify({
        'status': 'operational',
        'payment_allowed': check_result['allowed'],
        'mode': check_result['mode'],
        'restrictions': check_result['restrictions'],
        'checks': check_result['checks'],
        'user_authorized': current_user.email in payment_barrier.allowed_test_users
    })

@payment_security_bp.route('/test-payment', methods=['POST'])
@require_payment_security
def test_payment():
    """Endpoint de test pour les paiements sécurisés"""
    amount = int(request.json.get('amount', 0))  # En centimes
    
    if amount > payment_barrier.max_test_amount * 100:
        return jsonify({
            'error': f'Montant maximum autorisé: {payment_barrier.max_test_amount}€'
        }), 400
    
    result = payment_barrier.create_secure_payment_intent(
        amount=amount,
        user_email=current_user.email
    )
    
    return jsonify(result)

@payment_security_bp.route('/emergency-disable', methods=['POST'])
@login_required
def emergency_disable():
    """Endpoint d'arrêt d'urgence des paiements"""
    # Vérifier les permissions admin (à implémenter selon votre système)
    if not current_user.is_admin:  # Adapter selon votre modèle
        return jsonify({'error': 'Permissions insuffisantes'}), 403
    
    reason = request.json.get('reason', 'Arrêt d\'urgence manuel')
    payment_barrier.emergency_disable_payments(reason)
    
    return jsonify({
        'success': True,
        'message': 'Paiements désactivés en urgence',
        'timestamp': datetime.utcnow().isoformat()
    })

@payment_security_bp.route('/admin-unlock', methods=['POST'])
@login_required
def admin_unlock():
    """Endpoint de déverrouillage administrateur"""
    if not current_user.is_admin:
        return jsonify({'error': 'Permissions insuffisantes'}), 403
    
    unlock_key = request.json.get('unlock_key')
    if not unlock_key:
        return jsonify({'error': 'Clé de déverrouillage requise'}), 400
    
    success = payment_barrier.admin_unlock_production(unlock_key, current_user.email)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Mode production déverrouillé',
            'mode': 'production'
        })
    else:
        return jsonify({'error': 'Échec du déverrouillage'}), 403

def init_payment_security(app):
    """Initialise la barrière de sécurité des paiements"""
    app.register_blueprint(payment_security_bp)
    
    # Logs de démarrage
    logger.info("Barrière de sécurité des paiements initialisée")
    logger.info(f"Mode: {'Sandbox' if payment_barrier.sandbox_mode else 'Production'}")
    logger.info(f"Paiements activés: {payment_barrier.payment_enabled}")
    
    return payment_barrier