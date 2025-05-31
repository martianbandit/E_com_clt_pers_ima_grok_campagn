from datetime import datetime
import json
from app import db
from sqlalchemy.dialects.postgresql import JSON, JSONB
import enum
from sqlalchemy import UniqueConstraint
from flask_login import UserMixin

class OSPAnalysisType(enum.Enum):
    CONTENT_ANALYSIS = "content_analysis"
    VALUE_MAP = "value_map"
    SEO_OPTIMIZATION = "seo_optimization"

# Modèles pour l'authentification Replit
class User(UserMixin, db.Model):
    """Modèle pour les utilisateurs authentifiés via différentes méthodes (Replit/Google/GitHub/Email)"""
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    # ID numérique pour compatibilité avec les authentifications existantes
    numeric_id = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)

    # Identifiants des fournisseurs d'authentification
    github_id = db.Column(db.String(50), unique=True, nullable=True)  # ID GitHub pour l'authentification GitHub
    google_id = db.Column(db.String(50), unique=True, nullable=True)  # ID Google pour l'authentification Google

    # Nouveaux champs pour le profil utilisateur
    username = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin', 'user', 'manager', etc.
    language_preference = db.Column(db.String(10), default='fr', nullable=False)
    theme_preference = db.Column(db.String(10), default='dark', nullable=False)
    job_title = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    notification_preferences = db.Column(JSONB, default=lambda: {
        'email': True,
        'webapp': True,
        'marketing': False
    })
    last_login_at = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)  # Renamed from is_active to avoid conflict with UserMixin
    
    # Gestion des tokens et du plan
    tokens_total = db.Column(db.Integer, default=1000)  # Tokens totaux alloués
    tokens_used = db.Column(db.Integer, default=0)     # Tokens utilisés
    plan_name = db.Column(db.String(50), default='free', nullable=False)  # free, pro, premium
    plan_expires_at = db.Column(db.DateTime, nullable=True)  # Date d'expiration du plan
    referral_code = db.Column(db.String(20), unique=True, nullable=True)  # Code de parrainage unique
    
    # Avatar
    avatar_url = db.Column(db.String(500), nullable=True)  # URL de l'avatar personnalisé

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def update_login_stats(self):
        """Met à jour les statistiques de connexion de l'utilisateur"""
        self.last_login_at = datetime.utcnow()
        self.login_count = (self.login_count or 0) + 1
        return self
    
    @property
    def tokens_remaining(self):
        """Calcule les tokens restants"""
        return max(0, self.tokens_total - self.tokens_used)
    
    @property
    def plan_days_remaining(self):
        """Calcule les jours restants du plan"""
        if not self.plan_expires_at:
            return None
        delta = self.plan_expires_at - datetime.utcnow()
        return max(0, delta.days) if delta.total_seconds() > 0 else 0
    
    def generate_referral_code(self):
        """Génère un code de parrainage unique"""
        if not self.referral_code:
            import secrets
            import string
            self.referral_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        return self.referral_code
    
    def use_tokens(self, amount):
        """Utilise des tokens et retourne True si l'opération réussit"""
        if self.tokens_remaining >= amount:
            self.tokens_used += amount
            return True
        return False

    def get_user_data(self):
        """Retourne les données utilisateur pour l'affichage du profil"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'profile_image_url': self.profile_image_url,
            'role': self.role,
            'language_preference': self.language_preference,
            'theme_preference': self.theme_preference,
            'job_title': self.job_title,
            'company': self.company,
            'phone': self.phone,
            'bio': self.bio,
            'created_at': self.created_at,
            'last_login_at': self.last_login_at,
            'login_count': self.login_count
        }

    def update_login_stats(self):
        """Met à jour les statistiques de connexion"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1

    @property
    def is_active(self):
        """Required by Flask-Login"""
        return self.active

class OAuth(db.Model):
    """Modèle pour les tokens OAuth des utilisateurs"""
    __tablename__ = 'oauth'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    token = db.Column(JSONB, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey(User.id), nullable=False)
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

# UserActivity sera définie à la fin du fichier pour éviter les références circulaires

