"""
Script de migration pour ajouter les modèles de paiement à la base de données
"""
from app import app, db, logger
from models_payments import PricingPlan, Subscription, Payment
from payment_controller import DEFAULT_PLANS

def run_migration():
    """Execute the database migration to add payment models"""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Initialize pricing plans if they don't exist
        if PricingPlan.query.count() == 0:
            logger.info("Initializing pricing plans")
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
            logger.info(f"Added {len(DEFAULT_PLANS)} pricing plans")
        else:
            logger.info("Pricing plans already exist, skipping initialization")
        
        logger.info("Payment models migration completed successfully")

if __name__ == "__main__":
    run_migration()