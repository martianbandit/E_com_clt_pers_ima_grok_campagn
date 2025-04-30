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
    
    def __repr__(self):
        return f'<NicheMarket {self.name}>'
        
    def get_characteristics_list(self):
        """Return key characteristics as a list"""
        if not self.key_characteristics:
            return []
        return [char.strip() for char in self.key_characteristics.split(',')]

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
    niche_market_id = db.Column(db.Integer, db.ForeignKey('niche_market.id'), nullable=True)
    
    # Relations
    campaigns = db.relationship('Campaign', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'
    
    def get_interests_list(self):
        """Return interests as a list"""
        if not self.interests:
            return []
        return [interest.strip() for interest in self.interests.split(',')]
    
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
    data = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Metric {self.name}>'