class Boutique(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_demographic = db.Column(db.String(255), nullable=True)

    # Colonnes linguistiques
    language = db.Column(db.String(10), default='en', nullable=False)
    multilingual_enabled = db.Column(db.Boolean, default=False, nullable=False)
    supported_languages = db.Column(JSONB, default=lambda: ['en', 'fr'], nullable=False)

    # Colonne d'appartenance (multi-tenant)
    owner_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    owner = db.relationship('User', backref=db.backref('owned_boutiques', lazy=True, cascade='all, delete-orphan'))
    customers = db.relationship('Customer', backref='boutique', lazy=True, cascade='all, delete-orphan')
    personas = db.relationship('CustomerPersona', backref='boutique', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Boutique {self.name}>'

    def get_supported_languages(self):
        """Retourne la liste des langues supportées par la boutique"""
        if not self.supported_languages:
            return ['en', 'fr']  # Valeurs par défaut

        if isinstance(self.supported_languages, list):
            return self.supported_languages
        elif isinstance(self.supported_languages, str):
            try:
                return json.loads(self.supported_languages)
            except:
                return ['en', 'fr']

        return ['en', 'fr']

class NicheMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    key_characteristics = db.Column(db.Text, nullable=True)

    # Colonne d'appartenance (multi-tenant)
    owner_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    owner = db.relationship('User', backref=db.backref('owned_niches', lazy=True, cascade='all, delete-orphan'))
    customers = db.relationship('Customer', backref='niche_market', lazy=True, cascade='all, delete-orphan')
    personas = db.relationship('CustomerPersona', backref='niche_market', lazy=True, cascade='all, delete-orphan')

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

    # Colonne d'appartenance (multi-tenant)
    owner_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)

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
    language = db.Column(db.String(50), nullable=True)  # Langue originale du client
    preferred_language = db.Column(db.String(10), nullable=True)  # Langue préférée (ISO code: fr, en, es, etc.)
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
    """Modèle pour les campagnes marketing avec métadonnées complètes"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False)  # email, social, ad, product_description, etc.
    target_audience = db.Column(db.String(100), nullable=True)  # Description brève de l'audience cible
    status = db.Column(db.String(20), default="draft")  # draft, active, paused, completed, archived

    # Colonnes linguistiques
    language = db.Column(db.String(10), default='en', nullable=False)  # Langue principale de la campagne
    multilingual_campaign = db.Column(db.Boolean, default=False, nullable=False)  # Si campagne multilingue
    target_languages = db.Column(JSONB, default=lambda: ['en'], nullable=False)  # Langues cibles

    # Contenu et données
    profile_data = db.Column(JSONB, nullable=True)  # The customer profile this campaign is for
    prompt_used = db.Column(db.Text, nullable=True)  # Prompt utilisé pour générer le contenu
    ai_model_used = db.Column(db.String(50), nullable=True)  # Modèle IA utilisé (grok-2, gpt-4o, etc.)
    generation_params = db.Column(JSONB, nullable=True)  # Paramètres utilisés pour la génération

    # Métriques et suivi
    view_count = db.Column(db.Integer, default=0)  # Nombre de vues
    click_count = db.Column(db.Integer, default=0)  # Nombre de clics
    conversion_count = db.Column(db.Integer, default=0)  # Nombre de conversions

    # Image principale
    image_url = db.Column(db.Text, nullable=True)  # URL complète de l'image, peut être longue
    image_alt_text = db.Column(db.String(125), nullable=True)  # Alt text optimisé pour SEO
    image_title = db.Column(db.String(60), nullable=True)  # Titre optimisé pour SEO
    image_description = db.Column(db.Text, nullable=True)  # Description optimisée pour SEO
    image_keywords = db.Column(JSONB, nullable=True)  # Mots-clés pour le référencement
    image_prompt = db.Column(db.Text, nullable=True)  # Prompt utilisé pour générer l'image

    # Planification et publication
    scheduled_at = db.Column(db.DateTime, nullable=True)  # Date planifiée de publication
    published_at = db.Column(db.DateTime, nullable=True)  # Date effective de publication
    platforms = db.Column(JSONB, nullable=True)  # Plateformes de publication (Facebook, Instagram, Email, etc.)

    # Dates de création/modification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    # Relation sans backref pour éviter les conflits
    campaign_customer = db.relationship('Customer', foreign_keys=[customer_id], lazy=True)

    persona_id = db.Column(db.Integer, db.ForeignKey('customer_persona.id'), nullable=True)
    campaign_persona = db.relationship('CustomerPersona', foreign_keys=[persona_id], lazy=True)

    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
    campaign_boutique = db.relationship('Boutique', foreign_keys=[boutique_id], lazy=True)

    # Relation avec les produits similaires
    similar_products = db.relationship('SimilarProduct', backref='campaign', lazy=True)

    def __repr__(self):
        return f'<Campaign {self.title} ({self.campaign_type})>'

    @property
    def engagement_rate(self):
        """Calcule le taux d'engagement (vues -> clics)"""
        if self.view_count == 0:
            return 0
        return (self.click_count / self.view_count) * 100

    @property
    def conversion_rate(self):
        """Calcule le taux de conversion (clics -> conversions)"""
        if self.click_count == 0:
            return 0
        return (self.conversion_count / self.click_count) * 100

    def log_view(self):
        """Incrémente le compteur de vues"""
        self.view_count += 1
        db.session.commit()

    def log_click(self):
        """Incrémente le compteur de clics"""
        self.click_count += 1
        db.session.commit()

    def log_conversion(self):
        """Incrémente le compteur de conversions"""
        self.conversion_count += 1
        db.session.commit()

    def publish(self):
        """Publie la campagne"""
        if self.status == "draft":
            self.status = "active"
            self.published_at = datetime.utcnow()
            db.session.commit()

    def archive(self):
        """Archive la campagne"""
        self.status = "archived"
        db.session.commit()

    @staticmethod
    def get_campaign_stats():
        """Récupère des statistiques sur toutes les campagnes"""
        from sqlalchemy import func

        total_campaigns = Campaign.query.count()
        active_campaigns = Campaign.query.filter_by(status="active").count()

        # Aggrégations sur les vues, clics et conversions
        results = db.session.query(
            func.sum(Campaign.view_count).label('total_views'),
            func.sum(Campaign.click_count).label('total_clicks'),
            func.sum(Campaign.conversion_count).label('total_conversions')
        ).first()

        # Protection contre les valeurs nulles
        if results and hasattr(results, 'total_views'):
            total_views = results.total_views or 0
            total_clicks = results.total_clicks or 0
            total_conversions = results.total_conversions or 0
        else:
            total_views = 0
            total_clicks = 0
            total_conversions = 0

        # Campagnes par type
        campaign_types = db.session.query(
            Campaign.campaign_type,
            func.count(Campaign.id).label('count')
        ).group_by(Campaign.campaign_type).all()

        types_summary = {c_type: count for c_type, count in campaign_types}

        return {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'total_views': total_views,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'avg_engagement_rate': (total_clicks / total_views * 100) if total_views > 0 else 0,
            'avg_conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
            'campaigns_by_type': types_summary
        }

    @staticmethod
    def get_stats_by_boutique_type():
        """
        Récupère des statistiques sur les campagnes par type de boutique

        Returns:
            Dict avec les statistiques par boutique:
            {
                'boutiques': [
                    {
                        'id': 1,
                        'name': 'Boutique Mode Femme',
                        'total_campaigns': 10,
                        'active_campaigns': 5,
                        'total_views': 1500,
                        'total_clicks': 200,
                        'total_conversions': 50,
                        'engagement_rate': 13.33,
                        'conversion_rate': 25.0,
                        'campaigns_by_type': {'email': 5, 'social': 3, 'ad': 2}
                    },
                    ...
                ],
                'total_boutiques': 5,
                'top_performing': {'id': 1, 'name': 'Boutique Mode Femme', 'conversion_rate': 25.0}
            }
        """
        from sqlalchemy import func

        # Récupérer toutes les boutiques
        boutiques = Boutique.query.all()
        boutique_stats = []

        # Pour chaque boutique, calculer les statistiques
        for boutique in boutiques:
            # Récupérer les campagnes de cette boutique
            campaigns = Campaign.query.filter_by(boutique_id=boutique.id).all()

            if not campaigns:
                # Si pas de campagnes, ajouter des stats vides
                boutique_stats.append({
                    'id': boutique.id,
                    'name': boutique.name,
                    'description': boutique.description,
                    'target_demographic': boutique.target_demographic,
                    'total_campaigns': 0,
                    'active_campaigns': 0,
                    'total_views': 0,
                    'total_clicks': 0,
                    'total_conversions': 0,
                    'engagement_rate': 0,
                    'conversion_rate': 0,
                    'campaigns_by_type': {}
                })
                continue

            # Compter les campagnes par statut
            total_campaigns = len(campaigns)
            active_campaigns = sum(1 for c in campaigns if c.status == "active")

            # Calculer les totaux pour les métriques
            total_views = sum(c.view_count for c in campaigns)
            total_clicks = sum(c.click_count for c in campaigns)
            total_conversions = sum(c.conversion_count for c in campaigns)

            # Calculer les taux
            engagement_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
            conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

            # Regrouper par type de campagne
            campaigns_by_type = {}
            for c in campaigns:
                if c.campaign_type not in campaigns_by_type:
                    campaigns_by_type[c.campaign_type] = 0
                campaigns_by_type[c.campaign_type] += 1

            # Ajouter les statistiques pour cette boutique
            boutique_stats.append({
                'id': boutique.id,
                'name': boutique.name,
                'description': boutique.description,
                'target_demographic': boutique.target_demographic,
                'total_campaigns': total_campaigns,
                'active_campaigns': active_campaigns,
                'total_views': total_views,
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'engagement_rate': round(engagement_rate, 2),
                'conversion_rate': round(conversion_rate, 2),
                'campaigns_by_type': campaigns_by_type
            })

        # Trouver la boutique la plus performante (taux de conversion le plus élevé)
        top_performing = None
        if boutique_stats:
            # Filtrer les boutiques sans campagnes ou sans conversions
            performing_boutiques = [b for b in boutique_stats if b['total_campaigns'] > 0 and b['conversion_rate'] > 0]

            if performing_boutiques:
                top_performing = max(performing_boutiques, key=lambda x: x['conversion_rate'])
                top_performing = {
                    'id': top_performing['id'],
                    'name': top_performing['name'],
                    'conversion_rate': top_performing['conversion_rate']
                }

        return {
            'boutiques': boutique_stats,
            'total_boutiques': len(boutiques),
            'top_performing': top_performing
        }

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

    def get_target_languages(self):
        """Retourne la liste des langues cibles de la campagne"""
        if not self.target_languages:
            return [self.language or 'en']

        if isinstance(self.target_languages, list):
            return self.target_languages
        elif isinstance(self.target_languages, str):
            try:
                return json.loads(self.target_languages)
            except:
                return [self.language or 'en']

        return [self.language or 'en']

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


class OSPAnalysis(db.Model):
    """Model for storing OSP marketing analysis and tools output"""
    id = db.Column(db.Integer, primary_key=True)
    analysis_type = db.Column(db.Enum(OSPAnalysisType), nullable=False)
    title = db.Column(db.String(100), nullable=False)

    # Input data and results - utilisant la colonne 'content' existante dans la base
    content = db.Column(JSONB, nullable=True)  # Stored as JSON with the analysis results
    html_result = db.Column(db.Text, nullable=True, name="html_result")  # Optional HTML rendering of results

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations avec les autres entités
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('customer_persona.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)

    # Relations
    product = db.relationship('Product', backref=db.backref('osp_analyses', lazy=True))
    campaign = db.relationship('Campaign', backref=db.backref('osp_analyses', lazy=True))
    persona = db.relationship('CustomerPersona', backref=db.backref('osp_analyses', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('osp_analyses', lazy=True))
    boutique = db.relationship('Boutique', backref=db.backref('osp_analyses', lazy=True))

    def __repr__(self):
        return f'<OSPAnalysis {self.id}: {self.analysis_type.value} - {self.title}>'

class Metric(db.Model):
    """Model for storing application metrics and analytics data"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)  # Catégorie de la métrique (ai, user, system, etc.)
    status = db.Column(db.Boolean, default=True)        # État (True=succès, False=erreur)
    data = db.Column(JSONB, nullable=True)              # Données complètes
    execution_time = db.Column(db.Float, nullable=True) # Temps d'exécution en secondes
    response_time = db.Column(db.Float, nullable=True)  # Temps de réponse en millisecondes (pour les appels API)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Foreign keys optionnels
    user_id = db.Column(db.String, nullable=True)       # ID utilisateur associé (si pertinent) - Accepte UUID ou Integer sous forme de chaîne
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


# Classe UserActivity définie à la fin du fichier pour éviter les références circulaires
class UserActivity(db.Model):
    """Modèle pour suivre les activités des utilisateurs"""
    __tablename__ = 'user_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # login, profile_update, create_campaign, etc.
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    activity_data = db.Column(JSONB, nullable=True)  # Données supplémentaires sur l'activité (renommé de metadata)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec User
    user = db.relationship('User', backref=db.backref('user_activities', lazy=True, cascade='all, delete-orphan'))

    @classmethod
    def log_activity(cls, user_id, activity_type, description=None, ip_address=None, user_agent=None, metadata=None):
        """Crée une entrée d'activité pour un utilisateur"""
        activity = cls(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            activity_data=metadata  # Utilise activity_data à la place de metadata
        )
        db.session.add(activity)
        return activity

    @staticmethod
    def get_recent_activities(user_id, limit=10):
        """Récupère les activités récentes d'un utilisateur"""
        return UserActivity.query.filter_by(user_id=user_id).order_by(UserActivity.created_at.desc()).limit(limit).all()

# Ajouter d'autres modèles selon les besoins

# Classe OSPAnalysisType est déjà définie plus haut dans le fichier

# Table pour les audits SEO
class SEOAudit(db.Model):
    """Audits SEO pour les boutiques, campagnes et produits"""
    id = db.Column(db.Integer, primary_key=True)

    # Liens vers les objets analysés (un seul doit être non-null)
    boutique_id = db.Column(db.Integer, db.ForeignKey('boutique.id'), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)

    # Données de l'audit
    audit_date = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, nullable=False)  # Score global sur 100
    results = db.Column(JSONB, nullable=True)  # Résultats complets de l'audit
    locale = db.Column(db.String(10), default='fr_FR')  # Code de langue et région

    # Relations
    boutique = db.relationship('Boutique', backref=db.backref('seo_audits', lazy=True))
    campaign = db.relationship('Campaign', backref=db.backref('seo_audits', lazy=True))
    product = db.relationship('Product', backref=db.backref('seo_audits', lazy=True))

    @classmethod
    def get_latest_audit(cls, boutique_id=None, campaign_id=None, product_id=None):
        """Récupère le dernier audit pour un objet donné"""
        query = cls.query

        if boutique_id:
            query = query.filter_by(boutique_id=boutique_id)
        elif campaign_id:
            query = query.filter_by(campaign_id=campaign_id)
        elif product_id:
            query = query.filter_by(product_id=product_id)
        else:
            return None

        return query.order_by(cls.audit_date.desc()).first()

# Table pour les mots-clés SEO
class SEOKeyword(db.Model):
    """Mots-clés SEO analysés et leur performance"""
    id = db.Column(db.Integer, primary_key=True)

    # Données du mot-clé
    keyword = db.Column(db.String(255), nullable=False)
    locale = db.Column(db.String(10), default='fr_FR')  # Code de langue et région
    competition_score = db.Column(db.Float, default=0)  # Score de compétition (0-100)
    trend_change = db.Column(db.Float, default=0)  # Changement de tendance en %
    search_volume = db.Column(db.Integer, nullable=True)  # Volume de recherche mensuel
    status = db.Column(db.String(20), default='neutral')  # 'trending', 'declining', 'opportunity', 'neutral'

    # Horodatage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Unicité du mot-clé par locale
    __table_args__ = (
        db.UniqueConstraint('keyword', 'locale', name='uk_keyword_locale'),
    )

    @classmethod
    def get_trending_keywords(cls, locale='fr_FR', limit=10):
        """Récupère les mots-clés en tendance"""
        return cls.query.filter_by(
            locale=locale, 
            status='trending'
        ).order_by(cls.trend_change.desc()).limit(limit).all()

    @classmethod
    def get_opportunity_keywords(cls, locale='fr_FR', limit=10):
        """Récupère les mots-clés à faible compétition"""
        return cls.query.filter_by(
            locale=locale, 
            status='opportunity'
        ).order_by(cls.competition_score.asc()).limit(limit).all()