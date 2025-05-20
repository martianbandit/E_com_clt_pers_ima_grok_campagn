"""
Models for payment processing with Stripe integration
"""
from datetime import datetime
from app import db
from flask_login import current_user

class PricingPlan(db.Model):
    """Model for subscription pricing plans"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_monthly = db.Column(db.Float, nullable=False)
    price_annually = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="EUR", nullable=False)
    stripe_price_id_monthly = db.Column(db.String(100), nullable=True)
    stripe_price_id_annually = db.Column(db.String(100), nullable=True)
    stripe_product_id = db.Column(db.String(100), nullable=True)
    features = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PricingPlan {self.name} - {self.price_monthly}€/month>'


class Subscription(db.Model):
    """Model for user subscriptions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plan.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='inactive', nullable=False)  # active, inactive, cancelled, trial
    billing_period = db.Column(db.String(10), nullable=False)  # monthly, annually
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    trial_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    plan = db.relationship('PricingPlan', backref=db.backref('subscriptions', lazy=True))

    def __repr__(self):
        return f'<Subscription {self.user_id} - {self.plan.name if self.plan else "Unknown Plan"}>'

    @classmethod
    def get_active_subscription(cls, user_id):
        """Get the active subscription for a user"""
        return cls.query.filter_by(
            user_id=user_id,
            status='active'
        ).first()


class Payment(db.Model):
    """Model for payment records"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    stripe_invoice_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="EUR", nullable=False)
    status = db.Column(db.String(20), nullable=False)  # succeeded, pending, failed
    payment_method = db.Column(db.String(50), nullable=True)  # credit_card, bank_transfer
    invoice_url = db.Column(db.String(255), nullable=True)
    receipt_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    subscription = db.relationship('Subscription', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<Payment {self.id} - {self.amount}{self.currency} - {self.status}>'


class Product(db.Model):
    """Model for one-time purchase products"""
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="EUR", nullable=False)
    stripe_price_id = db.Column(db.String(100), nullable=True)
    stripe_product_id = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.name} - {self.price}{self.currency}>'