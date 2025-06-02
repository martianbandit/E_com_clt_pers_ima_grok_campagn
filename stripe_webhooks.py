"""
Gestion complète des webhooks Stripe pour les événements de paiement
et mise à jour automatique des statuts d'abonnement
"""

import stripe
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app import db
from models import User, Subscription, PaymentTransaction
import hmac
import hashlib

logger = logging.getLogger(__name__)

# Blueprint pour les webhooks Stripe
webhooks_bp = Blueprint('stripe_webhooks', __name__, url_prefix='/stripe/webhooks')

# Configuration Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

class StripeWebhookHandler:
    """Gestionnaire centralisé des événements webhook Stripe"""
    
    def __init__(self):
        self.event_handlers = {
            'customer.subscription.created': self.handle_subscription_created,
            'customer.subscription.updated': self.handle_subscription_updated,
            'customer.subscription.deleted': self.handle_subscription_deleted,
            'invoice.payment_succeeded': self.handle_payment_succeeded,
            'invoice.payment_failed': self.handle_payment_failed,
            'checkout.session.completed': self.handle_checkout_completed,
            'customer.created': self.handle_customer_created,
            'payment_intent.succeeded': self.handle_payment_intent_succeeded,
            'payment_intent.payment_failed': self.handle_payment_intent_failed,
        }
    
    def process_event(self, event):
        """
        Traite un événement webhook selon son type
        
        Args:
            event: Événement Stripe webhook
            
        Returns:
            bool: True si traité avec succès
        """
        event_type = event['type']
        
        if event_type in self.event_handlers:
            try:
                handler = self.event_handlers[event_type]
                return handler(event['data']['object'])
            except Exception as e:
                logger.error(f"Erreur traitement webhook {event_type}: {e}")
                return False
        else:
            logger.info(f"Événement webhook non géré: {event_type}")
            return True
    
    def handle_subscription_created(self, subscription):
        """Gère la création d'un nouvel abonnement"""
        try:
            customer_id = subscription['customer']
            
            # Récupérer les informations client Stripe
            customer = stripe.Customer.retrieve(customer_id)
            
            # Trouver l'utilisateur par email
            user = User.query.filter_by(email=customer['email']).first()
            if not user:
                logger.error(f"Utilisateur non trouvé pour l'email: {customer['email']}")
                return False
            
            # Créer ou mettre à jour l'abonnement
            db_subscription = Subscription.query.filter_by(user_id=user.id).first()
            if not db_subscription:
                db_subscription = Subscription(user_id=user.id)
                db.session.add(db_subscription)
            
            # Mettre à jour les détails de l'abonnement
            db_subscription.stripe_subscription_id = subscription['id']
            db_subscription.stripe_customer_id = customer_id
            db_subscription.status = subscription['status']
            db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
            db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            
            # Déterminer le plan à partir des métadonnées
            if subscription.get('metadata'):
                db_subscription.plan_id = subscription['metadata'].get('plan_id')
                db_subscription.billing_period = subscription['metadata'].get('billing_period')
            
            db.session.commit()
            
            logger.info(f"Abonnement créé pour l'utilisateur {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur création abonnement: {e}")
            db.session.rollback()
            return False
    
    def handle_subscription_updated(self, subscription):
        """Gère la mise à jour d'un abonnement"""
        try:
            db_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription['id']
            ).first()
            
            if db_subscription:
                db_subscription.status = subscription['status']
                db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
                db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
                db.session.commit()
                
                logger.info(f"Abonnement mis à jour: {subscription['id']}")
                return True
            else:
                logger.warning(f"Abonnement non trouvé: {subscription['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur mise à jour abonnement: {e}")
            db.session.rollback()
            return False
    
    def handle_subscription_deleted(self, subscription):
        """Gère la suppression/annulation d'un abonnement"""
        try:
            db_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription['id']
            ).first()
            
            if db_subscription:
                db_subscription.status = 'canceled'
                db_subscription.canceled_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Abonnement annulé: {subscription['id']}")
                return True
            else:
                logger.warning(f"Abonnement non trouvé pour annulation: {subscription['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur annulation abonnement: {e}")
            db.session.rollback()
            return False
    
    def handle_payment_succeeded(self, invoice):
        """Gère les paiements réussis"""
        try:
            # Enregistrer la transaction
            transaction = PaymentTransaction(
                stripe_payment_intent_id=invoice.get('payment_intent'),
                stripe_invoice_id=invoice['id'],
                amount=invoice['amount_paid'] / 100,  # Convertir de centimes
                currency=invoice['currency'],
                status='succeeded',
                created_at=datetime.fromtimestamp(invoice['created'])
            )
            
            # Associer à l'utilisateur si possible
            if invoice.get('customer'):
                subscription = Subscription.query.filter_by(
                    stripe_customer_id=invoice['customer']
                ).first()
                if subscription:
                    transaction.user_id = subscription.user_id
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Paiement réussi enregistré: {invoice['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur enregistrement paiement réussi: {e}")
            db.session.rollback()
            return False
    
    def handle_payment_failed(self, invoice):
        """Gère les échecs de paiement"""
        try:
            # Enregistrer la tentative de paiement échouée
            transaction = PaymentTransaction(
                stripe_invoice_id=invoice['id'],
                amount=invoice['amount_due'] / 100,
                currency=invoice['currency'],
                status='failed',
                created_at=datetime.fromtimestamp(invoice['created']),
                failure_reason=invoice.get('last_finalization_error', {}).get('message', 'Unknown')
            )
            
            # Associer à l'utilisateur
            if invoice.get('customer'):
                subscription = Subscription.query.filter_by(
                    stripe_customer_id=invoice['customer']
                ).first()
                if subscription:
                    transaction.user_id = subscription.user_id
                    
                    # Mettre à jour le statut d'abonnement si nécessaire
                    if subscription.status == 'active':
                        subscription.status = 'past_due'
                        db.session.commit()
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.warning(f"Échec de paiement enregistré: {invoice['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur enregistrement échec paiement: {e}")
            db.session.rollback()
            return False
    
    def handle_checkout_completed(self, session):
        """Gère la finalisation d'une session de checkout"""
        try:
            # Mettre à jour les métadonnées utilisateur
            if session.get('metadata'):
                user_id = session['metadata'].get('user_id')
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        user.stripe_customer_id = session.get('customer')
                        db.session.commit()
            
            logger.info(f"Checkout complété: {session['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur finalisation checkout: {e}")
            db.session.rollback()
            return False
    
    def handle_customer_created(self, customer):
        """Gère la création d'un nouveau client Stripe"""
        try:
            # Mettre à jour l'utilisateur avec l'ID client Stripe
            user = User.query.filter_by(email=customer['email']).first()
            if user:
                user.stripe_customer_id = customer['id']
                db.session.commit()
                
                logger.info(f"Client Stripe associé à l'utilisateur {user.id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur association client Stripe: {e}")
            db.session.rollback()
            return False
    
    def handle_payment_intent_succeeded(self, payment_intent):
        """Gère les succès de PaymentIntent"""
        try:
            # Enregistrer la transaction pour les paiements uniques
            transaction = PaymentTransaction(
                stripe_payment_intent_id=payment_intent['id'],
                amount=payment_intent['amount'] / 100,
                currency=payment_intent['currency'],
                status='succeeded',
                created_at=datetime.fromtimestamp(payment_intent['created'])
            )
            
            # Associer à l'utilisateur si possible via les métadonnées
            if payment_intent.get('metadata', {}).get('user_id'):
                transaction.user_id = int(payment_intent['metadata']['user_id'])
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"PaymentIntent réussi: {payment_intent['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur PaymentIntent réussi: {e}")
            db.session.rollback()
            return False
    
    def handle_payment_intent_failed(self, payment_intent):
        """Gère les échecs de PaymentIntent"""
        try:
            transaction = PaymentTransaction(
                stripe_payment_intent_id=payment_intent['id'],
                amount=payment_intent['amount'] / 100,
                currency=payment_intent['currency'],
                status='failed',
                created_at=datetime.fromtimestamp(payment_intent['created']),
                failure_reason=payment_intent.get('last_payment_error', {}).get('message', 'Unknown')
            )
            
            if payment_intent.get('metadata', {}).get('user_id'):
                transaction.user_id = int(payment_intent['metadata']['user_id'])
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.warning(f"PaymentIntent échoué: {payment_intent['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur PaymentIntent échoué: {e}")
            db.session.rollback()
            return False

# Instance globale du gestionnaire
webhook_handler = StripeWebhookHandler()

@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """
    Endpoint principal pour recevoir les webhooks Stripe
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET non configuré")
        return jsonify({'error': 'Webhook secret not configured'}), 500
    
    try:
        # Vérifier la signature du webhook
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        logger.info(f"Webhook reçu: {event['type']}")
        
        # Traiter l'événement
        success = webhook_handler.process_event(event)
        
        if success:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process event'}), 400
            
    except ValueError as e:
        logger.error(f"Payload webhook invalide: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Signature webhook invalide: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"Erreur traitement webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@webhooks_bp.route('/test', methods=['POST'])
def test_webhook():
    """Endpoint de test pour les webhooks en développement"""
    if os.environ.get('FLASK_ENV') != 'development':
        return jsonify({'error': 'Test endpoint only available in development'}), 403
    
    try:
        event_data = request.get_json()
        success = webhook_handler.process_event(event_data)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'processed': success
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur test webhook: {e}")
        return jsonify({'error': str(e)}), 500

def setup_stripe_webhooks():
    """
    Configure les webhooks Stripe automatiquement
    """
    if not stripe.api_key:
        logger.warning("Clé API Stripe non configurée - webhooks non créés")
        return False
    
    try:
        # Lister les webhooks existants
        webhooks = stripe.WebhookEndpoint.list()
        
        # URL du webhook
        webhook_url = f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/stripe/webhooks/stripe"
        
        # Vérifier si le webhook existe déjà
        existing_webhook = None
        for webhook in webhooks.data:
            if webhook.url == webhook_url:
                existing_webhook = webhook
                break
        
        # Événements à écouter
        events = [
            'customer.subscription.created',
            'customer.subscription.updated', 
            'customer.subscription.deleted',
            'invoice.payment_succeeded',
            'invoice.payment_failed',
            'checkout.session.completed',
            'customer.created',
            'payment_intent.succeeded',
            'payment_intent.payment_failed'
        ]
        
        if existing_webhook:
            # Mettre à jour le webhook existant
            stripe.WebhookEndpoint.modify(
                existing_webhook.id,
                enabled_events=events
            )
            logger.info(f"Webhook Stripe mis à jour: {webhook_url}")
        else:
            # Créer un nouveau webhook
            webhook = stripe.WebhookEndpoint.create(
                url=webhook_url,
                enabled_events=events
            )
            logger.info(f"Webhook Stripe créé: {webhook_url}")
            logger.info(f"Secret du webhook: {webhook.secret}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur configuration webhooks Stripe: {e}")
        return False