"""
Script de migration pour ajouter les tables de personas client
"""
import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Créer une mini-application Flask pour la migration
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

def run_migration():
    """Execute the database migration to add persona tables"""
    from sqlalchemy.schema import CreateTable
    
    with app.app_context():
        # Vérifier si la table existe déjà pour éviter les erreurs
        import sqlalchemy as sa
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        
        # Définir le modèle CustomerPersona
        class CustomerPersona(db.Model):
            """Model for storing detailed customer personas"""
            id = db.Column(db.Integer, primary_key=True)
            title = db.Column(db.String(100), nullable=False)  # Titre du persona (ex: "Jeune maman urbaine")
            description = db.Column(db.Text, nullable=False)  # Description complète du persona
            primary_goal = db.Column(db.String(255), nullable=True)  # Objectif principal du persona
            pain_points = db.Column(db.Text, nullable=True)  # Points de douleur/frustrations
            buying_triggers = db.Column(db.Text, nullable=True)  # Déclencheurs d'achat
            
            # Caractéristiques démographiques
            age_range = db.Column(db.String(50), nullable=True)  # Tranche d'âge (ex: "25-34")
            gender_affinity = db.Column(db.String(50), nullable=True)  # Affinité de genre
            location_type = db.Column(db.String(50), nullable=True)  # Type de localisation (urbain, rural, etc.)
            income_bracket = db.Column(db.String(50), nullable=True)  # Tranche de revenus
            education_level = db.Column(db.String(50), nullable=True)  # Niveau d'éducation
            
            # Caractéristiques psychographiques
            values = db.Column(JSONB, nullable=True)  # Valeurs importantes
            interests = db.Column(JSONB, nullable=True)  # Centres d'intérêt
            lifestyle = db.Column(db.Text, nullable=True)  # Style de vie
            personality_traits = db.Column(JSONB, nullable=True)  # Traits de personnalité
            
            # Comportements de consommation
            buying_habits = db.Column(db.Text, nullable=True)  # Habitudes d'achat
            brand_affinities = db.Column(JSONB, nullable=True)  # Affinités de marque
            price_sensitivity = db.Column(db.String(50), nullable=True)  # Sensibilité aux prix
            decision_factors = db.Column(JSONB, nullable=True)  # Facteurs de décision d'achat
            
            # Communication et médias
            preferred_channels = db.Column(JSONB, nullable=True)  # Canaux de communication préférés
            content_preferences = db.Column(db.Text, nullable=True)  # Préférences de contenu
            social_media_behavior = db.Column(JSONB, nullable=True)  # Comportement sur les réseaux sociaux
            
            # Attributs spécifiques à la niche
            niche_specific_attributes = db.Column(JSONB, nullable=True)  # Attributs spécifiques à la niche
            custom_fields = db.Column(JSONB, nullable=True)  # Champs personnalisés pour flexibilité
            
            # Avatar et représentation visuelle
            avatar_url = db.Column(db.Text, nullable=True)  # URL de l'avatar
            avatar_prompt = db.Column(db.Text, nullable=True)  # Prompt utilisé pour générer l'avatar
            
            # Métadonnées
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            
            # Foreign keys
            niche_market_id = db.Column(db.Integer, db.ForeignKey('niche_market.id'), nullable=True)
            boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
            
            def __repr__(self):
                return f'<CustomerPersona {self.title}>'
        
        # Définir le modèle CustomerPersonaAssociation
        class CustomerPersonaAssociation(db.Model):
            """Association table between Customers and CustomerPersonas"""
            id = db.Column(db.Integer, primary_key=True)
            customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
            persona_id = db.Column(db.Integer, db.ForeignKey('customer_persona.id'), nullable=False)
            relevance_score = db.Column(db.Float, nullable=True)  # Score de pertinence (0-1)
            is_primary = db.Column(db.Boolean, default=False)  # Indique si c'est le persona principal du client
            notes = db.Column(db.Text, nullable=True)  # Notes sur l'association
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            
            def __repr__(self):
                return f'<CustomerPersonaAssociation {self.customer_id}-{self.persona_id}>'
        
        # Vérifier et créer les tables
        if 'customer_persona' not in inspector.get_table_names():
            print("Création de la table customer_persona...")
            db.create_all(tables=[CustomerPersona.__table__])
            print("La table customer_persona a été créée avec succès.")
        else:
            print("La table customer_persona existe déjà.")
            
        if 'customer_persona_association' not in inspector.get_table_names():
            print("Création de la table customer_persona_association...")
            db.create_all(tables=[CustomerPersonaAssociation.__table__])
            print("La table customer_persona_association a été créée avec succès.")
        else:
            print("La table customer_persona_association existe déjà.")
            
        # Créer l'index pour améliorer les performances des requêtes
        try:
            if 'customer_persona_association' in inspector.get_table_names():
                with db.engine.connect() as conn:
                    conn.execute(sa.text('CREATE INDEX IF NOT EXISTS idx_customer_persona_assoc_customer ON customer_persona_association (customer_id)'))
                    conn.execute(sa.text('CREATE INDEX IF NOT EXISTS idx_customer_persona_assoc_persona ON customer_persona_association (persona_id)'))
                    conn.commit()
                print("Les index ont été créés avec succès.")
        except Exception as e:
            print(f"Erreur lors de la création des index: {e}")
        
        print("Migration terminée avec succès.")

if __name__ == "__main__":
    run_migration()