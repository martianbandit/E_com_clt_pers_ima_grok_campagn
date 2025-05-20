import os
import stripe
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_required, current_user
from app import db, logger
from models_payments import PricingPlan, Subscription, Payment

# Initialize Stripe with the API key from environment
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Create Blueprint for payment routes
payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

# Define pricing plans
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
        'stripe_price_id_monthly': 'price_starter_monthly',
        'stripe_price_id_annually': 'price_starter_annually',
        'stripe_product_id': 'prod_starter'
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
        'stripe_price_id_monthly': 'price_pro_monthly',
        'stripe_price_id_annually': 'price_pro_annually',
        'stripe_product_id': 'prod_pro'
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
        'stripe_price_id_monthly': 'price_business_monthly',
        'stripe_price_id_annually': 'price_business_annually',
        'stripe_product_id': 'prod_business'
    }
]

# Create sample in-app products
INAPP_PRODUCTS = [
    {
        'id': 'additional_campaign',
        'name': 'Campagne supplémentaire',
        'description': 'Ajoutez une campagne supplémentaire à votre forfait',
        'price': 9.99,
        'stripe_price_id': 'price_additional_campaign',
        'stripe_product_id': 'prod_additional_campaign'
    },
    {
        'id': 'additional_boutique',
        'name': 'Boutique supplémentaire',
        'description': 'Ajoutez une boutique supplémentaire à votre forfait',
        'price': 19.99,
        'stripe_price_id': 'price_additional_boutique',
        'stripe_product_id': 'prod_additional_boutique'
    },
    {
        'id': 'premium_analysis',
        'name': 'Analyse premium',
        'description': 'Analyse avancée de marché pour une campagne',
        'price': 29.99,
        'stripe_price_id': 'price_premium_analysis',
        'stripe_product_id': 'prod_premium_analysis'
    },
    {
        'id': 'export_shopify',
        'name': 'Export Shopify Pro',
        'description': 'Exportation avancée pour Shopify avec optimisations',
        'price': 14.99,
        'stripe_price_id': 'price_export_shopify',
        'stripe_product_id': 'prod_export_shopify'
    }
]


def init_plans():
    """Initialize pricing plans in the database if they don't exist"""
    if PricingPlan.query.count() == 0:
        for plan_data in DEFAULT_PLANS:
            plan = PricingPlan(
                name=plan_data['name'],
                description=plan_data['description'],
                price_monthly=plan_data['price_monthly'],
                price_annually=plan_data['price_annually'],
                features=plan_data['features'],
                stripe_price_id_monthly=plan_data['stripe_price_id_monthly'],
                stripe_price_id_annually=plan_data['stripe_price_id_annually'],
                stripe_product_id=plan_data['stripe_product_id'],
                is_active=True
            )
            db.session.add(plan)
        db.session.commit()
        logger.info("Pricing plans initialized")


def get_domain_url():
    """Get the domain URL for Stripe redirects"""
    if os.environ.get('REPLIT_DEPLOYMENT') != '':
        return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
    else:
        return f"https://{os.environ.get('REPLIT_DOMAINS').split(',')[0]}"


@payment_bp.route('/pricing')
def pricing():
    """Show pricing plans page"""
    plans = PricingPlan.query.filter_by(is_active=True).all()
    
    # Check if user has an active subscription
    active_subscription = None
    if current_user.is_authenticated:
        active_subscription = Subscription.get_active_subscription(current_user.id)
    
    return render_template(
        'payment/pricing.html',
        plans=plans,
        inapp_products=INAPP_PRODUCTS,
        active_subscription=active_subscription
    )


@payment_bp.route('/checkout/<int:plan_id>/<billing_period>')
@login_required
def checkout(plan_id, billing_period):
    """Create a Stripe checkout session and redirect to Stripe"""
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
        return redirect(url_for('payment.pricing'))
    
    # Create subscription in our database first (pending status)
    subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status='pending',
        billing_period=billing_period
    )
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
            success_url=domain_url + url_for('payment.success', session_id='{CHECKOUT_SESSION_ID}'),
            cancel_url=domain_url + url_for('payment.cancel'),
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
        return redirect(url_for('payment.pricing'))


@payment_bp.route('/one-time-purchase/<product_id>')
@login_required
def one_time_purchase(product_id):
    """Create a one-time purchase checkout for in-app products"""
    # Find the product in our list
    product = next((p for p in INAPP_PRODUCTS if p['id'] == product_id), None)
    
    if not product:
        flash('Produit non trouvé', 'danger')
        return redirect(url_for('payment.pricing'))
    
    try:
        # Create Stripe checkout session
        domain_url = get_domain_url()
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': product['stripe_price_id'],
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=domain_url + url_for('payment.success_one_time', session_id='{CHECKOUT_SESSION_ID}'),
            cancel_url=domain_url + url_for('payment.cancel'),
            metadata={
                'user_id': current_user.id,
                'product_id': product_id,
                'product_name': product['name']
            }
        )
        
        # Create pending payment in database
        payment = Payment(
            user_id=current_user.id,
            stripe_payment_intent_id=checkout_session.id,
            amount=product['price'],
            currency='EUR',
            status='pending',
            payment_method='credit_card'
        )
        db.session.add(payment)
        db.session.commit()
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating one-time checkout: {str(e)}")
        flash('Une erreur est survenue lors de la création de la session de paiement.', 'danger')
        return redirect(url_for('payment.pricing'))


@payment_bp.route('/success')
@login_required
def success():
    """Handle successful subscription payment"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Session ID manquant', 'warning')
        return redirect(url_for('payment.pricing'))
    
    try:
        # Retrieve checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = checkout_session.metadata.get('subscription_id')
        
        if not subscription_id:
            flash('ID de souscription manquant', 'warning')
            return redirect(url_for('payment.pricing'))
        
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
        
        return redirect(url_for('payment.subscription_details'))
    
    except Exception as e:
        logger.error(f"Error processing successful subscription: {str(e)}")
        flash('Une erreur est survenue lors du traitement de votre paiement.', 'danger')
        return redirect(url_for('payment.pricing'))


@payment_bp.route('/success-one-time')
@login_required
def success_one_time():
    """Handle successful one-time payment"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Session ID manquant', 'warning')
        return redirect(url_for('payment.pricing'))
    
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
            product_id = checkout_session.metadata.get('product_id')
            if product_id:
                # Here you would implement the logic to apply the purchased benefit
                # For example, increase campaign limit, add boutique, etc.
                pass
            
            flash('Merci pour votre achat! Votre compte a été mis à jour.', 'success')
        else:
            flash('Paiement non trouvé', 'warning')
        
        return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Error processing successful one-time payment: {str(e)}")
        flash('Une erreur est survenue lors du traitement de votre paiement.', 'danger')
        return redirect(url_for('payment.pricing'))


@payment_bp.route('/cancel')
@login_required
def cancel():
    """Handle cancelled checkout"""
    flash('Paiement annulé', 'info')
    return redirect(url_for('payment.pricing'))


@payment_bp.route('/subscription')
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


@payment_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel subscription"""
    active_subscription = Subscription.get_active_subscription(current_user.id)
    
    if not active_subscription:
        flash('Aucun abonnement actif trouvé', 'warning')
        return redirect(url_for('payment.subscription_details'))
    
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
    
    return redirect(url_for('payment.subscription_details'))