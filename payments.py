"""
Payment processing with Stripe integration
"""
import os
import stripe
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_required, current_user
from app import db, logger
from models_payment import PricingPlan, Subscription, Payment, Product

# Create Blueprint for payment routes
payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

# Default pricing plans
DEFAULT_PLANS = [
    {
        'name': 'Starter',
        'description': 'Pour les petites boutiques qui débutent',
        'price_monthly': 29.99,
        'price_annually': 299.90,
        'features': [
            'Jusqu\'à 3 campagnes',
            '1 boutique',
            '5 profils client',
            'Génération de contenu basique'
        ],
        'stripe_price_id_monthly': 'price_1PK5eGCm3jfTuSFyU9QX1iKH',
        'stripe_price_id_annually': 'price_1PK5e3Cm3jfTuSFygOZmI8iI',
        'stripe_product_id': 'prod_PhzR1JQoQyDuCq'
    },
    {
        'name': 'Pro',
        'description': 'Pour les boutiques en croissance',
        'price_monthly': 79.99,
        'price_annually': 799.90,
        'features': [
            'Jusqu\'à 10 campagnes',
            '3 boutiques',
            '20 profils client',
            'Génération de contenu avancée',
            'Analyse de marché',
            'Support prioritaire'
        ],
        'stripe_price_id_monthly': 'price_1PK5eGCm3jfTuSFywDDQzd9Y',
        'stripe_price_id_annually': 'price_1PK5eGCm3jfTuSFyc5YT1JcR',
        'stripe_product_id': 'prod_PhzRQeZBQEzRt0'
    },
    {
        'name': 'Business',
        'description': 'Pour les entreprises établies',
        'price_monthly': 149.99,
        'price_annually': 1499.90,
        'features': [
            'Campagnes illimitées',
            'Boutiques illimitées',
            'Profils client illimités',
            'Génération de contenu premium',
            'Analyse de marché avancée',
            'Support dédié',
            'API access',
            'Rapports personnalisés'
        ],
        'stripe_price_id_monthly': 'price_1PK5eGCm3jfTuSFyYWMNVlRu',
        'stripe_price_id_annually': 'price_1PK5eGCm3jfTuSFyi18LhHle',
        'stripe_product_id': 'prod_PhzRCTrZpRrPVF'
    }
]

# Default in-app products
DEFAULT_PRODUCTS = [
    {
        'product_code': 'additional_campaign',
        'name': 'Campagne supplémentaire',
        'description': 'Ajoutez une campagne supplémentaire à votre forfait',
        'price': 9.99,
        'stripe_price_id': 'price_1PK5eGCm3jfTuSFydZcBCjFi',
        'stripe_product_id': 'prod_PhzRGfwRqCUFFN'
    },
    {
        'product_code': 'additional_boutique',
        'name': 'Boutique supplémentaire',
        'description': 'Ajoutez une boutique supplémentaire à votre forfait',
        'price': 19.99,
        'stripe_price_id': 'price_1PK5eGCm3jfTuSFybhqnpfxT',
        'stripe_product_id': 'prod_PhzRXS23WnFDxI'
    },
    {
        'product_code': 'premium_analysis',
        'name': 'Analyse premium',
        'description': 'Analyse avancée de marché pour une campagne',
        'price': 29.99,
        'stripe_price_id': 'price_1PK5eGCm3jfTuSFyKQI3MGAx',
        'stripe_product_id': 'prod_PhzRvPkdXE0r6I'
    },
    {
        'product_code': 'export_shopify',
        'name': 'Export Shopify Pro',
        'description': 'Exportation avancée pour Shopify avec optimisations',
        'price': 14.99,
        'stripe_price_id': 'price_1PK5eGCm3jfTuSFyxsUDuB5a',
        'stripe_product_id': 'prod_PhzRQyPE2mEm7I'
    }
]


