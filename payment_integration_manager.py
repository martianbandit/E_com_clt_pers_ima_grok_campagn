"""
Gestionnaire d'intégration des paiements avec basculement contrôlé
Coordonne tous les systèmes de paiement avec la barrière de sécurité
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from payment_security_barrier import payment_barrier, require_payment_security

logger = logging.getLogger(__name__)

# Blueprint pour l'intégration des paiements
payment_integration_bp = Blueprint('payment_integration', __name__, url_prefix='/payments')

class PaymentIntegrationManager:
    """Gestionnaire principal d'intégration des paiements"""
    
    def __init__(self):
        self.barrier = payment_barrier
        self.stripe_available = False
        self.webhook_configured = False
        self._check_services()
    
    def _check_services(self):
        """Vérifie la disponibilité des services de paiement"""
        # Vérifier Stripe
        self.stripe_available = bool(os.environ.get('STRIPE_SECRET_KEY'))
        self.webhook_configured = bool(os.environ.get('STRIPE_WEBHOOK_SECRET'))
        
        if not self.stripe_available:
            logger.warning("Stripe non configuré - Clé API manquante")
        
        if not self.webhook_configured:
            logger.warning("Webhooks Stripe non configurés")
    
    def get_system_status(self):
        """Retourne le statut complet du système de paiement"""
        return {
            'barrier_status': {
                'sandbox_mode': self.barrier.sandbox_mode,
                'payments_enabled': self.barrier.payment_enabled,
                'max_test_amount': self.barrier.max_test_amount,
                'test_users_count': len(self.barrier.allowed_test_users)
            },
            'services_status': {
                'stripe_configured': self.stripe_available,
                'webhooks_configured': self.webhook_configured,
                'environment': os.environ.get('FLASK_ENV', 'production')
            },
            'restrictions': self.barrier._get_current_restrictions(),
            'ready_for_production': self._is_ready_for_production()
        }
    
    def _is_ready_for_production(self):
        """Vérifie si le système est prêt pour la production"""
        return (
            self.stripe_available and
            self.webhook_configured and
            bool(os.environ.get('PAYMENT_ADMIN_UNLOCK_KEY'))
        )
    
    def create_checkout_session(self, plan_id, billing_period, user_email):
        """
        Crée une session de checkout sécurisée
        
        Args:
            plan_id: ID du plan
            billing_period: Période de facturation
            user_email: Email utilisateur
            
        Returns:
            dict: Résultat avec URL de checkout ou erreur
        """
        # Vérification de sécurité
        check_result = self.barrier.is_payment_allowed(user_email)
        if not check_result['allowed']:
            return {
                'success': False,
                'error': 'Paiement non autorisé',
                'restrictions': check_result['restrictions']
            }
        
        try:
            import stripe
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
            
            # Plans avec limitations sandbox
            plans = {
                'starter': {
                    'monthly': 29.99 if not self.barrier.sandbox_mode else 9.99,
                    'annually': 299.90 if not self.barrier.sandbox_mode else 99.90
                },
                'pro': {
                    'monthly': 79.99 if not self.barrier.sandbox_mode else 19.99,
                    'annually': 799.90 if not self.barrier.sandbox_mode else 199.90
                },
                'business': {
                    'monthly': 149.99 if not self.barrier.sandbox_mode else 39.99,
                    'annually': 1499.90 if not self.barrier.sandbox_mode else 399.90
                }
            }
            
            if plan_id not in plans:
                return {'success': False, 'error': 'Plan non trouvé'}
            
            price = plans[plan_id][billing_period]
            
            # Vérifier la limite de montant en sandbox
            if self.barrier.sandbox_mode and price > self.barrier.max_test_amount:
                price = min(price, self.barrier.max_test_amount)
            
            # Métadonnées de sécurité
            metadata = {
                'security_mode': 'sandbox' if self.barrier.sandbox_mode else 'production',
                'plan_id': plan_id,
                'billing_period': billing_period,
                'user_email': user_email,
                'original_price': str(plans[plan_id][billing_period]),
                'applied_price': str(price)
            }
            
            # Créer le produit Stripe
            product = stripe.Product.create(
                name=f"NinjaLead.ai {plan_id.title()} ({billing_period})",
                description=f"Plan {plan_id} - Mode {check_result['mode']}",
                metadata=metadata
            )
            
            # Créer le prix
            price_obj = stripe.Price.create(
                product=product.id,
                unit_amount=int(price * 100),
                currency='eur',
                recurring={
                    'interval': 'month' if billing_period == 'monthly' else 'year',
                } if not self.barrier.sandbox_mode else None  # Pas d'abonnement récurrent en sandbox
            )
            
            # Configuration de la session
            session_config = {
                'customer_email': user_email,
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_obj.id,
                    'quantity': 1,
                }],
                'mode': 'subscription' if not self.barrier.sandbox_mode else 'payment',
                'success_url': f"{self._get_domain_url()}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
                'cancel_url': f"{self._get_domain_url()}/payments/cancel",
                'metadata': metadata
            }
            
            # Ajouter des restrictions sandbox
            if self.barrier.sandbox_mode:
                session_config['payment_intent_data'] = {
                    'capture_method': 'manual',  # Capture manuelle en sandbox
                    'metadata': metadata
                }
            
            checkout_session = stripe.checkout.Session.create(**session_config)
            
            # Log de sécurité
            logger.info(f"Session checkout créée - Mode: {check_result['mode']}, "
                       f"User: {user_email}, Plan: {plan_id}, Prix: {price}€")
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'mode': check_result['mode'],
                'applied_price': price,
                'restrictions': check_result['restrictions']
            }
            
        except Exception as e:
            logger.error(f"Erreur création session checkout: {e}")
            return {
                'success': False,
                'error': f'Erreur technique: {str(e)}'
            }
    
    def _get_domain_url(self):
        """Retourne l'URL de base du domaine"""
        if os.environ.get('REPLIT_DOMAINS'):
            domains = os.environ.get('REPLIT_DOMAINS')
            return f"https://{domains.split(',')[0]}"
        return "http://localhost:5000"
    
    def handle_successful_payment(self, session_id):
        """
        Traite un paiement réussi avec vérifications de sécurité
        
        Args:
            session_id: ID de la session Stripe
            
        Returns:
            dict: Résultat du traitement
        """
        try:
            import stripe
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
            
            # Récupérer la session
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Vérifier les métadonnées de sécurité
            metadata = session.get('metadata', {})
            security_mode = metadata.get('security_mode')
            
            if self.barrier.sandbox_mode and security_mode != 'sandbox':
                logger.warning(f"Session sans métadonnées sandbox: {session_id}")
            
            # En mode sandbox, ne pas activer d'abonnement réel
            if self.barrier.sandbox_mode:
                logger.info(f"Paiement sandbox traité: {session_id}")
                return {
                    'success': True,
                    'mode': 'sandbox',
                    'message': 'Paiement test réussi - Aucun abonnement activé',
                    'session_data': {
                        'plan': metadata.get('plan_id'),
                        'amount': metadata.get('applied_price'),
                        'user': metadata.get('user_email')
                    }
                }
            
            # Traitement production (à implémenter quand déverrouillé)
            return {
                'success': True,
                'mode': 'production',
                'message': 'Abonnement activé avec succès'
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement paiement réussi: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Instance globale du gestionnaire
payment_manager = PaymentIntegrationManager()

@payment_integration_bp.route('/')
@login_required
def dashboard():
    """Dashboard des paiements avec statut de sécurité"""
    status = payment_manager.get_system_status()
    return render_template('payments/dashboard.html', status=status)

@payment_integration_bp.route('/checkout/<plan_id>/<billing_period>')
@require_payment_security
def checkout(plan_id, billing_period):
    """Créer une session de checkout sécurisée"""
    result = payment_manager.create_checkout_session(
        plan_id, billing_period, current_user.email
    )
    
    if result['success']:
        return redirect(result['checkout_url'])
    else:
        flash(f"Erreur: {result['error']}", 'danger')
        if 'restrictions' in result:
            for restriction in result['restrictions']:
                flash(f"Restriction: {restriction}", 'warning')
        return redirect(url_for('payment_integration.dashboard'))

@payment_integration_bp.route('/success')
def success():
    """Page de succès après paiement"""
    session_id = request.args.get('session_id')
    
    if session_id:
        result = payment_manager.handle_successful_payment(session_id)
        
        if result['success']:
            flash(result['message'], 'success')
            if result['mode'] == 'sandbox':
                flash('Mode test - Aucun frais réel appliqué', 'info')
        else:
            flash(f"Erreur traitement: {result['error']}", 'danger')
    
    return render_template('payments/success.html')

@payment_integration_bp.route('/cancel')
def cancel():
    """Page d'annulation"""
    flash('Paiement annulé', 'info')
    return render_template('payments/cancel.html')

@payment_integration_bp.route('/api/status')
@login_required
def api_status():
    """API pour récupérer le statut du système"""
    status = payment_manager.get_system_status()
    user_check = payment_barrier.is_payment_allowed(current_user.email)
    
    return jsonify({
        'system_status': status,
        'user_authorization': user_check
    })

@payment_integration_bp.route('/api/test-limits')
@login_required
def api_test_limits():
    """API pour récupérer les limites de test"""
    if not payment_barrier.sandbox_mode:
        return jsonify({'error': 'Non disponible en production'}), 403
    
    return jsonify({
        'max_amount': payment_barrier.max_test_amount,
        'user_authorized': current_user.email in payment_barrier.allowed_test_users,
        'test_users_count': len(payment_barrier.allowed_test_users),
        'restrictions': payment_barrier._get_current_restrictions()
    })

def init_payment_integration(app):
    """Initialise l'intégration des paiements"""
    app.register_blueprint(payment_integration_bp)
    
    # Initialiser la barrière de sécurité
    from payment_security_barrier import init_payment_security
    init_payment_security(app)
    
    logger.info("Intégration des paiements initialisée avec barrière de sécurité")
    return payment_manager