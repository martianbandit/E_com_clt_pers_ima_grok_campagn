from datetime import datetime
import json
from app import db
from sqlalchemy.dialects.postgresql import JSON, JSONB

class Boutique(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_demographic = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    customers = db.relationship('Customer', backref='boutique', lazy=True)
    personas = db.relationship('CustomerPersona', backref='boutique', lazy=True)
    
    def __repr__(self):
        return f'<Boutique {self.name}>'

class NicheMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    key_characteristics = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    customers = db.relationship('Customer', backref='niche_market', lazy=True)
    personas = db.relationship('CustomerPersona', backref='niche_market', lazy=True)
    
    def __repr__(self):
        return f'<NicheMarket {self.name}>'
        
    def get_characteristics_list(self):
        """Return key characteristics as a list"""
        if not self.key_characteristics:
            return []
        return [char.strip() for char in self.key_characteristics.split(',')]

# Table d'association entre Customer et CustomerPersona
class CustomerPersonaAssociation(db.Model):
    """Association table between Customers and CustomerPersonas"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    persona_id = db.Column(db.Integer, db.ForeignKey('customer_persona.id'), nullable=False)
    relevance_score = db.Column(db.Float, nullable=True)  # Score de pertinence (0-1)
    is_primary = db.Column(db.Boolean, default=False)  # Indique si c'est le persona principal du client
    notes = db.Column(db.Text, nullable=True)  # Notes sur l'association
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation avec Customer et CustomerPersona
    customer = db.relationship("Customer", back_populates="persona_associations")
    persona = db.relationship("CustomerPersona", back_populates="customer_associations")
    
    def __repr__(self):
        return f'<CustomerPersonaAssociation {self.customer_id}-{self.persona_id}>'

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
    
    # Relations
    customer_associations = db.relationship("CustomerPersonaAssociation", back_populates="persona")
    customers = db.relationship(
        "Customer",
        secondary="customer_persona_association",
        viewonly=True,
        backref=db.backref("associated_personas", lazy="dynamic")
    )
    
    def __repr__(self):
        return f'<CustomerPersona {self.title}>'
    
    @classmethod
    def create_from_dict(cls, persona_data, niche_market_id=None, boutique_id=None):
        """Create a CustomerPersona instance from dictionary data"""
        return cls(
            title=persona_data.get('title'),
            description=persona_data.get('description'),
            primary_goal=persona_data.get('primary_goal'),
            pain_points=persona_data.get('pain_points'),
            buying_triggers=persona_data.get('buying_triggers'),
            age_range=persona_data.get('age_range'),
            gender_affinity=persona_data.get('gender_affinity'),
            location_type=persona_data.get('location_type'),
            income_bracket=persona_data.get('income_bracket'),
            education_level=persona_data.get('education_level'),
            values=persona_data.get('values'),
            interests=persona_data.get('interests'),
            lifestyle=persona_data.get('lifestyle'),
            personality_traits=persona_data.get('personality_traits'),
            buying_habits=persona_data.get('buying_habits'),
            brand_affinities=persona_data.get('brand_affinities'),
            price_sensitivity=persona_data.get('price_sensitivity'),
            decision_factors=persona_data.get('decision_factors'),
            preferred_channels=persona_data.get('preferred_channels'),
            content_preferences=persona_data.get('content_preferences'),
            social_media_behavior=persona_data.get('social_media_behavior'),
            niche_specific_attributes=persona_data.get('niche_specific_attributes'),
            custom_fields=persona_data.get('custom_fields'),
            avatar_url=persona_data.get('avatar_url'),
            avatar_prompt=persona_data.get('avatar_prompt'),
            niche_market_id=niche_market_id,
            boutique_id=boutique_id
        )

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    country_code = db.Column(db.String(2), nullable=True)  # ISO Country code (US, FR, etc.)
    gender = db.Column(db.String(20), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    interests = db.Column(db.Text, nullable=True)  # Stored as comma-separated values
    preferred_device = db.Column(db.String(50), nullable=True)
    income_level = db.Column(db.String(50), nullable=True)  # budget, middle, affluent, luxury
    education = db.Column(db.String(50), nullable=True)  # high school, bachelor, master, etc.
    occupation = db.Column(db.String(100), nullable=True)  # job title or profession
    social_media = db.Column(JSONB, nullable=True)  # Store usage frequency for different platforms
    shopping_frequency = db.Column(db.String(50), nullable=True)  # rarely, occasionally, frequently, very frequently
    persona = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)  # URL de l'image d'avatar générée pour ce client
    avatar_prompt = db.Column(db.Text, nullable=True)  # Prompt utilisé pour générer l'avatar
    purchased_products = db.Column(JSONB, nullable=True)  # Produits déjà achetés par le client
    niche_attributes = db.Column(JSONB, nullable=True)  # Attributs supplémentaires liés à la niche
    profile_data = db.Column(JSONB, nullable=True)  # Store full profile as JSON with better Postgres support
    usage_count = db.Column(db.Integer, default=0)  # Compteur d'utilisation du profil client
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
    niche_market_id = db.Column(db.Integer, db.ForeignKey('niche_market.id'), nullable=True)
    
    # Relations
    campaigns = db.relationship('Campaign', backref='customer', lazy=True)
    persona_associations = db.relationship("CustomerPersonaAssociation", back_populates="customer")
    
    def __repr__(self):
        return f'<Customer {self.name}>'
    
    def get_interests_list(self):
        """Return interests as a list"""
        if not self.interests:
            return []
        return [interest.strip() for interest in self.interests.split(',')]
    
    def get_primary_persona(self):
        """Get the primary persona for this customer"""
        association = CustomerPersonaAssociation.query.filter_by(
            customer_id=self.id, 
            is_primary=True
        ).first()
        
        if association:
            return association.persona
        return None
    
    def assign_persona(self, persona_id, is_primary=False, relevance_score=None, notes=None):
        """Assign a persona to this customer"""
        # Check if association already exists
        existing = CustomerPersonaAssociation.query.filter_by(
            customer_id=self.id,
            persona_id=persona_id
        ).first()
        
        if existing:
            # Update existing association
            existing.is_primary = is_primary
            if relevance_score is not None:
                existing.relevance_score = relevance_score
            if notes:
                existing.notes = notes
            return existing
        
        # If setting this as primary, unset any existing primary
        if is_primary:
            CustomerPersonaAssociation.query.filter_by(
                customer_id=self.id,
                is_primary=True
            ).update({"is_primary": False})
        
        # Create new association
        association = CustomerPersonaAssociation(
            customer_id=self.id,
            persona_id=persona_id,
            is_primary=is_primary,
            relevance_score=relevance_score,
            notes=notes
        )
        
        db.session.add(association)
        return association
    
    @classmethod
    def from_profile_dict(cls, profile_dict, niche_market_id=None):
        """Create a Customer instance from a profile dictionary"""
        interests = profile_dict.get('interests', [])
        interests_str = ', '.join(interests) if interests else None
        
        # Extract country code from location if available
        location = profile_dict.get('location', '')
        country_code = None
        if ',' in location:
            # Try to parse country code from location (e.g., "New York, US")
            try:
                country_code = location.split(',')[-1].strip()
                if len(country_code) > 2:
                    # This is a full country name, not a code
                    country_code = None
            except:
                country_code = None
                
        # Use explicit country code if available
        if profile_dict.get('country_code'):
            country_code = profile_dict.get('country_code')
        
        # Récupérer les produits achetés s'ils existent
        purchased_products = profile_dict.get('purchase_history', [])
        if not purchased_products and isinstance(profile_dict.get('purchased_products'), list):
            purchased_products = profile_dict.get('purchased_products')
            
        # Récupérer les attributs de niche s'ils existent
        niche_attributes = profile_dict.get('niche_attributes', {})
        
        # Récupérer l'URL de l'avatar et le prompt s'ils existent
        avatar_url = profile_dict.get('avatar_url')
        avatar_prompt = profile_dict.get('avatar_prompt')
            
        return cls(
            name=profile_dict.get('name'),
            age=profile_dict.get('age'),
            location=profile_dict.get('location'),
            country_code=country_code,
            gender=profile_dict.get('gender'),
            language=profile_dict.get('language'),
            interests=interests_str,
            preferred_device=profile_dict.get('preferred_device'),
            income_level=profile_dict.get('income_level'),
            education=profile_dict.get('education'),
            occupation=profile_dict.get('occupation'),
            social_media=profile_dict.get('social_media'),
            shopping_frequency=profile_dict.get('shopping_frequency'),
            persona=profile_dict.get('persona'),
            avatar_url=avatar_url,
            avatar_prompt=avatar_prompt,
            purchased_products=purchased_products,
            niche_attributes=niche_attributes,
            profile_data=profile_dict,
            niche_market_id=niche_market_id
        )

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False)  # email, social, ad, etc.
    profile_data = db.Column(JSONB, nullable=True)  # The customer profile this campaign is for
    image_url = db.Column(db.Text, nullable=True)  # URL complète de l'image, peut être longue
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # SEO metadata for images
    image_alt_text = db.Column(db.String(125), nullable=True)  # Alt text optimisé pour SEO
    image_title = db.Column(db.String(60), nullable=True)  # Titre optimisé pour SEO
    image_description = db.Column(db.Text, nullable=True)  # Description optimisée pour SEO
    image_keywords = db.Column(JSONB, nullable=True)  # Mots-clés pour le référencement
    image_prompt = db.Column(db.Text, nullable=True)  # Prompt utilisé pour générer l'image
    
    # Foreign keys
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    # Relation avec les produits similaires
    similar_products = db.relationship('SimilarProduct', backref='campaign', lazy=True)
    
    def __repr__(self):
        return f'<Campaign {self.title}>'
    
    @property
    def is_personalized(self):
        """Check if this campaign is personalized"""
        return self.customer_id is not None or self.profile_data is not None
        
    def get_seo_keywords(self):
        """Return image keywords as a list"""
        if self.image_keywords and isinstance(self.image_keywords, list):
            return self.image_keywords
        return []
        
    def get_seo_image_data(self):
        """Return a dictionary with all SEO image data"""
        return {
            "url": self.image_url,
            "alt_text": self.image_alt_text or f"Marketing image for {self.title}",
            "title": self.image_title or self.title,
            "description": self.image_description or self.content,
            "keywords": self.get_seo_keywords(),
            "prompt": self.image_prompt or ""
        }

class SimilarProduct(db.Model):
    """Model for storing similar products found on AliExpress"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    product_url = db.Column(db.Text, nullable=True)
    similarity_score = db.Column(db.Float, nullable=True)  # Score de similarité (0-1)
    relevance_notes = db.Column(db.Text, nullable=True)  # Notes sur la pertinence du produit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    
    def __repr__(self):
        return f'<SimilarProduct {self.name}>'


class Metric(db.Model):
    """Model for storing application metrics and analytics data"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)  # Catégorie de la métrique (ai, user, system, etc.)
    status = db.Column(db.String(20), nullable=True)    # État (success, error, warning, info)
    data = db.Column(JSONB, nullable=True)              # Données complètes
    response_time = db.Column(db.Float, nullable=True)  # Temps de réponse en millisecondes (pour les appels API)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Foreign keys optionnels
    user_id = db.Column(db.Integer, nullable=True)      # ID utilisateur associé (si pertinent)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    
    # Relation avec Customer (optionnelle)
    customer = db.relationship('Customer', backref=db.backref('metrics', lazy=True))
    
    def __repr__(self):
        return f'<Metric {self.name} ({self.category})>'
        
    @staticmethod
    def get_metrics_summary(category=None, start_date=None, end_date=None, limit=100):
        """
        Récupère un résumé des métriques avec filtres optionnels
        
        Args:
            category: Catégorie de métriques à récupérer (optionnel)
            start_date: Date de début pour filtrer les métriques (optionnel)
            end_date: Date de fin pour filtrer les métriques (optionnel)
            limit: Nombre maximum de résultats à retourner (par défaut 100)
            
        Returns:
            Dictionnaire contenant des statistiques résumées et les derniers enregistrements
        """
        query = Metric.query
        
        # Appliquer les filtres
        if category:
            query = query.filter_by(category=category)
        if start_date:
            query = query.filter(Metric.created_at >= start_date)
        if end_date:
            query = query.filter(Metric.created_at <= end_date)
            
        # Récupérer les derniers enregistrements
        latest_metrics = query.order_by(Metric.created_at.desc()).limit(limit).all()
        
        # Calculer les statistiques
        total_count = query.count()
        success_count = query.filter_by(status='success').count()
        error_count = query.filter_by(status='error').count()
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        # Calculer le temps de réponse moyen (pour les métriques avec temps de réponse)
        avg_response_time = db.session.query(db.func.avg(Metric.response_time))\
                           .filter(Metric.response_time.isnot(None)).scalar() or 0
        
        return {
            'total_count': total_count,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'latest_metrics': latest_metrics
        }
        
class Product(db.Model):
    """Model for storing product information and generated content"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    base_description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    
    # Champs pour les contenus générés
    generated_title = db.Column(db.String(100), nullable=True)
    generated_description = db.Column(db.Text, nullable=True)
    meta_title = db.Column(db.String(60), nullable=True)
    meta_description = db.Column(db.String(160), nullable=True)
    alt_text = db.Column(db.String(125), nullable=True)
    keywords = db.Column(JSONB, nullable=True)  # Liste de mots-clés
    
    # Variantes du produit
    variants = db.Column(JSONB, nullable=True)  # Stockage des variantes (couleurs, tailles, etc.)
    comparative_analysis = db.Column(JSONB, nullable=True)  # Analyse comparative
    
    # Données complémentaires
    target_audience_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    target_audience = db.relationship('Customer', backref='targeted_products', lazy=True)
    
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
    boutique = db.relationship('Boutique', backref='products', lazy=True)
    
    # Contenu HTML optimisé pour Shopify
    html_description = db.Column(db.Text, nullable=True)  # HTML principal de description
    html_specifications = db.Column(db.Text, nullable=True)  # HTML des spécifications techniques
    html_faq = db.Column(db.Text, nullable=True)  # HTML des FAQ
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.name}>'
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        if not self.keywords:
            return []
        if isinstance(self.keywords, list):
            return self.keywords
        return [k.strip() for k in self.keywords.split(',') if k.strip()]
        