def init_plans_and_products():
    """Initialize pricing plans and products in the database if they don't exist"""
    # Initialize pricing plans
    if PricingPlan.query.count() == 0:
        for plan_data in DEFAULT_PLANS:
            plan = PricingPlan()
            plan.name = plan_data['name']
            plan.description = plan_data['description']
            plan.price_monthly = plan_data['price_monthly']
            plan.price_annually = plan_data['price_annually']
            plan.features = plan_data['features']
            plan.stripe_price_id_monthly = plan_data['stripe_price_id_monthly']
            plan.stripe_price_id_annually = plan_data['stripe_price_id_annually']
            plan.stripe_product_id = plan_data['stripe_product_id']
            plan.is_active = True
            db.session.add(plan)
        db.session.commit()
        logger.info("Initialized pricing plans")
    
    # Initialize products
    if Product.query.count() == 0:
        for product_data in DEFAULT_PRODUCTS:
            product = Product()
            product.product_code = product_data['product_code']
            product.name = product_data['name']
            product.description = product_data['description']
            product.price = product_data['price']
            product.stripe_price_id = product_data['stripe_price_id']
            product.stripe_product_id = product_data['stripe_product_id']
            product.is_active = True
            db.session.add(product)
        db.session.commit()
        logger.info("Initialized products")


def get_domain_url():
    """Get the domain URL for Stripe redirects"""
    if os.environ.get('REPLIT_DEPLOYMENT'):
        return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
    elif os.environ.get('REPLIT_DOMAINS'):
        return f"https://{os.environ.get('REPLIT_DOMAINS').split(',')[0]}"
    else:
        return "http://localhost:5000"


@payments_bp.route('/pricing')
def pricing():
    """Show pricing plans page"""
    plans = PricingPlan.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    
    # Check if user has an active subscription
    active_subscription = None
    if current_user.is_authenticated:
        active_subscription = Subscription.get_active_subscription(current_user.id)
    
    return render_template(
        'payment/pricing.html',
        plans=plans,
        products=products,
        active_subscription=active_subscription
    )


@payments_bp.route('/checkout/<int:plan_id>/<billing_period>')
@login_required
def checkout(plan_id, billing_period):
    """Create a Stripe checkout session and redirect to Stripe"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    plan = PricingPlan.query.get_or_404(plan_id)
    
    # Determine price ID based on billing period
    if billing_period == 'monthly':
        price_id = plan.stripe_price_id_monthly
        amount = plan.price_monthly
    elif billing_period == 'annually':
        price_id = plan.stripe_price_id_annually
        amount = plan.price_annually
    else:
        flash('Période de facturation invalide', 'danger')
        return redirect(url_for('payments.pricing'))
    
    # Create subscription in our database first (pending status)
    subscription = Subscription()
    subscription.user_id = current_user.id
    subscription.plan_id = plan.id
    subscription.status = 'pending'
    subscription.billing_period = billing_period
    db.session.add(subscription)
    db.session.flush()  # Get ID without committing
    
    try:
        # Create Stripe checkout session
        domain_url = get_domain_url()
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=domain_url + url_for('payments.success', session_id='{CHECKOUT_SESSION_ID}'),
            cancel_url=domain_url + url_for('payments.cancel'),
            metadata={
                'subscription_id': subscription.id,
                'user_id': current_user.id,
                'plan_id': plan.id,
                'billing_period': billing_period
            }
        )
        
        # Save checkout session ID to subscription
        subscription.stripe_subscription_id = checkout_session.id
        db.session.commit()
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        db.session.rollback()
        flash('Une erreur est survenue lors de la création de la session de paiement.', 'danger')
        return redirect(url_for('payments.pricing'))


@payments_bp.route('/one-time-purchase/<product_code>')
@login_required
def one_time_purchase(product_code):
    """Create a one-time purchase checkout for in-app products"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Find the product in our database
    product = Product.query.filter_by(product_code=product_code, is_active=True).first_or_404()
    
    try:
        # Create Stripe checkout session
        domain_url = get_domain_url()
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': product.stripe_price_id,
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=domain_url + url_for('payments.success_one_time', session_id='{CHECKOUT_SESSION_ID}'),
            cancel_url=domain_url + url_for('payments.cancel'),
            metadata={
                'user_id': current_user.id,
                'product_code': product_code,
                'product_name': product.name
            }
        )
        
        # Create pending payment in database
        payment = Payment()
        payment.user_id = current_user.id
        payment.stripe_payment_intent_id = checkout_session.id
        payment.amount = product.price
        payment.currency = 'EUR'
        payment.status = 'pending'
        payment.payment_method = 'credit_card'
        db.session.add(payment)
        db.session.commit()
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating one-time checkout: {str(e)}")
        flash('Une erreur est survenue lors de la création de la session de paiement.', 'danger')
        return redirect(url_for('payments.pricing'))


