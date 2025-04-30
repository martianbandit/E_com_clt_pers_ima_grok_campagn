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
    gender = db.Column(db.String(20), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    interests = db.Column(db.Text, nullable=True)  # Stored as comma-separated values
    preferred_device = db.Column(db.String(50), nullable=True)
    persona = db.Column(db.Text, nullable=True)
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
        
        return cls(
            name=profile_dict.get('name'),
            age=profile_dict.get('age'),
            location=profile_dict.get('location'),
            gender=profile_dict.get('gender'),
            language=profile_dict.get('language'),
            interests=interests_str,
            preferred_device=profile_dict.get('preferred_device'),
            persona=profile_dict.get('persona'),
            profile_data=profile_dict,
            niche_market_id=niche_market_id
        )

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False)  # email, social, ad, etc.
    profile_data = db.Column(JSONB, nullable=True)  # The customer profile this campaign is for
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    def __repr__(self):
        return f'<Campaign {self.title}>'
    
    @property
    def is_personalized(self):
        """Check if this campaign is personalized"""
        return self.customer_id is not None or self.profile_data is not None

class Metric(db.Model):
    """Model for storing application metrics and analytics data"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    data = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Metric {self.name}>'
