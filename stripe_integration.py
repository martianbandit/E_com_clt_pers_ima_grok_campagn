"""
Intégration Stripe complète pour NinjaLead.ai
Gestion des paiements, abonnements et webhooks
"""

import os
import logging
import stripe
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class StripeManager:
    """Gestionnaire des paiements et abonnements Stripe"""
    
    def __init__(self):
        self.stripe_secret_key = os.environ.get('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
            self.enabled = True
            logger.info("Stripe payment system initialized")
        else:
            self.enabled = False
            logger.warning("Stripe non configuré - clés API manquantes")
    
    def create_customer(self, user_email: str, user_name: str, metadata: Dict = None) -> Optional[str]:
        """Créer un client Stripe"""
        if not self.enabled:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=user_email,
                name=user_name,
                metadata=metadata or {}
            )
            
            logger.info(f"Client Stripe créé: {customer.id} pour {user_email}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur création client Stripe: {str(e)}")
            return None
    
    def create_payment_intent(self, 
                            amount: int, 
                            currency: str = 'eur',
                            customer_id: str = None,
                            metadata: Dict = None) -> Optional[Dict]:
        """Créer une intention de paiement"""
        if not self.enabled:
            return None
        
        try:
            intent_params = {
                'amount': amount,  # en centimes
                'currency': currency,
                'automatic_payment_methods': {'enabled': True},
                'metadata': metadata or {}
            }
            
            if customer_id:
                intent_params['customer'] = customer_id
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': amount,
                'currency': currency
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur création PaymentIntent: {str(e)}")
            return None
    
    def create_subscription(self, 
                          customer_id: str,
                          price_id: str,
                          trial_days: int = 0,
                          metadata: Dict = None) -> Optional[Dict]:
        """Créer un abonnement"""
        if not self.enabled:
            return None
        
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
                'metadata': metadata or {}
            }
            
            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days
            
            subscription = stripe.Subscription.create(**subscription_params)
            
            return {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret,
                'status': subscription.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur création abonnement: {str(e)}")
            return None
    
    def cancel_subscription(self, subscription_id: str, immediately: bool = False) -> bool:
        """Annuler un abonnement"""
        if not self.enabled:
            return False
        
        try:
            if immediately:
                stripe.Subscription.delete(subscription_id)
            else:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            logger.info(f"Abonnement annulé: {subscription_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur annulation abonnement: {str(e)}")
            return False
    
    def get_subscription_status(self, subscription_id: str) -> Optional[Dict]:
        """Récupérer le statut d'un abonnement"""
        if not self.enabled:
            return None
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'trial_end': subscription.trial_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur récupération abonnement: {str(e)}")
            return None
    
    def create_checkout_session(self, 
                              price_id: str,
                              success_url: str,
                              cancel_url: str,
                              customer_id: str = None,
                              metadata: Dict = None) -> Optional[str]:
        """Créer une session Checkout"""
        if not self.enabled:
            return None
        
        try:
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'subscription',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': metadata or {}
            }
            
            if customer_id:
                session_params['customer'] = customer_id
            else:
                session_params['customer_creation'] = 'always'
            
            session = stripe.checkout.Session.create(**session_params)
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur création session checkout: {str(e)}")
            return None
    
    def handle_webhook(self, payload: bytes, signature: str) -> Optional[Dict]:
        """Traiter un webhook Stripe"""
        if not self.enabled or not self.webhook_secret:
            return None
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Webhook Stripe reçu: {event['type']}")
            
            # Traiter selon le type d'événement
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_success(event['data']['object'])
            
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failure(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.created':
                return self._handle_subscription_created(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.updated':
                return self._handle_subscription_updated(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.deleted':
                return self._handle_subscription_deleted(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_succeeded':
                return self._handle_invoice_paid(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_failed':
                return self._handle_invoice_failed(event['data']['object'])
            
            return {'status': 'handled', 'type': event['type']}
            
        except ValueError as e:
            logger.error(f"Payload webhook invalide: {str(e)}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Signature webhook invalide: {str(e)}")
            return None
    
    def _handle_payment_success(self, payment_intent) -> Dict:
        """Traiter un paiement réussi"""
        logger.info(f"Paiement réussi: {payment_intent['id']}")
        
        # Ici, vous pouvez mettre à jour votre base de données
        # Activer les fonctionnalités premium, etc.
        
        return {
            'status': 'success',
            'payment_intent_id': payment_intent['id'],
            'amount': payment_intent['amount']
        }
    
    def _handle_payment_failure(self, payment_intent) -> Dict:
        """Traiter un échec de paiement"""
        logger.warning(f"Échec paiement: {payment_intent['id']}")
        
        return {
            'status': 'failed',
            'payment_intent_id': payment_intent['id']
        }
    
    def _handle_subscription_created(self, subscription) -> Dict:
        """Traiter la création d'un abonnement"""
        logger.info(f"Abonnement créé: {subscription['id']}")
        
        return {
            'status': 'subscription_created',
            'subscription_id': subscription['id'],
            'customer_id': subscription['customer']
        }
    
    def _handle_subscription_updated(self, subscription) -> Dict:
        """Traiter la mise à jour d'un abonnement"""
        logger.info(f"Abonnement mis à jour: {subscription['id']}")
        
        return {
            'status': 'subscription_updated',
            'subscription_id': subscription['id'],
            'new_status': subscription['status']
        }
    
    def _handle_subscription_deleted(self, subscription) -> Dict:
        """Traiter la suppression d'un abonnement"""
        logger.info(f"Abonnement supprimé: {subscription['id']}")
        
        return {
            'status': 'subscription_deleted',
            'subscription_id': subscription['id']
        }
    
    def _handle_invoice_paid(self, invoice) -> Dict:
        """Traiter une facture payée"""
        logger.info(f"Facture payée: {invoice['id']}")
        
        return {
            'status': 'invoice_paid',
            'invoice_id': invoice['id'],
            'subscription_id': invoice['subscription']
        }
    
    def _handle_invoice_failed(self, invoice) -> Dict:
        """Traiter l'échec d'une facture"""
        logger.warning(f"Échec facture: {invoice['id']}")
        
        return {
            'status': 'invoice_failed',
            'invoice_id': invoice['id']
        }
    
    def get_customer_invoices(self, customer_id: str, limit: int = 10) -> List[Dict]:
        """Récupérer les factures d'un client"""
        if not self.enabled:
            return []
        
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            
            return [
                {
                    'id': invoice.id,
                    'amount_paid': invoice.amount_paid,
                    'currency': invoice.currency,
                    'status': invoice.status,
                    'created': invoice.created,
                    'hosted_invoice_url': invoice.hosted_invoice_url
                }
                for invoice in invoices.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur récupération factures: {str(e)}")
            return []
    
    def create_portal_session(self, customer_id: str, return_url: str) -> Optional[str]:
        """Créer une session du portail client"""
        if not self.enabled:
            return None
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur création portail client: {str(e)}")
            return None

# Instance globale
stripe_manager = StripeManager()

# Plans tarifaires prédéfinis
PRICING_PLANS = {
    'starter': {
        'name': 'Starter',
        'price_monthly': 2900,  # 29€ en centimes
        'price_yearly': 29000,  # 290€ en centimes (2 mois gratuits)
        'features': [
            'Jusqu\'à 100 clients',
            'Génération de campagnes IA',
            'Analyses de base',
            'Support email'
        ],
        'stripe_price_id_monthly': 'price_starter_monthly',
        'stripe_price_id_yearly': 'price_starter_yearly'
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 5900,  # 59€
        'price_yearly': 59000,  # 590€
        'features': [
            'Clients illimités',
            'IA avancée',
            'Analyses détaillées',
            'Intégrations API',
            'Support prioritaire'
        ],
        'stripe_price_id_monthly': 'price_pro_monthly',
        'stripe_price_id_yearly': 'price_pro_yearly'
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': 19900,  # 199€
        'price_yearly': 199000,  # 1990€
        'features': [
            'Tout Professional',
            'Équipes multiples',
            'White-label',
            'API personnalisée',
            'Support dédié'
        ],
        'stripe_price_id_monthly': 'price_enterprise_monthly',
        'stripe_price_id_yearly': 'price_enterprise_yearly'
    }
}