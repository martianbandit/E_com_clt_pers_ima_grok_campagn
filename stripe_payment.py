"""
Payment processing with Stripe integration for MarkEasy
"""
import os
import stripe
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app import db, logger
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

# Create Blueprint for payment routes
stripe_bp = Blueprint('stripe', __name__, url_prefix='/stripe')

# Plans configuration
PLANS = [
    {
        'id': 'starter',
        'name': 'Starter',
        'description': 'Pour les petites boutiques qui débutent',
        'price_monthly': 29.99,
        'price_annually': 299.90,
        'features': [
            'Jusqu\'à 3 campagnes',
            '1 boutique',
            '5 profils client',
            'Génération de contenu basique'
        ]
    },
    {
        'id': 'pro',
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
        ]
    },
    {
        'id': 'business',
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
        ]
    }
]

# In-app products configuration
PRODUCTS = [
    {
        'id': 'additional_campaign',
        'name': 'Campagne supplémentaire',
        'description': 'Ajoutez une campagne supplémentaire à votre forfait',
        'price': 9.99
    },
    {
        'id': 'additional_boutique',
        'name': 'Boutique supplémentaire',
        'description': 'Ajoutez une boutique supplémentaire à votre forfait',
        'price': 19.99
    },
    {
        'id': 'premium_analysis',
        'name': 'Analyse premium',
        'description': 'Analyse avancée de marché pour une campagne',
        'price': 29.99
    },
    {
        'id': 'export_shopify',
        'name': 'Export Shopify Pro',
        'description': 'Exportation avancée pour Shopify avec optimisations',
        'price': 14.99
    }
]

def get_domain_url():
    """Get the domain URL for Stripe redirects"""
    if os.environ.get('REPLIT_DEPLOYMENT'):
        return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
    elif os.environ.get('REPLIT_DOMAINS'):
        domains = os.environ.get('REPLIT_DOMAINS')
        if domains:
            return f"https://{domains.split(',')[0]}"
    return "http://localhost:5000"

@stripe_bp.route('/')
def index():
    """Landing page with pricing plans"""
    return render_template('stripe/landing.html', plans=PLANS, products=PRODUCTS)

@stripe_bp.route('/pricing')
def pricing():
    """Show pricing plans page"""
    return render_template('stripe/pricing.html', plans=PLANS, products=PRODUCTS)

@stripe_bp.route('/checkout/<plan_id>/<billing_period>')
@login_required
def checkout(plan_id, billing_period):
    """Create a Stripe checkout session and redirect to Stripe"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Find the plan
    plan = next((p for p in PLANS if p['id'] == plan_id), None)
    if not plan:
        flash('Plan non trouvé', 'danger')
        return redirect(url_for('stripe.pricing'))
    
    # Determine price based on billing period
    if billing_period == 'monthly':
        price = plan['price_monthly']
        interval = 'month'
    elif billing_period == 'annually':
        price = plan['price_annually']
        interval = 'year'
    else:
        flash('Période de facturation invalide', 'danger')
        return redirect(url_for('stripe.pricing'))
    
    try:
        # Create a product and price in Stripe
        product = stripe.Product.create(
            name=f"{plan['name']} Plan ({billing_period})",
            description=plan['description']
        )
        
        price_obj = stripe.Price.create(
            product=product.id,
            unit_amount=int(price * 100),  # Convert to cents
            currency='eur',
            recurring={
                'interval': interval,
            }
        )
        
        # Create checkout session
        domain_url = get_domain_url()
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_obj.id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=domain_url + url_for('stripe.success'),
            cancel_url=domain_url + url_for('stripe.cancel'),
            metadata={
                'user_id': current_user.id,
                'plan_id': plan_id,
                'billing_period': billing_period
            }
        )
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        flash('Une erreur est survenue lors de la création de la session de paiement.', 'danger')
        return redirect(url_for('stripe.pricing'))

@stripe_bp.route('/one-time/<product_id>')
@login_required
def one_time_purchase(product_id):
    """Create a one-time purchase checkout"""
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Find the product
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        flash('Produit non trouvé', 'danger')
        return redirect(url_for('stripe.pricing'))
    
    try:
        # Create a product and price in Stripe
        stripe_product = stripe.Product.create(
            name=product['name'],
            description=product['description']
        )
        
        price = stripe.Price.create(
            product=stripe_product.id,
            unit_amount=int(product['price'] * 100),  # Convert to cents
            currency='eur'
        )
        
        # Create checkout session
        domain_url = get_domain_url()
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price.id,
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=domain_url + url_for('stripe.success'),
            cancel_url=domain_url + url_for('stripe.cancel'),
            metadata={
                'user_id': current_user.id,
                'product_id': product_id
            }
        )
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating one-time checkout: {str(e)}")
        flash('Une erreur est survenue lors de la création de la session de paiement.', 'danger')
        return redirect(url_for('stripe.pricing'))

@stripe_bp.route('/success')
def success():
    """Payment success page"""
    flash('Votre paiement a été traité avec succès!', 'success')
    return render_template('stripe/success.html')

@stripe_bp.route('/cancel')
def cancel():
    """Payment canceled page"""
    flash('Le paiement a été annulé.', 'info')
    return render_template('stripe/cancel.html')

@stripe_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    # Initialize Stripe with the API key
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        else:
            # No webhook secret, so just parse the payload
            data = json.loads(payload)
            event = stripe.Event.construct_from(data, stripe.api_key)
        
        # Handle the event
        if event.type == 'checkout.session.completed':
            session = event.data.object
            fulfill_order(session)
        elif event.type == 'customer.subscription.updated':
            subscription = event.data.object
            update_subscription(subscription)
        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            cancel_subscription(subscription)
        
        return jsonify(success=True)
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return jsonify(success=False, error=str(e)), 400

def fulfill_order(session):
    """Fulfill the order after successful payment"""
    user_id = session.get('metadata', {}).get('user_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    product_id = session.get('metadata', {}).get('product_id')
    
    if user_id:
        logger.info(f"Fulfilling order for user {user_id}")
        
        if plan_id:
            logger.info(f"User {user_id} subscribed to plan {plan_id}")
            # Here you would update the user's subscription status in your database
        
        if product_id:
            logger.info(f"User {user_id} purchased product {product_id}")
            # Here you would apply the one-time purchase benefits to the user
    
    else:
        logger.warning("No user_id in session metadata")

def update_subscription(subscription):
    """Update user subscription in database"""
    logger.info(f"Updating subscription {subscription.id}")
    # Here you would update the subscription status in your database

def cancel_subscription(subscription):
    """Cancel user subscription in database"""
    logger.info(f"Cancelling subscription {subscription.id}")
    # Here you would update the subscription status in your database