@payments_bp.route('/success')
@login_required
def success():
    """Handle successful subscription payment"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Session ID manquant', 'warning')
        return redirect(url_for('payments.pricing'))
    
    try:
        # Retrieve checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = checkout_session.metadata.get('subscription_id')
        
        if not subscription_id:
            flash('ID de souscription manquant', 'warning')
            return redirect(url_for('payments.pricing'))
        
        # Update subscription in database
        subscription = Subscription.query.get(subscription_id)
        if subscription:
            subscription.status = 'active'
            subscription.stripe_subscription_id = checkout_session.subscription
            subscription.stripe_customer_id = checkout_session.customer
            subscription.start_date = datetime.utcnow()
            
            # Set end date based on billing period
            if subscription.billing_period == 'monthly':
                subscription.end_date = subscription.start_date + timedelta(days=30)
            else:
                subscription.end_date = subscription.start_date + timedelta(days=365)
            
            db.session.commit()
            
            flash('Merci pour votre abonnement! Votre compte a été mis à jour.', 'success')
        else:
            flash('Abonnement non trouvé', 'warning')
        
        return redirect(url_for('payments.subscription_details'))
    
    except Exception as e:
        logger.error(f"Error processing successful subscription: {str(e)}")
        flash('Une erreur est survenue lors du traitement de votre paiement.', 'danger')
        return redirect(url_for('payments.pricing'))


@payments_bp.route('/success-one-time')
@login_required
def success_one_time():
    """Handle successful one-time payment"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Session ID manquant', 'warning')
        return redirect(url_for('payments.pricing'))
    
    try:
        # Retrieve checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Update payment record in database
        payment = Payment.query.filter_by(stripe_payment_intent_id=session_id).first()
        if payment:
            payment.status = 'succeeded'
            payment.receipt_url = checkout_session.get('receipt_url')
            db.session.commit()
            
            # Apply the purchased benefit to the user's account
            product_code = checkout_session.metadata.get('product_code')
            if product_code:
                # Here you would implement the logic to apply the purchased benefit
                # For example, increase campaign limit, add boutique, etc.
                logger.info(f"User {current_user.id} purchased product {product_code}")
            
            flash('Merci pour votre achat! Votre compte a été mis à jour.', 'success')
        else:
            flash('Paiement non trouvé', 'warning')
        
        return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Error processing successful one-time payment: {str(e)}")
        flash('Une erreur est survenue lors du traitement de votre paiement.', 'danger')
        return redirect(url_for('payments.pricing'))


@payments_bp.route('/cancel')
@login_required
def cancel():
    """Handle cancelled checkout"""
    flash('Paiement annulé', 'info')
    return redirect(url_for('payments.pricing'))


@payments_bp.route('/subscription')
@login_required
def subscription_details():
    """Show subscription details page"""
    # Get active subscription
    active_subscription = Subscription.get_active_subscription(current_user.id)
    
    # Get payment history
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    
    return render_template(
        'payment/subscription.html',
        subscription=active_subscription,
        payments=payments
    )


@payments_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel subscription"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    active_subscription = Subscription.get_active_subscription(current_user.id)
    
    if not active_subscription:
        flash('Aucun abonnement actif trouvé', 'warning')
        return redirect(url_for('payments.subscription_details'))
    
    try:
        # Cancel subscription in Stripe
        if active_subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                active_subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
        
        # Update our database
        active_subscription.cancel_at_period_end = True
        db.session.commit()
        
        flash('Votre abonnement sera annulé à la fin de la période en cours', 'info')
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        flash('Une erreur est survenue lors de l\'annulation de votre abonnement', 'danger')
    
    return redirect(url_for('payments.subscription_details'))


@payments_bp.route('/landing')
def landing():
    """Show pricing landing page with subscription options"""
    plans = PricingPlan.query.filter_by(is_active=True).all()
    
    # Check for active subscription if user is authenticated
    active_subscription = None
    if current_user.is_authenticated:
        active_subscription = Subscription.get_active_subscription(current_user.id)
    
    return render_template('payment/landing.html', plans=plans, active_subscription=active_subscription)