class ImportedProduct(db.Model):
    """Model for storing products imported from AliExpress with optimization data"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Lien avec le produit dans notre système
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref='import_data', lazy=True)
    
    # Données source
    source = db.Column(db.String(50), default="aliexpress")  # Source de l'import (aliexpress, amazon, etc.)
    source_url = db.Column(db.Text, nullable=False)  # URL source complète
    source_id = db.Column(db.String(100), nullable=True)  # ID du produit sur la plateforme source
    
    # Données brutes extraites
    raw_data = db.Column(JSONB, nullable=True)  # Données brutes extraites
    
    # Données de prix
    original_price = db.Column(db.Float, nullable=True)  # Prix original sur la source
    original_currency = db.Column(db.String(3), nullable=True)  # Devise d'origine (EUR, USD, etc.)
    optimized_price = db.Column(db.Float, nullable=True)  # Prix optimisé calculé
    pricing_strategy = db.Column(JSONB, nullable=True)  # Stratégie de prix complète (marges, etc.)
    
    # Données de transformation
    templates = db.Column(JSONB, nullable=True)  # Templates HTML générés (description, specs, FAQ)
    optimization_settings = db.Column(JSONB, nullable=True)  # Paramètres utilisés pour l'optimisation
    
    # Métadonnées
    import_status = db.Column(db.String(20), default="pending")  # pending, processing, complete, failed
    status_message = db.Column(db.Text, nullable=True)  # Message d'erreur ou de statut
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ImportedProduct {self.id} from {self.source}>'
