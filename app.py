import os
import json
import logging
import datetime
import uuid
import sys
import stripe
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from security_enhancements import init_security_extensions, add_security_headers, setup_error_handlers
from security_middleware import security_middleware
from centralized_logging import setup_logging
# Modules de sécurité et performance avancés (initialisation conditionnelle)
try:
    from encryption_manager import encryption_manager, get_encryption_status
    encryption_available = True
except ImportError as e:
    logger.warning(f"Module de chiffrement non disponible: {e}")
    encryption_available = False

try:
    from redis_cache_manager import cache_manager, SessionManager, BusinessDataCache
    cache_available = True
except ImportError as e:
    logger.warning(f"Module de cache Redis non disponible: {e}")
    cache_available = False

try:
    from database_optimization import DatabaseOptimizer
    db_optimization_available = True
except ImportError as e:
    logger.warning(f"Module d'optimisation DB non disponible: {e}")
    db_optimization_available = False

try:
    from ddos_protection import ddos_protection, ddos_protection_middleware, get_ddos_stats
    ddos_protection_available = True
except ImportError as e:
    logger.warning(f"Module de protection DDoS non disponible: {e}")
    ddos_protection_available = False
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, g
from markupsafe import Markup, escape
import html
import re
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_babel import gettext as _
from flask_login import login_required, current_user, login_user, logout_user, LoginManager
from i18n import babel, get_locale, get_supported_languages, get_language_name, get_boutique_languages, is_multilingual_campaign, get_campaign_target_languages
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.github import make_github_blueprint, github

# Performance optimizations
try:
    from performance_cache import performance_cache
    from database_indexing import db_index_optimizer
    from asset_optimizer import asset_optimizer
    performance_modules_loaded = True
    print("Performance optimization modules loaded successfully")
except ImportError as e:
    print(f"Performance modules not available: {e}")
    performance_modules_loaded = False
    performance_cache = None
    db_index_optimizer = None
    asset_optimizer = None

# User feedback system
try:
    from user_feedback_system import feedback_manager, FeedbackType, FeedbackPriority
    feedback_system_loaded = True
except ImportError as e:
    logging.warning(f"Feedback system not available: {e}")
    feedback_system_loaded = False

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger("NinjaMark")

def secure_log(level, message, **kwargs):
    """Log sécurisé qui masque les informations sensibles"""
    sensitive_fields = ['password', 'token', 'key', 'secret', 'email']
    
    # Masquer les informations sensibles dans le message
    for field in sensitive_fields:
        if field in message.lower():
            message = re.sub(f'{field}[=:]\s*[\w@.-]+', f'{field}=***', message, flags=re.IGNORECASE)
    
    # Masquer les informations sensibles dans kwargs
    safe_kwargs = {}
    for key, value in kwargs.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            safe_kwargs[key] = '***'
        else:
            safe_kwargs[key] = value
    
    logger.log(level, message, extra=safe_kwargs)


# Protection robuste contre les attaques par déni de service avec Flask-Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import os

# Module de gestion des erreurs
from error_handlers import register_error_handlers

def validate_sql_params(**kwargs):
    """Valide les paramètres SQL pour prévenir les injections"""
    validated = {}
    for key, value in kwargs.items():
        if value is not None:
            # Suppression des caractères SQL dangereux
            if isinstance(value, str):
                value = re.sub(r'[\'";]', '', str(value))
            validated[key] = value
    return validated

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# Initialize Sentry for monitoring
def init_sentry():
    """Initialize Sentry monitoring with advanced profiling and tracing"""
    sentry_dsn = os.environ.get("SENTRY_DSN", "https://350994d4ed87e5e65b314481f8257c07@o4509423969107968.ingest.us.sentry.io/4509424027303936")
    
    if sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                ],
                # Set traces_sample_rate to 1.0 to capture 100%
                # of transactions for tracing.
                traces_sample_rate=1.0,
                # Set profile_session_sample_rate to 1.0 to profile 100%
                # of profile sessions.
                profile_session_sample_rate=1.0,
                # Set profile_lifecycle to "trace" to automatically
                # run the profiler on when there is an active transaction
                profile_lifecycle="trace",
                send_default_pii=True,
                attach_stacktrace=True,
                debug=False,
                environment=os.environ.get("ENVIRONMENT", "production"),
                release=os.environ.get("APP_VERSION", "1.0.0"),
            )
            logger.info("Sentry monitoring initialized with advanced profiling and 100% trace sampling")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {str(e)}")
    else:
        logger.info("Sentry monitoring disabled - no DSN provided")

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-please-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize monitoring with provided DSN
init_sentry()

# Configure and initialize rate limiting
def init_rate_limiting():
    """Initialize robust rate limiting with Flask-Limiter"""
    try:
        # Try to use Redis if available, fallback to memory
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            storage_uri = redis_url
            logger.info("Rate limiting configured with Redis backend")
        else:
            storage_uri = "memory://"
            logger.info("Rate limiting configured with memory backend")
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["1000 per day", "200 per hour", "50 per minute"],
            storage_uri=storage_uri,
            strategy="fixed-window",
            headers_enabled=True,
            swallow_errors=True  # Continue serving if rate limiting fails
        )
        
        # Apply specific limits to sensitive endpoints
        @limiter.limit("5 per minute")
        def login_rate_limit():
            pass
        
        @limiter.limit("3 per minute") 
        def register_rate_limit():
            pass
            
        @limiter.limit("20 per minute")
        def ai_generation_rate_limit():
            pass
        
        logger.info("Rate limiting system initialized successfully")
        return limiter
        
    except Exception as e:
        logger.error(f"Failed to initialize rate limiting: {str(e)}")
        return None

limiter = init_rate_limiting()

# Apply rate limiting configuration
if limiter:
    from rate_limiting_config import apply_rate_limits_to_routes, setup_advanced_rate_limiting
    apply_rate_limits_to_routes(app, limiter)
    setup_advanced_rate_limiting(app, limiter)

# Configuration de sécurité avancée
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=1)

# Configuration du middleware de sécurité
app.config['SECURITY_RATE_LIMIT_REQUESTS'] = 100
app.config['SECURITY_RATE_LIMIT_WINDOW'] = 3600
app.config['SECURITY_BLOCK_ATTACKS'] = True
app.config['SECURITY_LOG_ATTACKS'] = True

# Initialisation du middleware de sécurité avancée
security_middleware.init_app(app)

# Initialisation du système de logs centralisés
centralized_logs = setup_logging(app)

# Initialisation du système GDPR (après création de db)
try:
    from gdpr_compliance import gdpr_compliance
    from gdpr_routes import gdpr_bp
    gdpr_compliance.init_app(app)
    app.register_blueprint(gdpr_bp)
    logger.info("✅ Système GDPR initialisé avec succès")
except ImportError as e:
    logger.warning(f"Module GDPR non disponible: {e}")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation GDPR: {e}")

# Configuration OAuth GitHub
app.config["GITHUB_OAUTH_CLIENT_ID"] = os.environ.get("GITHUB_CLIENT_ID")
app.config["GITHUB_OAUTH_CLIENT_SECRET"] = os.environ.get("GITHUB_CLIENT_SECRET")

# Fonctions de sécurité pour valider les entrées
def sanitize_input(input_data, input_type="text"):
    """Nettoie et valide les entrées utilisateur pour prévenir XSS et injections"""
    if not input_data:
        return ""
    
    # Conversion en string et nettoyage de base
    cleaned = str(input_data).strip()
    
    # Suppression des caractères de contrôle dangereux
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
    
    if input_type == "email":
        # Validation email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, cleaned):
            raise ValueError("Format d'email invalide")
    
    elif input_type == "html":
        # Échappement HTML pour prévenir XSS
        cleaned = escape(cleaned)
    
    elif input_type == "url":
        # Validation URL basique
        if cleaned and not cleaned.startswith(('http://', 'https://')):
            raise ValueError("URL invalide")
    
    return cleaned

def validate_form_data(form_data, required_fields=None):
    """Valide les données de formulaire"""
    if required_fields is None:
        required_fields = []
    
    validated_data = {}
    for field, value in form_data.items():
        if field in required_fields and not value:
            raise ValueError(f"Le champ {field} est requis")
        
        # Nettoyage des données selon le type de champ
        if field.endswith('_email'):
            validated_data[field] = sanitize_input(value, "email")
        elif field.endswith('_url'):
            validated_data[field] = sanitize_input(value, "url")
        else:
            validated_data[field] = sanitize_input(value, "html")
    
    return validated_data
def secure_file_upload(file):
    """Valide de manière sécurisée les fichiers uploadés"""
    if not file or not file.filename:
        return False, "Aucun fichier sélectionné"
    
    # Extensions autorisées
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.csv'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension non autorisée: {file_ext}"
    
    # Taille maximale (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return False, "Fichier trop volumineux (max 5MB)"
    
    # Vérification du nom de fichier
    import string
    allowed_chars = string.ascii_letters + string.digits + '.-_'
    if not all(c in allowed_chars for c in file.filename):
        return False, "Nom de fichier contient des caractères non autorisés"
    
    return True, "Fichier valide"


# Rendre current_user et d'autres variables disponibles dans tous les templates
@app.context_processor
def inject_template_globals():
    return dict(
        current_user=current_user,
        # Fonctions utilitaires pour les templates
        min=min,
        max=max
    )

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Configuration du LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
# Setting the login view with a string value
setattr(login_manager, 'login_view', 'login')
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    try:
        # Essai de conversion en entier pour les anciens utilisateurs
        return User.query.get(int(user_id))
    except ValueError:
        # Si l'ID n'est pas un entier, il s'agit d'un UUID
        return User.query.get(user_id)

# Authentification Google supprimée comme demandé

# Importation et initialisation de l'authentification Replit
from replit_auth import init_auth
init_auth(app, db)

# Import and register Stripe payment blueprint
from stripe_payment import stripe_bp
app.register_blueprint(stripe_bp)

# Initialisation de l'authentification GitHub
github_bp = make_github_blueprint(scope=["user:email"])
app.register_blueprint(github_bp, url_prefix="/github")

# Protection contre les attaques par déni de service
# Rate limiting is now handled by Flask-Limiter automatically

# Route d'accueil
@app.route('/home')
def home():
    """Page d'accueil pour les utilisateurs connectés"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('landing'))

@app.route('/')
def index():
    """Page d'accueil - landing page publique"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Page d'accueil avec présentation de l'application
    return render_template('index.html')

@app.route('/test')
def test_page():
    """Page de test pour diagnostiquer les problèmes"""
    return """
    <html>
    <head><title>Test MarkEasy</title></head>
    <body>
        <h1>Test MarkEasy</h1>
        <p>L'application fonctionne correctement.</p>
        <ul>
            <li><a href="/login">Page de connexion</a></li>
            <li><a href="/register">Page d'inscription</a></li>
            <li><a href="/auth/replit_auth/login">Connexion Replit</a></li>
        </ul>
    </body>
    </html>
    """
    
@app.route('/landing')
@login_required
def landing():
    """Landing page avec les plans tarifaires - accès restreint"""
    from stripe_payment import PLANS, PRODUCTS
    return render_template('stripe/landing_fixed.html', plans=PLANS, products=PRODUCTS)

# Gestionnaire d'authentification réussie GitHub
@oauth_authorized.connect_via(github_bp)
def github_logged_in(blueprint, token):
    from models import User, UserActivity
    if not token:
        flash("Échec de l'authentification GitHub.", "danger")
        return False

    # Récupération des informations utilisateur GitHub
    resp = blueprint.session.get("/user")
    if not resp.ok:
        flash("Échec de la récupération des informations utilisateur GitHub.", "danger")
        return False

    # Extraction des données utilisateur
    github_info = resp.json()
    github_id = str(github_info["id"])
    github_username = github_info.get("login")
    github_email = github_info.get("email")
    
    # Si l'email n'est pas disponible, récupérer les emails de l'utilisateur
    if not github_email:
        emails_resp = blueprint.session.get("/user/emails")
        if emails_resp.ok:
            emails = emails_resp.json()
            # Recherche de l'email principal et vérifié
            for email_data in emails:
                if email_data.get("primary") and email_data.get("verified"):
                    github_email = email_data.get("email")
                    break
    
    # Recherche de l'utilisateur par github_id
    user = User.query.filter_by(github_id=github_id).first()
    
    # Si l'utilisateur n'existe pas, le créer
    if not user:
        # Génération d'un ID unique
        user = User()
        user.id = str(uuid.uuid4())
        user.github_id = github_id
        user.created_at = datetime.datetime.now()
    
    # Mise à jour des informations utilisateur
    user.username = github_username
    user.email = github_email
    user.profile_image_url = github_info.get("avatar_url")
    
    # Nom complet
    name = github_info.get("name", "").split(" ", 1)
    if len(name) > 0:
        user.first_name = name[0]
    if len(name) > 1:
        user.last_name = name[1]
    
    # Sauvegarde des modifications
    db.session.add(user)
    
    # Enregistrement de l'activité de connexion
    activity = UserActivity(
        user_id=user.id,
        activity_type="login",
        description="Connexion GitHub",
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")
    )
    db.session.add(activity)
    db.session.commit()
    
    # Connexion de l'utilisateur
    login_user(user)
    
    # Redirection vers la page d'accueil
    flash(f"Bienvenue, {user.username or 'utilisateur GitHub'} !", "success")
    return False  # Ne pas rediriger, laisser Flask-Dance le faire

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion avec email/mot de passe + options OAuth"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    from forms import LoginForm
    from models import User
    from werkzeug.security import check_password_hash
    from datetime import datetime
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            # Mise à jour des statistiques de connexion
            user.login_count = (user.login_count or 0) + 1
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            
            # Redirection vers la page demandée ou la page d'accueil
            next_page = request.args.get('next')
            if next_page:
                # Validate redirect URL to prevent open redirect attacks
                from urllib.parse import urlparse
                parsed_url = urlparse(next_page)
                # Only allow redirects to relative paths on the same host
                if (not parsed_url.netloc and 
                    parsed_url.path.startswith('/') and 
                    not parsed_url.path.startswith('//') and
                    '\\' not in parsed_url.path):
                    return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
    
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    from forms import RegistrationForm
    from models import User
    from werkzeug.security import generate_password_hash
    import uuid
    from datetime import datetime
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Génération d'un ID unique pour la compatibilité avec les utilisateurs OAuth
        user_id = str(uuid.uuid4())
        
        # Création du nouvel utilisateur
        user = User()
        user.id = user_id
        user.username = form.username.data
        user.email = form.email.data
        user.password_hash = generate_password_hash(form.password.data) if form.password.data else None
        user.role = 'user'
        user.active = True
        user.created_at = datetime.datetime.now()
        user.updated_at = datetime.datetime.now()
        
        db.session.add(user)
        db.session.commit()
        
        flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Déconnexion et redirection vers la page d'accueil"""
    # Enregistrer l'activité de déconnexion
    try:
        if current_user and current_user.is_authenticated:
            from models import UserActivity
            user_id = current_user.id
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.remote_addr or '0.0.0.0'
            
            # Si UserActivity a une méthode log_activity, l'utiliser
            if hasattr(UserActivity, 'log_activity'):
                UserActivity.log_activity(
                    user_id=user_id,
                    activity_type='logout',
                    description=f'Déconnexion depuis {ip_address}',
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:
                # Sinon, créer manuellement une entrée d'activité
                activity = UserActivity()
                activity.user_id = user_id
                activity.activity_type = 'logout'
                activity.description = f'Déconnexion depuis {ip_address}'
                db.session.add(activity)
                
            db.session.commit()
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'activité de déconnexion : {e}")
    
    # Déconnecter l'utilisateur
    logout_user()
    
    # Message flash de confirmation
    flash('Vous avez été déconnecté avec succès.', 'info')
    
    # Rediriger vers la page d'accueil
    return redirect(url_for('index'))

# Cette route a été remplacée par la route logout ci-dessus qui redirige vers Replit Auth
    
@app.route('/user-info')
def user_info():
    """Page d'information utilisateur pour le débogage"""
    return render_template('user_info.html')

# Routes pour l'authentification et le profil utilisateur
@app.route('/user/profile')
@login_required
def user_profile():
    """Page de profil utilisateur avec statistiques"""
    from models import Campaign, Customer, Product, UserActivity
    
    # Récupération des statistiques d'utilisation
    campaigns_count = Campaign.query.count()
    customers_count = Customer.query.count()
    products_count = Product.query.count()
    
    # Récupérer les activités récentes de l'utilisateur
    activities = UserActivity.get_recent_activities(current_user.id, limit=10)
    
    return render_template('user/profile.html',
                          campaigns_count=campaigns_count,
                          customers_count=customers_count,
                          products_count=products_count,
                          activities=activities)

@app.route('/user/settings')
@login_required
def user_settings():
    """Page de paramètres utilisateur"""
    return render_template('user/settings.html', title='Paramètres')

@app.route('/user/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Mettre à jour le profil utilisateur"""
    from models import UserActivity
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        current_user.job_title = request.form.get('job_title')
        current_user.company = request.form.get('company')
        current_user.address = request.form.get('address')
        current_user.bio = request.form.get('bio')
        current_user.language_preference = request.form.get('language_preference', 'fr')
        current_user.theme_preference = request.form.get('theme_preference', 'dark')
        
        # Enregistrer l'activité
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='profile_update',
            description='Mise à jour du profil',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Sauvegarder les modifications
        db.session.commit()
        
        flash('Profil mis à jour avec succès !', 'success')
        return redirect(url_for('user_profile'))
    
    return redirect(url_for('user_profile'))

@app.route('/user/update-account-settings', methods=['POST'])
@login_required
def update_account_settings():
    """Mettre à jour les paramètres du compte"""
    from models import UserActivity
    
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        current_user.language_preference = request.form.get('language_preference', 'fr')
        
        # Enregistrer l'activité
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='account_update',
            description='Mise à jour des paramètres du compte',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        flash('Paramètres du compte mis à jour avec succès !', 'success')
        return redirect(url_for('user_settings'))
    
    return redirect(url_for('user_settings'))

@app.route('/user/update-password', methods=['POST'])
@login_required
def update_password():
    """Mettre à jour le mot de passe"""
    from models import UserActivity
    from werkzeug.security import generate_password_hash
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Pour la démo, on accepte admin comme mot de passe actuel
        if current_password == 'admin' and new_password == confirm_password:
            # Hasher le nouveau mot de passe
            current_user.password_hash = generate_password_hash(new_password) if new_password else None
            
            # Enregistrer l'activité
            activity = UserActivity.log_activity(
                user_id=current_user.id,
                activity_type='password_update',
                description='Mise à jour du mot de passe',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            db.session.commit()
            
            flash('Mot de passe mis à jour avec succès !', 'success')
        else:
            flash('Erreur lors de la mise à jour du mot de passe. Vérifiez vos informations.', 'danger')
        
        return redirect(url_for('user_settings'))
    
    return redirect(url_for('user_settings'))

@app.route('/user/update-notification-preferences', methods=['POST'])
@login_required
def update_notification_preferences():
    """Mettre à jour les préférences de notification"""
    from models import UserActivity
    
    if request.method == 'POST':
        # Mettre à jour les préférences de notification
        current_user.notification_preferences = {
            'email': 'email_notifications' in request.form,
            'webapp': 'webapp_notifications' in request.form,
            'marketing': 'marketing_notifications' in request.form
        }
        
        # Enregistrer l'activité
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='notification_update',
            description='Mise à jour des préférences de notification',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        flash('Préférences de notification mises à jour !', 'success')
        return redirect(url_for('user_settings'))
    
    return redirect(url_for('user_settings'))

@app.route('/user/update-appearance-settings', methods=['POST'])
@login_required
def update_appearance_settings():
    """Mettre à jour les paramètres d'apparence"""
    from models import UserActivity
    
    if request.method == 'POST':
        current_user.theme_preference = request.form.get('theme_preference', 'dark')
        
        # Enregistrer l'activité
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='appearance_update',
            description='Mise à jour des paramètres d\'apparence',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        flash('Paramètres d\'apparence mis à jour !', 'success')
        return redirect(url_for('user_settings'))
    
    return redirect(url_for('user_settings'))

@app.route('/user/add-api-key', methods=['POST'])
@login_required
def add_api_key():
    """Ajouter une clé API"""
    from models import UserActivity
    
    if request.method == 'POST':
        service_name = request.form.get('service_name')
        api_key = request.form.get('api_key')
        
        # Ici, on pourrait stocker la clé API dans la base de données
        # Pour l'instant, on simule juste l'ajout
        
        # Enregistrer l'activité
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='api_key_add',
            description=f'Ajout d\'une clé API pour {service_name}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        flash('Clé API ajoutée avec succès !', 'success')
        return redirect(url_for('user_settings'))
    
    return redirect(url_for('user_settings'))

# Configure the PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    raise RuntimeError("DATABASE_URL environment variable is not set. PostgreSQL database is required.")
    
# Check if DATABASE_URL starts with postgres://, and if so, replace with postgresql://
# This is required for SQLAlchemy 1.4.x+
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel.init_app(app, locale_selector=get_locale)

# Enregistrement des gestionnaires d'erreurs personnalisés
register_error_handlers(app)

# Import routes after app initialization
from models import Boutique, NicheMarket, Customer, Campaign, SimilarProduct, Metric, Product, ImportedProduct
import asyncio
import aliexpress_importer
import product_generator
from boutique_ai import (
    generate_customers, 
    generate_customer_persona, 
    generate_marketing_content,
    GROK_2_IMAGE,
    generate_marketing_image
)

# Ajouter des filtres Jinja personnalisés
@app.template_filter('nl2br')
def nl2br_filter(s):
    """Convertit les retours à la ligne en balises <br>"""
    if s is None:
        return ""
    return Markup(s.replace('\n', '<br>'))

# Function to log metrics to the database
def log_metric(metric_name, data, category=None, status=None, response_time=None, customer_id=None):
    """
    Fonction améliorée pour enregistrer des métriques dans la base de données
    
    Args:
        metric_name: Nom de la métrique
        data: Données à enregistrer (dictionnaire)
        category: Catégorie de la métrique (ai, user, system, etc.)
        status: État (success, error, warning, info)
        response_time: Temps de réponse en ms (pour les appels API)
        customer_id: ID du client associé (si pertinent)
    
    Returns:
        Métrique créée ou None en cas d'erreur
    """
    try:
        # Extraire automatiquement le statut des données si non spécifié
        if status is None and isinstance(data, dict) and 'success' in data:
            # Conversion explicite en booléen (True/False) au lieu de chaîne de caractères
            status = True if data['success'] else False
        elif status == 'success':
            # Convertir 'success' en True
            status = True
        elif status == 'error':
            # Convertir 'error' en False
            status = False
        
        # Extraire automatiquement la catégorie si non spécifiée
        if category is None:
            # Détection basée sur le nom de la métrique
            if 'ai_' in metric_name or 'grok_' in metric_name or 'openai_' in metric_name:
                category = 'ai'
            elif 'user_' in metric_name:
                category = 'user'
            elif 'system_' in metric_name:
                category = 'system'
            elif 'generation' in metric_name:
                category = 'generation'
            elif 'import' in metric_name:
                category = 'import'
            else:
                category = 'misc'
        
        # Créer et sauvegarder la métrique avec l'ID numérique de l'utilisateur
        metric = Metric()
        metric.name = metric_name
        metric.category = category
        metric.status = status
        metric.data = data
        metric.response_time = response_time
        metric.created_at = datetime.datetime.now()
        metric.customer_id = customer_id
        
        # Utilisation de l'ID numérique pour la compatibilité
        if current_user and current_user.is_authenticated and hasattr(current_user, 'numeric_id'):
            metric.user_id = current_user.numeric_id
        db.session.add(metric)
        db.session.commit()
        
        # Journal des métriques importantes ou des erreurs uniquement
        if status is False:
            logging.error(f"Metric Error: {metric_name} - {json.dumps(data)}")
        else:
            logging.info(f"Metric: {metric_name} ({category}) - Status: {status}")
            
        return metric
    except Exception as e:
        logging.error(f"Failed to log metric {metric_name}: {e}")
        db.session.rollback()
        return None

@app.route('/change_language/<string:lang>')
def change_language(lang):
    """Change the application language"""
    # Only accept valid languages from the supported list
    if lang not in get_supported_languages():
        lang = 'en'
    
    # Store the language in the session
    session['language'] = lang
    
    # Redirect back to the page they were on, but check if referrer is safe
    if request.referrer:
        from urllib.parse import urlparse
        parsed_url = urlparse(request.referrer)
        # Only redirect to URLs on the same site and with safe schemes
        if (parsed_url.scheme in ['http', 'https'] and 
            parsed_url.netloc == request.host and 
            not parsed_url.fragment.startswith('javascript:') and
            not parsed_url.path.startswith('//')):
            return redirect(request.referrer)
    # Default to index if referrer is missing or external
    return redirect(url_for('index'))

# This route was removed because it conflicted with another '/' route defined later
# @app.route('/')
# @login_required
# def index():
#     return render_template('index.html')

@app.route('/faq')
def faq():
    """Page de Foire Aux Questions (FAQ)"""
    return render_template('faq.html')

# Routes pour les pages légales
@app.route('/privacy')
def privacy_policy():
    """Politique de confidentialité"""
    return render_template('legal/privacy.html')

@app.route('/terms')
def terms_of_service():
    """Conditions générales d'utilisation"""
    return render_template('legal/terms.html')

@app.route('/cookies')
def cookies_policy():
    """Politique des cookies"""
    return render_template('legal/cookies.html')

@app.route('/legal')
def legal_notice():
    """Mentions légales"""
    return render_template('legal/legal_notice.html')

@app.route('/refund')
def refund_policy():
    """Politique de remboursement et programme de tokens"""
    return render_template('legal/refund.html')

@app.route('/boutique_language_settings/<int:boutique_id>', methods=['GET'])
@login_required
def boutique_language_settings(boutique_id):
    """Affiche les paramètres linguistiques d'une boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    supported_languages = get_supported_languages()
    
    return render_template('language_settings.html', 
                          boutique=boutique, 
                          supported_languages=supported_languages)

@app.route('/save_boutique_language_settings', methods=['POST'])
def save_boutique_language_settings():
    """Enregistre les paramètres linguistiques d'une boutique"""
    boutique_id = request.form.get('boutique_id', type=int)
    boutique = Boutique.query.get_or_404(boutique_id)
    
    # Récupérer les données du formulaire
    language = request.form.get('language', 'en')
    multilingual_enabled = request.form.get('multilingual_enabled') == 'on'
    supported_languages = request.form.getlist('supported_languages')
    
    # Vérifier que la langue principale est toujours dans les langues supportées
    if language not in supported_languages:
        supported_languages.append(language)
    
    # Mettre à jour la boutique
    boutique.language = language
    boutique.multilingual_enabled = multilingual_enabled
    boutique.supported_languages = supported_languages
    
    # Sauvegarder les changements
    db.session.commit()
    
    flash(_('Language settings updated successfully'), 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/campaign_language_settings/<int:campaign_id>', methods=['GET'])
@login_required
def campaign_language_settings(campaign_id):
    """Affiche les paramètres linguistiques d'une campagne"""
    campaign = Campaign.query.get_or_404(campaign_id)
    supported_languages = get_supported_languages()
    
    return render_template('campaign_language_settings.html', 
                          campaign=campaign, 
                          supported_languages=supported_languages,
                          get_campaign_target_languages=get_campaign_target_languages)

@app.route('/save_campaign_language_settings', methods=['POST'])
def save_campaign_language_settings():
    """Enregistre les paramètres linguistiques d'une campagne"""
    campaign_id = request.form.get('campaign_id', type=int)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Récupérer les données du formulaire
    language = request.form.get('language', 'en')
    multilingual_campaign = request.form.get('multilingual_campaign') == 'on'
    target_languages = request.form.getlist('target_languages')
    
    # Vérifier que la langue principale est toujours dans les langues cibles
    if language not in target_languages:
        target_languages.append(language)
    
    # Mettre à jour la campagne
    campaign.language = language
    campaign.multilingual_campaign = multilingual_campaign
    campaign.target_languages = target_languages
    
    # Sauvegarder les changements
    db.session.commit()
    
    flash(_('Campaign language settings updated successfully'), 'success')
    
    return redirect(url_for('edit_campaign', campaign_id=campaign.id))

@app.route('/dashboard')
@login_required
def dashboard():
    # Récupérer les données pour le tableau de bord filtrées par utilisateur connecté
    user_id = current_user.id
    
    # Filtrer les boutiques et niches par propriétaire
    boutiques = Boutique.query.filter_by(owner_id=user_id).all()
    niches = NicheMarket.query.filter_by(owner_id=user_id).all()
    
    # Récupérer les métriques pour les analyses (filtrer par user_id si disponible)
    try:
        # Convertir l'UUID en string si nécessaire
        user_id_str = str(user_id) if user_id else None
        
        persona_metrics = Metric.query.filter_by(name='persona_generation').filter(
            Metric.user_id.is_(None)
        ).order_by(Metric.created_at.desc()).limit(10).all()
        
        profile_metrics = Metric.query.filter_by(name='profile_generation').filter(
            Metric.user_id.is_(None)
        ).order_by(Metric.created_at.desc()).limit(10).all()
    except Exception as e:
        # En cas d'erreur, récupérer les métriques sans filtrer par user_id
        persona_metrics = Metric.query.filter_by(name='persona_generation').order_by(Metric.created_at.desc()).limit(10).all()
        profile_metrics = Metric.query.filter_by(name='profile_generation').order_by(Metric.created_at.desc()).limit(10).all()
    
    # Compter le nombre total d'éléments de l'utilisateur
    # Trouver les IDs des boutiques pour filtrer les clients et campagnes
    boutique_ids = [b.id for b in boutiques]
    
    # Filtrer les clients et campagnes par boutiques de l'utilisateur
    total_customers = Customer.query.filter(Customer.boutique_id.in_(boutique_ids) if boutique_ids else False).count()
    total_campaigns = Campaign.query.filter(Campaign.boutique_id.in_(boutique_ids) if boutique_ids else False).count()
    total_boutiques = len(boutiques)
    total_niches = len(niches)
    
    # Récupérer les dernières campagnes créées (uniquement celles de l'utilisateur)
    recent_campaigns = Campaign.query.filter(
        Campaign.boutique_id.in_(boutique_ids) if boutique_ids else False
    ).order_by(Campaign.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          boutiques=boutiques, 
                          niches=niches,
                          persona_metrics=persona_metrics,
                          profile_metrics=profile_metrics,
                          total_customers=total_customers,
                          total_campaigns=total_campaigns,
                          total_boutiques=total_boutiques,
                          total_niches=total_niches,
                          recent_campaigns=recent_campaigns)
                          
@app.route('/boutique_dashboard')
def boutique_dashboard():
    """Tableau de bord des performances de campagne par type de boutique"""
    # Récupérer les statistiques par boutique
    boutique_stats = Campaign.get_stats_by_boutique_type()
    
    # Récupérer les statistiques globales
    global_stats = Campaign.get_campaign_stats()
    
    # Récupérer les types de campagnes les plus performants par boutique
    for boutique in boutique_stats['boutiques']:
        if not boutique['campaigns_by_type']:
            boutique['top_campaign_type'] = None
            continue
            
        # Trouver le type de campagne avec le plus grand nombre
        top_type = max(boutique['campaigns_by_type'].items(), key=lambda x: x[1])
        boutique['top_campaign_type'] = {'type': top_type[0], 'count': top_type[1]}
    
    return render_template('boutique_dashboard_simple.html',
                          boutique_stats=boutique_stats,
                          global_stats=global_stats)



@app.route('/profiles', methods=['GET', 'POST'])
@app.route('/profiles/<int:page>', methods=['GET'])
@login_required
def profiles(page=1):
    if request.method == 'POST':
        niche_id = int(request.form.get('niche_id', 0))
        num_profiles = int(request.form.get('num_profiles', 5))
        persist_to_db = request.form.get('persist_to_db') == 'on'
        
        # Nouveaux paramètres
        target_country = request.form.get('target_country', '')
        age_range = request.form.get('age_range', '')
        income_level = request.form.get('income_level', '')
        
        try:
            # Generate customer profiles for the selected niche
            niche = NicheMarket.query.get(niche_id)
            if niche:
                # Generate profiles with AI with additional parameters
                generation_params = {
                    'target_country': target_country,
                    'age_range': age_range,
                    'income_level': income_level
                }
                
                customer_profiles = generate_customers(niche.name, niche.description, num_profiles, generation_params)
                
                # Log metric for profile generation
                log_metric("profile_generation", {
                    "success": True,
                    "niche_id": niche_id,
                    "niche_name": niche.name,
                    "count": len(customer_profiles),
                    "persist_to_db": persist_to_db,
                    "target_country": target_country,
                    "age_range": age_range,
                    "income_level": income_level
                })
                
                # Store profiles in the session
                session['customer_profiles'] = customer_profiles
                
                # If requested, persist profiles to the database
                if persist_to_db:
                    saved_profiles = 0
                    for profile_dict in customer_profiles:
                        # Create Customer objects and save to database
                        customer = Customer.from_profile_dict(profile_dict, niche_id)
                        db.session.add(customer)
                        saved_profiles += 1
                    
                    db.session.commit()
                    flash(f'Successfully generated and saved {saved_profiles} customer profiles', 'success')
                else:
                    flash('Successfully generated customer profiles (not saved to database)', 'success')
            else:
                flash('Invalid niche selected', 'danger')
                log_metric("profile_generation", {
                    "success": False,
                    "error": "Invalid niche selected",
                    "niche_id": niche_id
                })
        except Exception as e:
            flash(f'Error generating profiles: {str(e)}', 'danger')
            logging.error(f"Error generating profiles: {e}")
            log_metric("profile_generation", {
                "success": False,
                "error": str(e),
                "niche_id": niche_id
            })
        
        return redirect(url_for('profiles'))
    
    # Get data for the page
    niches = NicheMarket.query.all()
    customer_profiles = session.get('customer_profiles', [])
    
    # Configuration de la pagination
    per_page = 10  # Nombre de profils par page
    
    # Get saved profiles from database with pagination
    paginated_profiles = Customer.query.order_by(Customer.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('profiles.html', 
                           niches=niches, 
                           profiles=customer_profiles,
                           saved_profiles=paginated_profiles.items,
                           pagination=paginated_profiles)

@app.route('/generate_persona/<int:profile_index>', methods=['POST'])
@login_required
def generate_persona(profile_index):
    customer_profiles = session.get('customer_profiles', [])
    
    if not customer_profiles or profile_index >= len(customer_profiles):
        return jsonify({'error': 'Invalid profile'}), 400
    
    try:
        profile = customer_profiles[profile_index]
        persona = generate_customer_persona(profile)
        
        # Update the profile with the persona
        customer_profiles[profile_index]['persona'] = persona
        session['customer_profiles'] = customer_profiles
        
        # Log metric for persona generation
        log_metric("persona_generation", {
            "success": True,
            "profile_name": profile.get('name', 'Unknown'),
            "niche": profile.get('interests', ['Unknown'])[0] if profile.get('interests') else 'Unknown'
        })
        
        return jsonify({'success': True, 'persona': persona})
    except Exception as e:
        # Log metric for failed persona generation
        log_metric("persona_generation", {
            "success": False,
            "error": str(e)
        })
        
        logging.error(f"Error generating persona: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaigns', methods=['GET', 'POST'])
@login_required
def campaigns():
    if request.method == 'POST':
        profile_source = request.form.get('profile_source', 'session')
        campaign_type = request.form.get('campaign_type', 'email')
        niche_focus = request.form.get('niche_focus')
        find_products = request.form.get('find_products') == '1'
        
        # Obtenir le profil soit de la session, soit de la base de données
        profile = None
        if profile_source == 'session':
            profile_index = int(request.form.get('profile_index', 0))
            customer_profiles = session.get('customer_profiles', [])
            
            if not customer_profiles or profile_index >= len(customer_profiles):
                flash('Invalid profile selected', 'danger')
                return redirect(url_for('campaigns'))
            
            profile = customer_profiles[profile_index]
            customer_id = None
        else:
            # Profil de la base de données
            customer_id = int(request.form.get('customer_id', 0))
            customer = Customer.query.get(customer_id)
            
            if not customer:
                flash('Invalid customer selected', 'danger')
                return redirect(url_for('campaigns'))
            
            # Utiliser les données de profil stockées ou convertir l'objet en dictionnaire
            profile = customer.profile_data if customer.profile_data else {
                'name': customer.name,
                'age': customer.age,
                'location': customer.location,
                'gender': customer.gender,
                'language': customer.language,
                'interests': customer.get_interests_list(),
                'preferred_device': customer.preferred_device,
                'persona': customer.persona
            }
        
        try:
            # Générer le contenu marketing personnalisé
            content = generate_marketing_content(profile, campaign_type)
            
            # Log metric pour la génération de contenu marketing
            log_metric("marketing_content_generation", {
                "success": True,
                "profile_name": profile.get('name', 'Unknown'),
                "campaign_type": campaign_type
            })
            
            # Générer une image pour la campagne si demandé
            image_prompt = request.form.get('image_prompt', '')
            image_url = None
            if image_prompt:
                image_url = generate_marketing_image(profile, image_prompt)
                
                # Log metric pour la génération d'image
                log_metric("marketing_image_generation", {
                    "success": True if image_url else False,
                    "prompt": image_prompt
                })
            
            # Déterminer la niche pour la recherche de produits
            selected_niche = None
            if niche_focus:
                selected_niche = NicheMarket.query.get(niche_focus)
            elif profile.get('interests'):
                # Auto-détecter la niche depuis les intérêts du client
                interests = profile.get('interests', [])
                if interests:
                    niche_name = interests[0] if isinstance(interests, list) else interests
                    selected_niche = NicheMarket.query.filter(
                        NicheMarket.name.ilike(f'%{niche_name}%')
                    ).first()
            
            # Créer et sauvegarder la campagne
            campaign = Campaign(
                title=request.form.get('title', f"Campaign for {profile.get('name', 'Customer')}"),
                content=content,
                campaign_type=campaign_type,
                profile_data=profile,
                image_url=image_url,
                customer_id=customer_id,
                owner_id=current_user.id,
                generation_params={
                    "niche_focus": selected_niche.name if selected_niche else None,
                    "generation_timestamp": datetime.datetime.now().isoformat()
                }
            )
            db.session.add(campaign)
            db.session.commit()
            
            # Rechercher des produits similaires si demandé
            if find_products and selected_niche:
                try:
                    from aliexpress_search import search_similar_products
                    product_description = f"{campaign_type} for {selected_niche.name}"
                    if selected_niche.description:
                        product_description += f" - {selected_niche.description}"
                    
                    similar_products = search_similar_products(
                        product_description,
                        campaign.id,
                        niche=selected_niche.name,
                        max_results=3
                    )
                    
                    if similar_products:
                        flash(f'Campaign created with {len(similar_products)} relevant products found', 'success')
                    else:
                        flash('Campaign created successfully', 'success')
                except Exception as e:
                    logging.error(f"Error finding products for campaign: {e}")
                    flash('Campaign created successfully (product search unavailable)', 'success')
            else:
                flash('Campaign created successfully', 'success')
            
            # Rediriger vers la page de détail de la campagne
            return redirect(url_for('view_campaign', campaign_id=campaign.id))
        except Exception as e:
            flash(f'Error creating campaign: {str(e)}', 'danger')
            logging.error(f"Error creating campaign: {e}")
            
            # Log metric pour l'échec de génération
            log_metric("marketing_content_generation", {
                "success": False,
                "error": str(e),
                "campaign_type": campaign_type
            })
        
        return redirect(url_for('campaigns'))
    
    # GET request - afficher la page des campagnes
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    customer_profiles = session.get('customer_profiles', [])
    
    # Récupérer TOUS les clients pour le moment (debugging)
    # TODO: Rétablir le filtrage par owner_id une fois les migrations terminées
    saved_customers = Customer.query.order_by(
        # Prioriser ceux avec persona ET avatar
        (Customer.persona.isnot(None) & Customer.avatar_url.isnot(None)).desc(),
        # Puis ceux avec persona seulement
        Customer.persona.isnot(None).desc(),
        # Puis par nom
        Customer.name
    ).all()
    
    # Récupérer les niches pour la sélection  
    # TODO: Rétablir le filtrage par owner_id une fois les migrations terminées
    niches = NicheMarket.query.all()
    
    # Vérifier s'il y a des profils disponibles (session ou base de données)
    has_profiles = len(customer_profiles) > 0 or len(saved_customers) > 0
    
    return render_template('campaigns.html', 
                          campaigns=campaigns, 
                          profiles=customer_profiles,
                          saved_customers=saved_customers,
                          niches=niches,
                          has_profiles=has_profiles)

@app.route('/api/boutiques', methods=['POST'])
@login_required
def create_boutique():
    data = request.json
    try:
        # Créer la boutique avec le propriétaire actuel
        boutique = Boutique(
            name=data.get('name'),
            description=data.get('description'),
            target_demographic=data.get('target_demographic'),
            owner_id=current_user.id  # Associer la boutique à l'utilisateur connecté
        )
        db.session.add(boutique)
        db.session.commit()
        
        # Enregistrer l'activité utilisateur
        from models import UserActivity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="create_boutique",
            description=f"Création de la boutique: {boutique.name}"
        )
        db.session.add(activity)
        
        return jsonify({'id': boutique.id, 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches', methods=['POST'])
@login_required
def create_niche():
    data = request.json
    try:
        niche = NicheMarket(
            name=data.get('name'),
            description=data.get('description'),
            key_characteristics=data.get('key_characteristics'),
            owner_id=current_user.id  # Associer le niche au propriétaire actuel
        )
        db.session.add(niche)
        db.session.commit()
        
        # Enregistrer l'activité utilisateur
        from models import UserActivity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="create_niche",
            description=f"Création du créneau de marché: {niche.name}"
        )
        db.session.add(activity)
        return jsonify({'id': niche.id, 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches/<int:niche_id>', methods=['PUT'])
def edit_niche(niche_id):
    """Modifier une niche de marché via API"""
    data = request.json
    niche = NicheMarket.query.get_or_404(niche_id)
    
    try:
        if data.get('name'):
            niche.name = data.get('name')
        if data.get('description') is not None:
            niche.description = data.get('description')
        if data.get('key_characteristics') is not None:
            niche.key_characteristics = data.get('key_characteristics')
        
        niche.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'id': niche.id, 
            'name': niche.name,
            'status': 'success'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches/<int:niche_id>', methods=['DELETE'])
def delete_niche(niche_id):
    """Supprimer une niche de marché via API"""
    niche = NicheMarket.query.get_or_404(niche_id)
    
    try:
        # Vérifier s'il y a des clients associés
        customers_count = Customer.query.filter_by(niche_market_id=niche_id).count()
        
        if customers_count > 0:
            return jsonify({
                'error': f'Cannot delete niche: {customers_count} customer(s) are associated with it.',
                'status': 'error'
            }), 400
        
        db.session.delete(niche)
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error'}), 400

@app.route('/customer/<int:customer_id>')
@login_required
def view_customer(customer_id):
    """Afficher les détails d'un client spécifique"""
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customer_detail.html', customer=customer)

@app.route('/customer/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Modifier les informations d'un client"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs du client
            customer.name = request.form.get('name', customer.name)
            customer.age = request.form.get('age', customer.age)
            customer.location = request.form.get('location', customer.location)
            customer.country_code = request.form.get('country_code', customer.country_code)
            customer.gender = request.form.get('gender', customer.gender)
            customer.language = request.form.get('language', customer.language)
            customer.interests = request.form.get('interests', customer.interests)
            customer.preferred_device = request.form.get('preferred_device', customer.preferred_device)
            customer.persona = request.form.get('persona', customer.persona)
            
            # Nouveaux champs
            customer.occupation = request.form.get('occupation', customer.occupation)
            customer.education = request.form.get('education', customer.education)
            customer.income_level = request.form.get('income_level', customer.income_level)
            customer.shopping_frequency = request.form.get('shopping_frequency', customer.shopping_frequency)
            
            # Niche de marché
            niche_market_id = request.form.get('niche_market_id')
            if niche_market_id:
                customer.niche_market_id = int(niche_market_id)
            else:
                customer.niche_market_id = None
            
            # Si des données JSON sont soumises, les traiter
            profile_data = request.form.get('profile_data')
            if profile_data:
                try:
                    customer.profile_data = json.loads(profile_data)
                except json.JSONDecodeError:
                    flash('Invalid JSON format for profile data', 'danger')
            
            db.session.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('view_customer', customer_id=customer.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    # GET request - afficher le formulaire de modification
    niches = NicheMarket.query.all()
    return render_template('customer_edit.html', customer=customer, niches=niches)

@app.route('/customer/<int:customer_id>/delete', methods=['GET', 'POST'])
def delete_customer(customer_id):
    """Supprimer un client"""
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Client supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du client: {str(e)}', 'danger')
    return redirect(url_for('profiles'))

@app.route('/generate_customer_persona/<int:customer_id>', methods=['POST'])
def generate_customer_persona_db(customer_id):
    """Générer un persona pour un client dans la base de données"""
    from boutique_ai import generate_enhanced_customer_data_async, AsyncOpenAI, grok_client
    import asyncio
    import traceback
    import persona_manager  # Importer le module de gestion des personas
    from models import CustomerPersona, CustomerPersonaAssociation
    
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        # Incrémenter le compteur d'utilisation du profil
        customer.usage_count = (customer.usage_count or 0) + 1
        
        # Préparer les données du profil pour la génération
        profile = customer.profile_data if customer.profile_data else {
            'name': customer.name,
            'age': customer.age,
            'location': customer.location,
            'gender': customer.gender,
            'language': customer.language,
            'interests': customer.get_interests_list(),
            'preferred_device': customer.preferred_device,
            'id': customer.id  # Ajouter l'ID pour permettre les mises à jour des attributs supplémentaires
        }
        
        # Récupérer le nom de la niche associée au client
        niche_name = "general boutique"
        if customer.niche_market:
            niche_name = customer.niche_market.name
        
        # Récupérer les personas existants pour éviter la répétition
        existing_personas = []
        other_customers = Customer.query.filter(Customer.id != customer_id, Customer.persona != None).order_by(Customer.created_at.desc()).limit(5).all()
        for other in other_customers:
            if other.persona:
                existing_personas.append(other.persona)
        
        # Utiliser asyncio pour exécuter la génération asynchrone
        async def generate_data():
            return await generate_enhanced_customer_data_async(
                client=grok_client,
                customer=profile,
                niche=niche_name,
                existing_personas=existing_personas,
                boutique_info=None if not customer.boutique_id else {
                    "name": customer.boutique.name if customer.boutique else "",
                    "description": customer.boutique.description if customer.boutique else "",
                    "target_demographic": customer.boutique.target_demographic if customer.boutique else ""
                }
            )
        
        # Exécuter la fonction asynchrone
        enhanced_data = asyncio.run(generate_data())
        
        # Mettre à jour le client avec les nouvelles données enrichies
        customer.persona = enhanced_data["persona"]
        customer.niche_attributes = enhanced_data["niche_attributes"]
        customer.purchased_products = enhanced_data["purchased_products"]
        
        # Pour l'avatar, nous allons générer l'image avec le prompt fourni
        # Mais comme la génération d'image prend du temps, nous allons d'abord stocker le prompt
        customer.avatar_prompt = enhanced_data["avatar_prompt"]
        
        db.session.commit()
        
        # Créer un persona structuré et l'associer au client
        try:
            # Vérifier si un persona principal existe déjà pour ce client
            existing_primary = CustomerPersonaAssociation.query.filter_by(
                customer_id=customer.id,
                is_primary=True
            ).first()
            
            # Si un persona principal existe déjà, le mettre à jour
            if existing_primary:
                persona = existing_primary.persona
                # Mettre à jour les champs du persona
                persona.description = enhanced_data["persona"]
                persona.niche_specific_attributes = enhanced_data["niche_attributes"]
                persona.avatar_prompt = enhanced_data["avatar_prompt"]
                
                # Extraire les valeurs spécifiques des attributs de niche si disponibles
                if customer.niche_attributes and isinstance(customer.niche_attributes, dict):
                    for key, value in customer.niche_attributes.items():
                        if key == "interests" and value:
                            persona.interests = value
                        elif key == "values" and value:
                            persona.values = value
                        elif key == "preferred_channels" and value:
                            persona.preferred_channels = value
                
                db.session.commit()
                logging.info(f"Persona existant mis à jour pour le client {customer.id}: {persona.id}")
                persona_id = persona.id
            else:
                # Créer un nouveau persona
                persona_title = f"Persona pour {customer.name}"
                
                # Extraire les attributs spécifiques pour le persona
                additional_data = {
                    'primary_goal': None,  # À compléter ultérieurement
                    'pain_points': None,  # À compléter ultérieurement
                    'age_range': f"{customer.age - 5}-{customer.age + 5}" if customer.age else None,
                    'gender_affinity': customer.gender,
                    'location_type': "Urbain" if customer.location and any(city in customer.location.lower() for city in ["paris", "lyon", "marseille", "lille", "bordeaux"]) else "Périurbain",
                    'income_bracket': customer.income_level,
                    'education_level': customer.education,
                    'niche_specific_attributes': enhanced_data["niche_attributes"],
                    'avatar_prompt': enhanced_data["avatar_prompt"]
                }
                
                # Créer le persona
                new_persona = persona_manager.create_persona_from_text(
                    title=persona_title,
                    description=enhanced_data["persona"],
                    niche_market_id=customer.niche_market_id,
                    boutique_id=customer.boutique_id,
                    additional_data=additional_data
                )
                
                # Assigner le persona au client
                assoc = persona_manager.assign_persona_to_customer(
                    customer_id=customer.id,
                    persona_id=new_persona.id,
                    is_primary=True,
                    relevance_score=1.0,
                    notes="Persona généré automatiquement"
                )
                
                logging.info(f"Nouveau persona créé et assigné au client {customer.id}: {new_persona.id}")
                persona_id = new_persona.id
        except Exception as persona_error:
            logging.error(f"Erreur lors de la création du persona structuré: {persona_error}\n{traceback.format_exc()}")
            # Ne pas échouer toute la requête si cette partie échoue
        
        # Log metric pour la génération de persona
        log_metric("persona_generation", {
            "success": True,
            "customer_id": customer.id,
            "profile_name": customer.name,
            "enhanced": True,
            "avatar_prompt_generated": True
        })
        
        return jsonify({
            'success': True, 
            'persona': enhanced_data["persona"],
            'niche_attributes': enhanced_data["niche_attributes"],
            'purchased_products': enhanced_data["purchased_products"],
            'avatar_prompt': enhanced_data["avatar_prompt"]
        })
    except Exception as e:
        db.session.rollback()
        # Log metric pour l'échec de génération
        log_metric("persona_generation", {
            "success": False,
            "customer_id": customer.id,
            "error": str(e)
        })
        
        logging.error(f"Error generating enhanced persona for customer {customer_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>')
def view_campaign(campaign_id):
    """Afficher les détails d'une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('campaign_detail.html', campaign=campaign)

@app.route('/campaign/<int:campaign_id>/generate-image', methods=['GET', 'POST'])
def generate_campaign_image(campaign_id):
    """Générer ou régénérer une image pour une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    
    try:
        # Récupérer le profil client associé
        customer = campaign.customer
        
        # Créer un profil, même générique si pas de client
        if customer:
            profile = {
                "name": customer.name,
                "age": customer.age,
                "location": customer.location,
                "language": customer.language,
                "interests": customer.get_interests_list() if hasattr(customer, 'get_interests_list') else customer.interests,
                "occupation": customer.occupation if hasattr(customer, 'occupation') else "Non spécifié",
                "avatar_url": customer.avatar_url
            }
        else:
            # Créer un profil générique pour les campagnes sans client
            profile = {
                "name": "Utilisateur",
                "age": 30,
                "location": "France",
                "language": "fr",
                "interests": [campaign.campaign_type or "marketing"],
                "occupation": "Client potentiel",
                "avatar_url": None
            }
        
        # Générer un prompt si aucun n'est déjà défini
        image_prompt = campaign.image_prompt
        if not image_prompt:
            # Générer un prompt à partir du contenu de la campagne et du profil client
            from boutique_ai import generate_image_prompt_from_content
            image_prompt = generate_image_prompt_from_content(
                campaign_content=campaign.content,
                campaign_type=campaign.campaign_type,
                customer_profile=profile
            )
        
        # Générer l'image
        image_url = generate_marketing_image(profile, image_prompt)
        
        # Mettre à jour la campagne
        campaign.image_url = image_url
        campaign.image_prompt = image_prompt
        db.session.commit()
        
        # Journal des métriques
        log_metric(
            metric_name="campaign_image_generation",
            data={
                "campaign_id": campaign.id,
                "prompt": image_prompt
            },
            category="generation",
            status=True
        )
        
        flash(_("Image de campagne générée avec succès"), 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la génération de l'image de campagne: {e}")
        flash(_("Erreur lors de la génération de l'image: {}").format(str(e)), 'danger')
    
    return redirect(url_for('view_campaign', campaign_id=campaign_id))

@app.route('/campaign/<int:campaign_id>/delete', methods=['GET', 'POST'])
def delete_campaign(campaign_id):
    """Supprimer une campagne"""
    campaign = Campaign.query.get_or_404(campaign_id)
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash('Campagne supprimée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression de la campagne: {str(e)}', 'danger')
    return redirect(url_for('campaigns'))

@app.route('/generate_customer_avatar/<int:customer_id>', methods=['POST'])
def generate_customer_avatar(customer_id):
    """Générer un avatar pour un client basé sur son persona et ses attributs"""
    from boutique_ai import generate_boutique_image_async, AsyncOpenAI, grok_client, GROK_2_IMAGE
    import asyncio
    
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        # Incrémenter le compteur d'utilisation du profil
        customer.usage_count = (customer.usage_count or 0) + 1
        
        # Vérifier si le client a un avatar_prompt
        if not customer.avatar_prompt:
            return jsonify({
                'error': 'Ce client n\'a pas de prompt d\'avatar. Veuillez d\'abord générer un persona.'
            }), 400
        
        # Utiliser asyncio pour exécuter la génération d'image asynchrone
        async def generate_avatar():
            # Ajouter les informations de la boutique au prompt
            boutique_info = None
            if customer.boutique_id:
                try:
                    boutique = customer.boutique
                    if boutique:
                        boutique_info = {
                            "name": boutique.name,
                            "description": boutique.description,
                            "target_demographic": boutique.target_demographic
                        }
                        # Enrichir le prompt avec des informations de la boutique
                        enhanced_prompt = f"{customer.avatar_prompt} This avatar should reflect the style and aesthetic of '{boutique.name}' boutique, which is {boutique.description}."
                    else:
                        enhanced_prompt = customer.avatar_prompt
                except Exception as e:
                    logging.warning(f"Could not retrieve boutique information: {e}")
                    enhanced_prompt = customer.avatar_prompt
            else:
                enhanced_prompt = customer.avatar_prompt
                
            # Générer l'image avec les informations de contexte enrichies
            try:
                avatar_url = await generate_boutique_image_async(
                    client=grok_client,
                    image_prompt=enhanced_prompt,
                    model=GROK_2_IMAGE
                )
                # Vérifier si c'est une URL d'erreur (placeholder)
                if avatar_url.startswith("https://placehold.co") or "Error" in avatar_url:
                    raise Exception("L'image n'a pas pu être générée correctement. Le service d'IA a retourné une erreur.")
                return avatar_url
            except Exception as img_error:
                logging.error(f"Error in avatar generation API call: {img_error}")
                error_details = str(img_error)
                if "400" in error_details or "invalid_request_error" in error_details:
                    raise Exception("Le contenu du prompt n'est pas accepté par l'API image. Veuillez régénérer le persona.")
                elif "429" in error_details or "rate limit" in error_details.lower():
                    raise Exception("Limite de requêtes atteinte. Veuillez réessayer dans quelques minutes.")
                else:
                    raise Exception(f"Erreur lors de la génération de l'avatar: {error_details}")
        
        # Exécuter la fonction asynchrone
        avatar_url = asyncio.run(generate_avatar())
        
        # Mettre à jour le client avec l'URL de l'avatar
        customer.avatar_url = avatar_url
        db.session.commit()
        
        # Log metric pour la génération d'avatar
        log_metric("avatar_generation", {
            "success": True,
            "customer_id": customer.id,
            "profile_name": customer.name
        })
        
        return jsonify({
            'success': True, 
            'avatar_url': avatar_url
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        # Log metric pour l'échec de génération
        log_metric("avatar_generation", {
            "success": False,
            "customer_id": customer.id,
            "profile_name": customer.name,
            "error": error_msg,
            "stack_trace": stack_trace[:500]  # Tronquer pour éviter les entrées trop longues
        }, category="generation", status=False)
    
        logging.error(f"Error generating avatar for customer {customer_id}: {e}\n{stack_trace}")
        
        # Formater un message d'erreur plus convivial
        user_friendly_error = error_msg
        if "API key" in error_msg.lower() or "openai" in error_msg.lower():
            user_friendly_error = "Problème de connexion avec le service d'IA. Veuillez vérifier les clés API."
        elif "timeout" in error_msg.lower():
            user_friendly_error = "Le délai d'attente a été dépassé. Veuillez réessayer."
        elif "exceeded" in error_msg.lower() or "quota" in error_msg.lower():
            user_friendly_error = "Quota d'utilisation dépassé. Veuillez réessayer plus tard."
        
        return jsonify({
            'success': False,
            'error': user_friendly_error,
            'details': error_msg
        }), 500

@app.route('/profile')
@login_required
def user_profile_config():
    """Page de configuration du profil utilisateur"""
    # Générer le code de parrainage si nécessaire
    if not current_user.referral_code:
        current_user.generate_referral_code()
        db.session.commit()
    
    # Calculer les statistiques de l'utilisateur
    user_stats = {
        'total_campaigns': Campaign.query.filter_by(owner_id=current_user.numeric_id).count() if current_user.numeric_id else 0,
        'total_customers': Customer.query.filter_by(owner_id=current_user.numeric_id).count() if current_user.numeric_id else 0,
        'total_products': Product.query.filter_by(owner_id=current_user.numeric_id).count() if current_user.numeric_id else 0,
    }
    
    # URL complète du lien de parrainage
    referral_url = url_for('register', ref=current_user.referral_code, _external=True) if current_user.referral_code else None
    
    return render_template('profile_config.html', 
                         user=current_user, 
                         user_stats=user_stats,
                         referral_url=referral_url)

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Route pour supprimer un compte utilisateur"""
    try:
        user_id = current_user.id
        
        # Supprimer toutes les données associées à l'utilisateur
        # (Les contraintes CASCADE s'occupent de la suppression en cascade)
        db.session.delete(current_user)
        db.session.commit()
        
        flash('Your account has been successfully deleted.', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting account: {e}")
        flash('An error occurred while deleting your account. Please try again.', 'danger')
        return redirect(url_for('user_profile_config'))

@app.route('/images/<filename>')
def serve_generated_image(filename):
    """Sert les images générées par IA stockées localement"""
    from flask import send_from_directory
    from pathlib import Path
    
    try:
        # Chemin vers le répertoire de stockage des images
        image_dir = Path("generated_images")
        
        # Vérifier dans les sous-dossiers
        for subdir in ["avatars", "campaigns", "products", "."]:
            full_path = image_dir / subdir / filename
            if full_path.exists():
                return send_from_directory(str(image_dir / subdir), filename)
        
        # Si le fichier n'est pas trouvé
        return "Image not found", 404
        
    except Exception as e:
        logging.error(f"Erreur lors du service d'image {filename}: {str(e)}")
        return "Error serving image", 500

@app.route('/api/images/gallery/<user_id>')
@login_required
def get_user_image_gallery(user_id):
    """API pour récupérer la galerie d'images d'un utilisateur"""
    from integrated_image_service import integrated_image_service
    
    try:
        # Vérifier que l'utilisateur peut accéder à ces images
        if current_user.id != user_id and current_user.role != 'admin':
            return jsonify({"success": False, "error": "Accès non autorisé"}), 403
        
        image_type = request.args.get('type', None)
        limit = int(request.args.get('limit', 20))
        
        result = integrated_image_service.get_user_image_gallery(user_id, image_type, limit)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération de la galerie: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/stats')
@login_required
def get_storage_statistics():
    """API pour les statistiques de stockage d'images"""
    from integrated_image_service import integrated_image_service
    
    if current_user.role != 'admin':
        return jsonify({"success": False, "error": "Accès administrateur requis"}), 403
    
    result = integrated_image_service.get_storage_statistics()
    return jsonify(result)

@app.route('/admin/database-replication')
@login_required
def database_replication_status():
    """Page d'administration de la réplication de base de données"""
    if current_user.role != 'admin':
        flash('Accès administrateur requis', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from database_replication_setup import db_replication
        
        # Obtenir les statistiques de réplication
        db_stats = db_replication.get_database_stats()
        replication_test = db_replication.test_replication_lag()
        
        # Analytics récentes
        user_analytics = db_replication.execute_analytics_query(
            "SELECT COUNT(*) as total_users, COUNT(CASE WHEN last_login_at > NOW() - INTERVAL '7 days' THEN 1 END) as active_users FROM users"
        )
        
        campaign_analytics = db_replication.execute_analytics_query(
            "SELECT COUNT(*) as total_campaigns, COUNT(CASE WHEN created_at > NOW() - INTERVAL '30 days' THEN 1 END) as recent_campaigns FROM campaign"
        )
        
        return render_template('admin/database_replication.html',
                             db_stats=db_stats,
                             replication_test=replication_test,
                             user_analytics=user_analytics[0] if user_analytics else None,
                             campaign_analytics=campaign_analytics[0] if campaign_analytics else None)
        
    except Exception as e:
        logging.error(f"Erreur réplication DB: {str(e)}")
        flash(f'Erreur lors de la récupération des statistiques: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/admin/migrations')
@login_required
def migrations_management():
    """Page d'administration des migrations de base de données"""
    if current_user.role != 'admin':
        flash('Accès administrateur requis', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from automated_migration_system import MigrationManager
        
        manager = MigrationManager()
        migration_status = manager.get_migration_status()
        schema_validation = manager.validate_database_schema()
        
        return render_template('admin/migrations.html',
                             migration_status=migration_status,
                             schema_validation=schema_validation)
        
    except Exception as e:
        logging.error(f"Erreur migrations: {str(e)}")
        flash(f'Erreur lors de la récupération des migrations: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/api/admin/run-migrations', methods=['POST'])
@login_required
def run_migrations_api():
    """API pour exécuter les migrations en attente"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "error": "Accès administrateur requis"}), 403
    
    try:
        from automated_migration_system import MigrationManager
        
        manager = MigrationManager()
        results = manager.run_pending_migrations()
        
        # Log de l'activité d'administration
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='admin_migration',
            description=f'Exécution de migrations: {len(results["applied"])} appliquées, {len(results["failed"])} échecs',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            "success": len(results["failed"]) == 0,
            "results": results
        })
        
    except Exception as e:
        logging.error(f"Erreur exécution migrations: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/database-stats')
@login_required
def database_stats_api():
    """API pour les statistiques de base de données en temps réel"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "error": "Accès administrateur requis"}), 403
    
    try:
        from database_replication_setup import db_replication
        
        stats = db_replication.get_database_stats()
        replication_test = db_replication.test_replication_lag()
        
        return jsonify({
            "success": True,
            "database_stats": stats,
            "replication_status": replication_test
        })
        
    except Exception as e:
        logging.error(f"Erreur stats DB: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/service-worker.js')
def service_worker():
    """Sert le Service Worker"""
    from flask import send_from_directory
    return send_from_directory('static/js', 'service-worker.js', mimetype='application/javascript')

@app.route('/offline')
def offline_page():
    """Page hors ligne pour le Service Worker"""
    return render_template('offline.html')

@app.route('/api/customers/paginated')
@login_required
def customers_paginated():
    """API pour le chargement progressif des clients"""
    from progressive_loading_system import progressive_loader, search_filter_manager
    
    try:
        # Paramètres de pagination
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Paramètres de filtre
        search_term = request.args.get('search', '').strip()
        filters = {
            'language': request.args.get('language'),
            'gender': request.args.get('gender'),
            'age_range': request.args.get('age_range')
        }
        
        # Filtrer les valeurs vides
        filters = {k: v for k, v in filters.items() if v and v != 'all'}
        
        # Requête de base
        base_query = Customer.query.filter_by(owner_id=current_user.numeric_id) if current_user.numeric_id else Customer.query.filter_by(id=-1)
        
        # Appliquer les filtres
        filtered_query = search_filter_manager.apply_filters(
            base_query, 
            filters, 
            search_term, 
            ['name', 'location', 'interests']
        )
        
        # Paginer
        pagination_data = progressive_loader.paginate_query(
            filtered_query.order_by(Customer.created_at.desc()),
            page=page,
            per_page=per_page,
            endpoint='customers_paginated'
        )
        
        # Préparer la réponse
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Requête AJAX - renvoyer HTML des items
            items_html = render_template('partials/customer_items.html', customers=pagination_data['items'])
            
            return jsonify({
                "success": True,
                "items_html": items_html,
                "has_more": pagination_data['has_next'],
                "total_items": pagination_data['total'],
                "current_page": pagination_data['page'],
                "total_pages": pagination_data['pages']
            })
        else:
            # Requête normale - page complète
            return render_template('customers_progressive.html', 
                                 pagination=pagination_data,
                                 search_term=search_term,
                                 filters=filters)
        
    except Exception as e:
        logging.error(f"Erreur customers_paginated: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/campaigns/paginated')
@login_required
def campaigns_paginated():
    """API pour le chargement progressif des campagnes"""
    from progressive_loading_system import progressive_loader, search_filter_manager
    
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        search_term = request.args.get('search', '').strip()
        filters = {
            'status': request.args.get('status'),
            'campaign_type': request.args.get('campaign_type'),
            'boutique_id': request.args.get('boutique_id')
        }
        
        filters = {k: v for k, v in filters.items() if v and v != 'all'}
        
        base_query = Campaign.query.filter_by(owner_id=current_user.numeric_id) if current_user.numeric_id else Campaign.query.filter_by(id=-1)
        
        filtered_query = search_filter_manager.apply_filters(
            base_query, 
            filters, 
            search_term, 
            ['title', 'description', 'content']
        )
        
        pagination_data = progressive_loader.paginate_query(
            filtered_query.order_by(Campaign.created_at.desc()),
            page=page,
            per_page=per_page,
            endpoint='campaigns_paginated'
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            items_html = render_template('partials/campaign_items.html', campaigns=pagination_data['items'])
            
            return jsonify({
                "success": True,
                "items_html": items_html,
                "has_more": pagination_data['has_next'],
                "total_items": pagination_data['total'],
                "current_page": pagination_data['page'],
                "total_pages": pagination_data['pages']
            })
        else:
            return render_template('campaigns_progressive.html', 
                                 pagination=pagination_data,
                                 search_term=search_term,
                                 filters=filters)
        
    except Exception as e:
        logging.error(f"Erreur campaigns_paginated: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/image_generation', methods=['GET', 'POST'])
def image_generation():
    """Page de génération d'images marketing optimisées avec stockage persistant"""
    # Récupérer les clients sauvegardés pour la sélection
    saved_customers = Customer.query.order_by(Customer.name).all()
    
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')
            base_prompt = request.form.get('base_prompt', '')
            style = request.form.get('style', None)
            find_similar = request.form.get('find_similar_products') == 'on'
            image_data = None
            
            # Vérifier si une image a été téléchargée
            if 'reference_image' in request.files and request.files['reference_image'].filename:
                import base64
                from io import BytesIO
                
                # Lire le fichier image
                uploaded_file = request.files['reference_image']
                image_bytes = BytesIO(uploaded_file.read())
                
                # Encoder en base64
                image_data = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
            
            # Récupérer le profil client
            customer = Customer.query.get(customer_id)
            if not customer:
                flash('Client invalide sélectionné', 'danger')
                return redirect(url_for('image_generation'))
                
            # Incrémenter le compteur d'utilisation du profil
            customer.usage_count = (customer.usage_count or 0) + 1
            
            # Convertir le client en dictionnaire pour l'API
            profile = customer.profile_data if customer.profile_data else {
                'name': customer.name,
                'age': customer.age,
                'location': customer.location,
                'gender': customer.gender,
                'language': customer.language,
                'interests': customer.get_interests_list(),
                'preferred_device': customer.preferred_device,
                'persona': customer.persona
            }
            
            # Récupérer les métadonnées SEO fournies par l'utilisateur
            user_seo_keywords = request.form.get('seo_keywords', '')
            user_seo_alt_text = request.form.get('seo_alt_text', '')
            user_seo_title = request.form.get('seo_title', '')
            
            # Générer l'image et les métadonnées SEO
            image_result = generate_marketing_image(
                profile, 
                base_prompt, 
                image_data=image_data, 
                style=style,
                boutique_id=customer.boutique_id if customer.boutique_id else None
            )
            
            # Déterminer si nous avons reçu une simple URL ou un dictionnaire complet
            if isinstance(image_result, dict) and "url" in image_result:
                image_url = image_result["url"]
                # Combiner les métadonnées générées par l'IA avec celles de l'utilisateur
                seo_metadata = {
                    "alt_text": user_seo_alt_text or image_result.get("alt_text", ""),
                    "title": user_seo_title or image_result.get("title", ""),
                    "description": image_result.get("description", ""),
                    "keywords": [],
                    "prompt": image_result.get("prompt", base_prompt)
                }
                
                # Traiter les mots-clés (priorité à l'utilisateur, puis l'IA)
                if user_seo_keywords:
                    seo_metadata["keywords"] = [k.strip() for k in user_seo_keywords.split(',') if k.strip()]
                elif "keywords" in image_result and image_result["keywords"]:
                    seo_metadata["keywords"] = image_result["keywords"]
            else:
                # Compatible avec l'ancienne version qui retourne juste l'URL
                image_url = image_result
                
                # Extraire les mots-clés des intérêts du client si l'utilisateur n'en a pas fourni
                keywords = []
                if user_seo_keywords:
                    keywords = [k.strip() for k in user_seo_keywords.split(',') if k.strip()]
                else:
                    keywords = customer.get_interests_list()
                    if not keywords and customer.niche_market:
                        keywords = [customer.niche_market.name]
                
                # Combiner les métadonnées par défaut avec celles de l'utilisateur
                default_alt_text = f"Image marketing pour {customer.name} dans la niche {', '.join(keywords[:2]) if keywords else 'boutique'}"
                default_title = request.form.get('title', f"Image marketing pour {customer.name}")
                
                seo_metadata = {
                    "alt_text": user_seo_alt_text or default_alt_text,
                    "title": user_seo_title or default_title,
                    "description": f"Image générée avec le prompt: {base_prompt}",
                    "keywords": keywords,
                    "prompt": base_prompt
                }
            
            # Créer et sauvegarder la campagne avec l'image et les métadonnées SEO
            campaign = Campaign(
                title=request.form.get('title', f"Image marketing pour {customer.name}"),
                content=f"Image générée avec le prompt: {base_prompt}",
                campaign_type="image",
                profile_data=profile,
                image_url=image_url,
                image_alt_text=seo_metadata["alt_text"],
                image_title=seo_metadata["title"],
                image_description=seo_metadata["description"],
                image_keywords=seo_metadata["keywords"],
                image_prompt=seo_metadata["prompt"],
                customer_id=customer_id
            )
            db.session.add(campaign)
            db.session.commit()
            
            # Rechercher des produits similaires sur AliExpress si demandé
            similar_products = []
            if find_similar:
                try:
                    # Importer le module de recherche AliExpress
                    from aliexpress_search import search_similar_products
                    
                    # Extraire les intérêts du client comme niche
                    niche = ""
                    if customer.interests:
                        niche = customer.get_interests_list()[0]
                    
                    # Rechercher des produits similaires
                    similar_products = search_similar_products(
                        base_prompt, 
                        campaign.id,
                        niche=niche, 
                        max_results=3
                    )
                    
                    if similar_products:
                        flash(f'{len(similar_products)} produits similaires trouvés sur AliExpress', 'success')
                except Exception as e:
                    logging.error(f"Error searching similar products: {e}")
                    flash('Erreur lors de la recherche de produits similaires', 'warning')
            
            # Log metric pour la génération d'image
            log_metric("marketing_image_generation", {
                "success": True if image_url else False,
                "prompt": base_prompt,
                "customer_id": customer_id,
                "style": style,
                "similar_products_found": len(similar_products) if similar_products else 0
            })
            
            flash('Image marketing générée avec succès', 'success')
            return redirect(url_for('view_campaign', campaign_id=campaign.id))
            
        except Exception as e:
            flash(f'Erreur lors de la génération de l\'image: {str(e)}', 'danger')
            logging.error(f"Error generating marketing image: {e}")
            
            # Log metric pour l'échec de génération
            log_metric("marketing_image_generation", {
                "success": False,
                "error": str(e)
            })
    
    # Styles disponibles pour la génération d'images
    available_styles = [
        {"id": "watercolor", "name": "Aquarelle"},
        {"id": "oil_painting", "name": "Peinture à l'huile"},
        {"id": "photorealistic", "name": "Photoréaliste"},
        {"id": "sketch", "name": "Croquis"},
        {"id": "anime", "name": "Anime"},
        {"id": "3d_render", "name": "Rendu 3D"},
        {"id": "minimalist", "name": "Minimaliste"},
        {"id": "pop_art", "name": "Pop Art"}
    ]
    
    return render_template('image_generation.html',
                          saved_customers=saved_customers,
                          available_styles=available_styles)



# Routes pour la gestion des produits
@app.route('/products', methods=['GET'])
@login_required
def products():
    """Page de gestion des produits et génération de contenu"""
    # Récupérer les produits existants
    products_list = Product.query.order_by(Product.name).all()
    
    # Récupérer les clients pour le ciblage
    customers = Customer.query.order_by(Customer.name).all()
    
    # Récupérer les boutiques pour l'association des produits
    boutiques = Boutique.query.order_by(Boutique.name).all()
    
    return render_template('products.html',
                          products=products_list,
                          customers=customers,
                          boutiques=boutiques)

@app.route('/create_product', methods=['POST'])
def create_product():
    """Créer un nouveau produit"""
    try:
        # Créer le produit à partir des données du formulaire
        product = Product(
            name=request.form.get('name'),
            category=request.form.get('category'),
            price=float(request.form.get('price', 0)),
            base_description=request.form.get('base_description'),
            image_url=request.form.get('image_url')
        )
        
        # Associer à une boutique si spécifiée
        boutique_id = request.form.get('boutique_id')
        if boutique_id and boutique_id.isdigit():
            product.boutique_id = int(boutique_id)
        
        # Sauvegarder le produit
        db.session.add(product)
        db.session.commit()
        
        flash(f'Produit "{product.name}" créé avec succès', 'success')
        return redirect(url_for('view_product', product_id=product.id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la création du produit: {str(e)}', 'danger')
        logging.error(f"Error creating product: {e}")
        return redirect(url_for('products'))

@app.route('/product/<int:product_id>', methods=['GET'])
def view_product(product_id):
    """Afficher les détails d'un produit spécifique"""
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Modifier les informations d'un produit"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs du produit
            product.name = request.form.get('name', product.name)
            product.category = request.form.get('category')
            # Safely convert price to float with validation
            price_str = request.form.get('price', '0')
            # Check for NaN values in any capitalization
            if price_str.lower() == 'nan':
                flash('Prix invalide : valeur NaN non autorisée', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))
            try:
                product.price = float(price_str)
            except ValueError:
                flash('Prix invalide : veuillez entrer un nombre valide', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))
            product.base_description = request.form.get('base_description')
            product.image_url = request.form.get('image_url')
            
            # Associer à une boutique si spécifiée
            boutique_id = request.form.get('boutique_id')
            if boutique_id and boutique_id.isdigit():
                product.boutique_id = int(boutique_id)
            else:
                product.boutique_id = None
            
            # Associer à un public cible si spécifié
            target_audience_id = request.form.get('target_audience_id')
            if target_audience_id and target_audience_id.isdigit():
                product.target_audience_id = int(target_audience_id)
            else:
                product.target_audience_id = None
            
            # Mettre à jour les métadonnées SEO si fournies
            meta_title = request.form.get('meta_title')
            if meta_title:
                product.meta_title = meta_title
                
            meta_description = request.form.get('meta_description')
            if meta_description:
                product.meta_description = meta_description
                
            alt_text = request.form.get('alt_text')
            if alt_text:
                product.alt_text = alt_text
                
            keywords = request.form.get('keywords')
            if keywords:
                product.keywords = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # Sauvegarder les modifications
            db.session.commit()
            
            flash(f'Produit "{product.name}" mis à jour avec succès', 'success')
            return redirect(url_for('view_product', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du produit: {str(e)}', 'danger')
            logging.error(f"Error updating product: {e}")
    
    # GET request - afficher le formulaire d'édition
    boutiques = Boutique.query.order_by(Boutique.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('product_edit.html', 
                          product=product,
                          boutiques=boutiques,
                          customers=customers)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Supprimer un produit"""
    product = Product.query.get_or_404(product_id)
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Produit "{product.name}" supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du produit: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/generate_product_content', methods=['POST'])
def generate_product_content():
    """Générer du contenu pour un produit (description, variantes, analyse comparative)"""
    try:
        product_id = request.form.get('product_id')
        product = Product.query.get_or_404(product_id)
        
        # Récupérer les options de génération
        generate_options = {
            "generate_description": request.form.get('generate_description') == '1',
            "generate_meta": request.form.get('generate_meta') == '1',
            "generate_variants": request.form.get('generate_variants') == '1',
            "generate_comparative": request.form.get('generate_comparative') == '1'
        }
        
        # Récupérer les instructions spécifiques
        instructions = request.form.get('generation_instructions', '')
        
        # Récupérer le public cible si spécifié
        target_audience = None
        target_audience_id = request.form.get('target_audience_id')
        if target_audience_id and target_audience_id.isdigit():
            customer = Customer.query.get(int(target_audience_id))
            if customer:
                target_audience = {
                    'name': customer.name,
                    'age': customer.age,
                    'location': customer.location,
                    'gender': customer.gender,
                    'interests': customer.get_interests_list(),
                    'persona': customer.persona
                }
                
                # Incrémenter le compteur d'utilisation du client
                customer.usage_count = (customer.usage_count or 0) + 1
                db.session.commit()
        
        # Préparation des données du produit
        product_data = {
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'price': product.price,
            'base_description': product.base_description
        }
        
        async def generate_content():
            try:
                # Générer le contenu principal
                content_result = await product_generator.generate_product_content(
                    product_data,
                    target_audience,
                    generate_options,
                    instructions
                )
                
                # Générer le HTML si demandé
                html_templates = None
                if request.form.get('generate_html') == '1':
                    html_templates = await product_generator.generate_product_html_templates(
                        {**product_data, **content_result},
                        "moyenne_gamme"  # Par défaut, ciblage moyen de gamme
                    )
                
                # Mettre à jour le produit avec le contenu généré
                if content_result:
                    if generate_options.get("generate_description"):
                        product.generated_title = content_result.get('generated_title')
                        product.generated_description = content_result.get('generated_description')
                    
                    if generate_options.get("generate_meta"):
                        product.meta_title = content_result.get('meta_title')
                        product.meta_description = content_result.get('meta_description')
                        product.alt_text = content_result.get('alt_text')
                        product.keywords = content_result.get('keywords')
                    
                    if generate_options.get("generate_variants"):
                        product.variants = content_result.get('variants')
                    
                    if generate_options.get("generate_comparative"):
                        product.comparative_analysis = content_result.get('comparative_analysis')
                
                # Ajouter le HTML généré si disponible
                if html_templates:
                    product.html_description = html_templates.get('html_description')
                    product.html_specifications = html_templates.get('html_specifications')
                    product.html_faq = html_templates.get('html_faq')
                
                # Si un client spécifique a été utilisé, mettre à jour la liaison
                if target_audience_id and target_audience_id.isdigit():
                    product.target_audience_id = int(target_audience_id)
                
                # Enregistrer les modifications
                db.session.commit()
            except Exception as e:
                logging.error(f"Error during async content generation: {e}")
                raise
        
        # Exécuter la génération en arrière-plan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_content())
        loop.close()
        
        # Log metric pour la génération
        log_metric("product_content_generation", {
            "success": True,
            "product_id": product.id,
            "product_name": product.name,
            "options": generate_options
        })
        
        flash('Contenu généré avec succès!', 'success')
        return redirect(url_for('view_product', product_id=product.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la génération du contenu: {str(e)}', 'danger')
        logging.error(f"Error generating product content: {e}")
        
        # Log metric pour l'échec de génération
        log_metric("product_content_generation", {
            "success": False,
            "error": str(e)
        })
        
        return redirect(url_for('products'))

@app.route('/export_product/<int:product_id>', methods=['GET'])
def export_product(product_id):
    """Exporter un produit au format JSON"""
    product = Product.query.get_or_404(product_id)
    
    # Créer un dictionnaire avec toutes les données du produit
    product_data = {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'price': product.price,
        'base_description': product.base_description,
        'generated_title': product.generated_title,
        'generated_description': product.generated_description,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
        'alt_text': product.alt_text,
        'keywords': product.get_keywords_list(),
        'variants': product.variants,
        'comparative_analysis': product.comparative_analysis,
        'image_url': product.image_url,
        'created_at': product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else None
    }
    
    # Ajouter les informations sur le public cible si disponible
    if product.target_audience:
        product_data['target_audience'] = {
            'id': product.target_audience.id,
            'name': product.target_audience.name,
            'age': product.target_audience.age,
            'location': product.target_audience.location,
            'gender': product.target_audience.gender
        }
    
    # Ajouter les informations sur la boutique si disponible
    if product.boutique:
        product_data['boutique'] = {
            'id': product.boutique.id,
            'name': product.boutique.name,
            'description': product.boutique.description
        }
    
    # Créer une réponse JSON avec le bon header pour le téléchargement
    response = jsonify(product_data)
    response.headers['Content-Disposition'] = f'attachment; filename=product_{product.id}.json'
    return response

# Routes pour l'importation AliExpress et l'export Shopify

@app.route('/import_aliexpress_form')
def import_aliexpress_form():
    """Afficher le formulaire d'importation de produits AliExpress"""
    boutiques = Boutique.query.all()
    customers = Customer.query.all()
    
    # Récupérer les 5 derniers imports
    recent_imports = (ImportedProduct.query
                     .order_by(ImportedProduct.imported_at.desc())
                     .limit(5)
                     .all())
    
    return render_template('product_import.html', 
                           boutiques=boutiques, 
                           customers=customers,
                           recent_imports=recent_imports)

@app.route('/import_aliexpress_product', methods=['POST'])
def import_aliexpress_product():
    """Importer et optimiser un produit depuis AliExpress"""
    try:
        aliexpress_url = request.form.get('aliexpress_url')
        product_name = request.form.get('product_name')
        target_market = request.form.get('target_market', 'moyenne_gamme')
        category = request.form.get('category')
        boutique_id = request.form.get('boutique_id')
        target_audience_id = request.form.get('target_audience_id')
        
        # Valider les entrées
        if not aliexpress_url or not product_name:
            flash('L\'URL AliExpress et le nom du produit sont obligatoires.', 'danger')
            return redirect(url_for('import_aliexpress_form'))
        
        # Convertir les IDs en entiers si nécessaire
        if boutique_id and boutique_id.isdigit():
            boutique_id = int(boutique_id)
        else:
            boutique_id = None
            
        if target_audience_id and target_audience_id.isdigit():
            target_audience_id = int(target_audience_id)
        else:
            target_audience_id = None
        
        # Créer le produit dans la base de données
        new_product = Product(
            name=product_name,
            category=category,
            boutique_id=boutique_id,
            target_audience_id=target_audience_id
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        # Créer l'entrée d'importation
        imported_product = ImportedProduct(
            product_id=new_product.id,
            source_url=aliexpress_url,
            source="aliexpress",
            import_status="processing",
            source_id=aliexpress_importer.extract_aliexpress_product_id(aliexpress_url),
            optimization_settings={
                "target_market": target_market,
                "optimize_seo": request.form.get('optimize_seo') == 'on',
                "optimize_price": request.form.get('optimize_price') == 'on',
                "generate_html": request.form.get('generate_html') == 'on',
                "generate_specs": request.form.get('generate_specs') == 'on',
                "generate_faq": request.form.get('generate_faq') == 'on',
                "generate_variants": request.form.get('generate_variants') == 'on'
            }
        )
        
        db.session.add(imported_product)
        db.session.commit()
        
        # Lancer l'importation en arrière-plan
        async def process_import_task():
            try:
                # Mettre à jour le statut
                imported_product.import_status = "processing"
                db.session.commit()
                
                # Extraire les données
                product_data = await aliexpress_importer.extract_aliexpress_product_data(aliexpress_url)
                imported_product.raw_data = product_data
                
                # Optimiser les prix
                pricing_data = await aliexpress_importer.optimize_pricing_strategy(product_data, target_market)
                imported_product.pricing_strategy = pricing_data
                imported_product.original_price = pricing_data.get('original_price', 0)
                imported_product.optimized_price = pricing_data.get('psychological_price', 0)
                imported_product.original_currency = product_data.get('devise', 'EUR')
                
                # Mettre à jour le produit avec les données extraites
                new_product.price = pricing_data.get('psychological_price', 0)
                if product_data.get('images_urls') and len(product_data.get('images_urls', [])) > 0:
                    new_product.image_url = product_data['images_urls'][0]
                new_product.base_description = product_data.get('description', '')
                
                # Générer le contenu HTML optimisé pour Shopify
                if imported_product.optimization_settings.get('generate_html'):
                    template_data = await aliexpress_importer.generate_shopify_html_template(product_data, pricing_data)
                    imported_product.templates = template_data
                    
                    # Mettre à jour les données du produit
                    new_product.meta_title = template_data.get('meta_title', '')
                    new_product.meta_description = template_data.get('meta_description', '')
                    new_product.alt_text = template_data.get('alt_text', '')
                    new_product.keywords = template_data.get('tags', [])
                    new_product.generated_title = template_data.get('meta_title', '')
                    
                    # Ajouter le HTML généré
                    if imported_product.optimization_settings.get('generate_html'):
                        new_product.html_description = template_data.get('html_description', '')
                    
                    if imported_product.optimization_settings.get('generate_specs'):
                        new_product.html_specifications = template_data.get('html_specifications', '')
                    
                    if imported_product.optimization_settings.get('generate_faq'):
                        new_product.html_faq = template_data.get('html_faq', '')
                
                # Finaliser l'importation
                imported_product.import_status = "complete"
                db.session.commit()
                
            except Exception as e:
                # En cas d'erreur, marquer l'importation comme échouée
                imported_product.import_status = "failed"
                imported_product.status_message = str(e)
                db.session.commit()
                logging.error(f"Error importing AliExpress product: {e}")
                raise
        
        # Lancer la tâche asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_import_task())
        loop.close()
        
        flash('Produit importé et optimisé avec succès!', 'success')
        return redirect(url_for('view_product', product_id=new_product.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'importation: {str(e)}', 'danger')
        logging.error(f"Error importing AliExpress product: {e}")
        return redirect(url_for('import_aliexpress_form'))

@app.route('/import_aliexpress_bulk', methods=['POST'])
def import_aliexpress_bulk():
    """Importer plusieurs produits AliExpress par lot"""
    bulk_urls = request.form.get('bulk_urls', '').strip().split('\n')
    bulk_category = request.form.get('bulk_category')
    bulk_boutique_id = request.form.get('bulk_boutique_id')
    
    if not bulk_urls or not bulk_urls[0]:
        flash('Veuillez entrer au moins une URL AliExpress.', 'danger')
        return redirect(url_for('import_aliexpress_form'))
    
    # Convertir l'ID de boutique en entier si nécessaire
    if bulk_boutique_id and bulk_boutique_id.isdigit():
        bulk_boutique_id = int(bulk_boutique_id)
    else:
        bulk_boutique_id = None
    
    imported_count = 0
    failed_count = 0
    
    for url in bulk_urls:
        url = url.strip()
        if not url:
            continue
            
        try:
            # Extraire l'ID du produit pour générer un nom temporaire
            product_id = aliexpress_importer.extract_aliexpress_product_id(url)
            temp_name = f"Produit AliExpress #{product_id}"
            
            # Créer le produit dans la base de données
            new_product = Product(
                name=temp_name,
                category=bulk_category,
                boutique_id=bulk_boutique_id
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            # Créer l'entrée d'importation
            imported_product = ImportedProduct(
                product_id=new_product.id,
                source_url=url,
                source="aliexpress",
                import_status="pending",
                source_id=product_id,
                optimization_settings={
                    "target_market": "moyenne_gamme",
                    "optimize_seo": True,
                    "optimize_price": True,
                    "generate_html": True,
                    "generate_specs": True,
                    "generate_faq": True,
                    "generate_variants": True
                }
            )
            
            db.session.add(imported_product)
            db.session.commit()
            
            imported_count += 1
            
        except Exception as e:
            failed_count += 1
            logging.error(f"Error in bulk import for URL {url}: {e}")
            continue
    
    if imported_count > 0:
        flash(f'{imported_count} produits ont été ajoutés à la file d\'importation. Ils seront traités en arrière-plan.', 'success')
    
    if failed_count > 0:
        flash(f'{failed_count} produits n\'ont pas pu être ajoutés à la file d\'importation.', 'warning')
    
    return redirect(url_for('products'))

@app.route('/shopify_export/<int:product_id>')
def shopify_export(product_id):
    """Afficher la page d'export Shopify pour un produit"""
    product = Product.query.get_or_404(product_id)
    return render_template('product_shopify_export.html', product=product)

@app.route('/update_product_html/<int:product_id>', methods=['POST'])
def update_product_html(product_id):
    """Mettre à jour le HTML d'un produit via AJAX"""
    try:
        data = request.get_json()
        section = data.get('section')
        content = data.get('content')
        
        product = Product.query.get_or_404(product_id)
        
        if section == 'description':
            product.html_description = content
        elif section == 'specifications':
            product.html_specifications = content
        elif section == 'faq':
            product.html_faq = content
        else:
            return jsonify({'success': False, 'error': 'Section non valide'})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error updating product HTML: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/export_product_json/<int:product_id>')
def export_product_json(product_id):
    """Exporter un produit au format JSON"""
    product = Product.query.get_or_404(product_id)
    
    # Créer un dictionnaire avec toutes les données du produit
    product_data = {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'price': product.price,
        'base_description': product.base_description,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
        'alt_text': product.alt_text,
        'keywords': product.get_keywords_list(),
        'html_description': product.html_description,
        'html_specifications': product.html_specifications,
        'html_faq': product.html_faq,
        'image_url': product.image_url,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None
    }
    
    # Générer le nom du fichier
    filename = f"product_{product.id}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Créer une réponse JSON téléchargeable
    response = make_response(json.dumps(product_data, indent=2, ensure_ascii=False))
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'application/json'
    
    return response

@app.route('/regenerate_product_content/<int:product_id>')
def regenerate_product_content(product_id):
    """Régénérer le contenu HTML d'un produit"""
    product = Product.query.get_or_404(product_id)
    
    # Vérifier si le produit a été importé depuis AliExpress
    imported_product = ImportedProduct.query.filter_by(product_id=product.id).first()
    
    if not imported_product or not imported_product.raw_data:
        flash('Impossible de régénérer le contenu: données source non disponibles.', 'danger')
        return redirect(url_for('shopify_export', product_id=product.id))
    
    try:
        # Régénérer le contenu en arrière-plan
        async def regenerate_content():
            try:
                # Récupérer les données
                product_data = imported_product.raw_data
                pricing_data = imported_product.pricing_strategy
                
                # Générer un nouveau template HTML
                template_data = await aliexpress_importer.generate_shopify_html_template(product_data, pricing_data)
                
                # Mettre à jour les templates stockés
                imported_product.templates = template_data
                
                # Mettre à jour les données du produit
                product.meta_title = template_data.get('meta_title', '')
                product.meta_description = template_data.get('meta_description', '')
                product.alt_text = template_data.get('alt_text', '')
                product.keywords = template_data.get('tags', [])
                product.html_description = template_data.get('html_description', '')
                product.html_specifications = template_data.get('html_specifications', '')
                product.html_faq = template_data.get('html_faq', '')
                
                # Sauvegarder les modifications
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error regenerating product content: {e}")
                raise
        
        # Exécuter la tâche asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(regenerate_content())
        loop.close()
        
        flash('Contenu régénéré avec succès!', 'success')
        
    except Exception as e:
        flash(f'Erreur lors de la régénération: {str(e)}', 'danger')
        logging.error(f"Error regenerating product content: {e}")
    
    return redirect(url_for('shopify_export', product_id=product.id))

# Routes supprimées pour la gestion des personas (fonctionnalité déplacée dans la page profil client)

@app.route('/seo_audit')
@login_required
def seo_audit_dashboard():
    """Tableau de bord d'audit SEO"""
    from models import SEOAudit, Boutique, Campaign, Product
    
    # Récupérer les derniers audits
    latest_audits = SEOAudit.query.order_by(SEOAudit.audit_date.desc()).limit(10).all()
    
    # Récupérer les boutiques, campagnes et produits pour le formulaire
    boutiques = Boutique.query.all()
    campaigns = Campaign.query.all()
    products = Product.query.all()
    
    return render_template(
        'seo_audit_dashboard.html',
        latest_audits=latest_audits,
        boutiques=boutiques,
        campaigns=campaigns,
        products=products
    )

@app.route('/run_seo_audit', methods=['POST'])
@login_required
def run_new_seo_audit():
    """Exécute un nouvel audit SEO"""
    import asyncio
    from seo_audit import run_seo_audit
    
    # Récupérer les paramètres
    boutique_id = request.form.get('boutique_id', type=int)
    campaign_id = request.form.get('campaign_id', type=int)
    product_id = request.form.get('product_id', type=int)
    locale = request.form.get('locale', 'fr_FR')
    
    # Vérifier qu'au moins un objet est spécifié
    if not (boutique_id or campaign_id or product_id):
        flash("Veuillez sélectionner une boutique, une campagne ou un produit à auditer.", "danger")
        return redirect(url_for('seo_audit_dashboard'))
    
    try:
        # Exécuter l'audit de manière asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audit_results = loop.run_until_complete(run_seo_audit(
            boutique_id=boutique_id,
            campaign_id=campaign_id,
            product_id=product_id,
            locale=locale
        ))
        loop.close()
        
        if audit_results.get("success", False):
            flash(f"Audit SEO terminé avec un score de {audit_results.get('global_score', 0)}/100.", "success")
        else:
            flash(f"L'audit SEO a échoué: {audit_results.get('error', 'Erreur inconnue')}", "danger")
        
        # Rediriger vers la page de détails si un ID d'audit est disponible
        if "audit_id" in audit_results:
            return redirect(url_for('view_seo_audit', audit_id=audit_results["audit_id"]))
        
    except Exception as e:
        flash(f"Erreur lors de l'exécution de l'audit SEO: {str(e)}", "danger")
    
    return redirect(url_for('seo_audit_dashboard'))

@app.route('/seo_audit/<int:audit_id>')
@login_required
def view_seo_audit(audit_id):
    """Affiche les détails d'un audit SEO"""
    from models import SEOAudit
    
    audit = SEOAudit.query.get_or_404(audit_id)
    
    # Récupérer l'objet audité
    audited_object = None
    audited_object_type = None
    
    if audit.boutique_id:
        audited_object = audit.boutique
        audited_object_type = "boutique"
    elif audit.campaign_id:
        audited_object = audit.campaign
        audited_object_type = "campaign"
    elif audit.product_id:
        audited_object = audit.product
        audited_object_type = "product"
    
    return render_template(
        'seo_audit_detail.html',
        audit=audit,
        audited_object=audited_object,
        audited_object_type=audited_object_type
    )

@app.route('/seo_keywords')
@login_required
def seo_keywords():
    """Page de gestion des mots-clés SEO"""
    from models import SEOKeyword, NicheMarket
    
    # Paramètres de filtre
    locale = request.args.get('locale', 'fr_FR')
    status = request.args.get('status')
    niche_id = request.args.get('niche_id', type=int)
    
    # Construire la requête
    query = SEOKeyword.query.filter_by(locale=locale)
    
    if status:
        query = query.filter_by(status=status)
    
    # Trier et récupérer les mots-clés
    keywords = query.order_by(SEOKeyword.last_updated.desc()).limit(100).all()
    
    # Récupérer les niches pour le filtrage
    niches = NicheMarket.query.all()
    
    # Si une niche est sélectionnée, récupérer les mots-clés recommandés
    recommended_keywords = []
    selected_niche = None
    
    if niche_id:
        from seo_audit import get_recommended_keywords
        selected_niche = NicheMarket.query.get(niche_id)
        if selected_niche:
            recommended_keywords = get_recommended_keywords(niche_id, locale)
    
    return render_template(
        'seo_keywords.html',
        keywords=keywords,
        niches=niches,
        selected_niche=selected_niche,
        recommended_keywords=recommended_keywords,
        locale=locale,
        status=status
    )

@app.route('/metrics_dashboard')
@app.route('/metrics')
def metrics_dashboard():
    """Page d'analyse des métriques de performance"""
    from models import Metric
    from datetime import datetime, timedelta
    from sqlalchemy import func, desc
    
    # Récupérer les paramètres de filtre
    category = request.args.get('category', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    limit_str = request.args.get('limit', '50')
    
    # Convertir et valider les dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    except ValueError:
        flash(_("Format de date de début invalide. Utilisation du format par défaut."), "warning")
        start_date = None
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if end_date:
            # Ajouter un jour pour inclure toute la journée de fin
            end_date = end_date + timedelta(days=1)
    except ValueError:
        flash(_("Format de date de fin invalide. Utilisation du format par défaut."), "warning")
        end_date = None
    
    # Convertir la limite
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 50
    
    # Construire la requête de base
    query = Metric.query
    
    # Appliquer les filtres
    if category:
        query = query.filter(Metric.category == category)
    if start_date:
        query = query.filter(Metric.created_at >= start_date)
    if end_date:
        query = query.filter(Metric.created_at <= end_date)
    
    # Récupérer le total des métriques (pour les statistiques)
    total_metrics = query.count()
    
    # Valeurs par défaut pour éviter les divisions par zéro
    success_count = 0
    error_count = 0
    success_rate = 0
    avg_time = 0
    category_labels = []
    category_counts = []
    time_labels = []
    time_values = []
    trend_dates = []
    trend_counts = []
    
    # Calculer les statistiques uniquement s'il y a des métriques
    if total_metrics > 0:
        # Récupérer les métriques pour l'affichage (triées par date et limitées)
        metrics = query.order_by(Metric.created_at.desc()).limit(limit).all()
        
        # Calculer les statistiques
        success_count = query.filter(Metric.status == True).count()
        error_count = total_metrics - success_count
        success_rate = (success_count / total_metrics * 100) if total_metrics > 0 else 0
        
        # Calculer le temps moyen
        avg_time_result = db.session.query(db.func.avg(Metric.execution_time)).filter(Metric.execution_time != None).scalar()
        avg_time = avg_time_result if avg_time_result is not None else 0
        
        # Données pour le graphique des catégories
        category_stats = db.session.query(
            Metric.category, db.func.count(Metric.id)
        ).group_by(Metric.category).all()
        
        category_labels = [cat[0] or _("Non catégorisé") for cat in category_stats]
        category_counts = [cat[1] for cat in category_stats]
        
        # Données détaillées pour les générations par type
        generation_stats = db.session.query(
            Metric.name, db.func.count(Metric.id)
        ).filter(
            Metric.category == 'generation'
        ).group_by(Metric.name).all()
        
        # Analyser les types de générations basés sur les noms des métriques
        generation_types = {
            'images': 0,
            'personas': 0,
            'campaigns': 0,
            'profiles': 0,
            'products': 0,
            'content': 0,
            'other': 0
        }
        
        for metric_name, count in generation_stats:
            metric_lower = metric_name.lower()
            if any(keyword in metric_lower for keyword in ['image', 'avatar', 'picture', 'photo']):
                generation_types['images'] += count
            elif any(keyword in metric_lower for keyword in ['persona', 'character', 'portrait']):
                generation_types['personas'] += count
            elif any(keyword in metric_lower for keyword in ['campaign', 'marketing', 'ad', 'promotion']):
                generation_types['campaigns'] += count
            elif any(keyword in metric_lower for keyword in ['profile', 'customer', 'client']):
                generation_types['profiles'] += count
            elif any(keyword in metric_lower for keyword in ['product', 'item', 'description']):
                generation_types['products'] += count
            elif any(keyword in metric_lower for keyword in ['content', 'text', 'copy', 'writing']):
                generation_types['content'] += count
            else:
                generation_types['other'] += count
        
        # Données pour le graphique des temps de réponse
        time_stats = db.session.query(
            Metric.name, db.func.avg(Metric.execution_time)
        ).filter(Metric.execution_time != None).group_by(Metric.name).order_by(db.func.avg(Metric.execution_time).desc()).limit(10).all()
        
        time_labels = [stat[0] for stat in time_stats]
        time_values = [float(stat[1]) for stat in time_stats]
        
        # Données pour le graphique de tendance (nombre de métriques par jour)
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        trend_stats = db.session.query(
            db.func.date_trunc('day', Metric.created_at).label('date'),
            db.func.count(Metric.id)
        ).filter(Metric.created_at >= week_ago).group_by('date').order_by('date').all()
        
        trend_dates = [stat[0].strftime('%m/%d') for stat in trend_stats]
        trend_counts = [stat[1] for stat in trend_stats]
        
        # Données de performance temporelle (métriques avec temps d'exécution)
        time_metrics = Metric.query.filter(
            Metric.execution_time.isnot(None),
            Metric.execution_time > 0
        ).order_by(Metric.execution_time.desc()).limit(10).all()
        
        time_labels = [m.name[:15] + '...' if len(m.name) > 15 else m.name for m in time_metrics]
        time_values = [float(m.execution_time) for m in time_metrics]
        
    else:
        # S'il n'y a pas de métriques, initialiser avec des listes vides
        metrics = []
        trend_dates = []
        trend_counts = []
        time_labels = []
        time_values = []
        generation_types = {
            'images': 0,
            'personas': 0,
            'campaigns': 0,
            'profiles': 0,
            'products': 0,
            'content': 0,
            'other': 0
        }
    
    # Fonction pour déterminer la couleur de la catégorie
    def get_category_color(category):
        if not category:
            return 'secondary'
        
        color_map = {
            'ai': 'primary',
            'generation': 'info',
            'user': 'success',
            'system': 'warning',
            'import': 'danger',
            'profile': 'primary',
            'persona': 'info',
            'boutique': 'success'
        }
        
        return color_map.get(category.lower(), 'secondary')
    
    return render_template(
        'metrics.html',
        metrics=metrics,
        total_metrics=total_metrics,
        success_count=success_count,
        error_count=error_count,
        success_rate=success_rate,
        avg_time=avg_time,
        category_labels=category_labels,
        category_counts=category_counts,
        time_labels=time_labels,
        time_values=time_values,
        trend_dates=trend_dates,
        trend_counts=trend_counts,
        generation_stats=generation_types,
        category=category,
        start_date=start_date_str,
        end_date=end_date_str,
        limit=limit,
        get_category_color=get_category_color
    )

# Routes pour la gestion des personas supprimées (fonctionnalité déplacée dans la page profil client)
# Conservez seulement la fonction get_persona pour l'API JSON
@app.route('/persona/<int:persona_id>')
def get_persona(persona_id):
    """Récupérer les détails d'un persona au format JSON"""
    try:
        from models import CustomerPersona
        
        persona = CustomerPersona.query.get_or_404(persona_id)
        
        # Récupérer les informations de niche et de boutique
        niche_market = None
        if persona.niche_market_id:
            niche = NicheMarket.query.get(persona.niche_market_id)
            if niche:
                niche_market = {
                    'id': niche.id,
                    'name': niche.name
                }
        
        boutique = None
        if persona.boutique_id:
            b = Boutique.query.get(persona.boutique_id)
            if b:
                boutique = {
                    'id': b.id,
                    'name': b.name
                }
        
        # Récupérer les clients associés
        customers = []
        for assoc in persona.customer_associations:
            customer = Customer.query.get(assoc.customer_id)
            if customer:
                customers.append({
                    'id': customer.id,
                    'name': customer.name,
                    'is_primary': assoc.is_primary,
                    'relevance_score': assoc.relevance_score,
                    'notes': assoc.notes
                })
        
        # Créer une réponse JSON avec les données du persona
        result = {
            'id': persona.id,
            'title': persona.title,
            'description': persona.description,
            'primary_goal': persona.primary_goal,
            'pain_points': persona.pain_points,
            'buying_triggers': persona.buying_triggers,
            'age_range': persona.age_range,
            'gender_affinity': persona.gender_affinity,
            'location_type': persona.location_type,
            'income_bracket': persona.income_bracket,
            'education_level': persona.education_level,
            'values': persona.values,
            'interests': persona.interests,
            'lifestyle': persona.lifestyle,
            'personality_traits': persona.personality_traits,
            'buying_habits': persona.buying_habits,
            'brand_affinities': persona.brand_affinities,
            'price_sensitivity': persona.price_sensitivity,
            'decision_factors': persona.decision_factors,
            'preferred_channels': persona.preferred_channels,
            'content_preferences': persona.content_preferences,
            'social_media_behavior': persona.social_media_behavior,
            'niche_specific_attributes': persona.niche_specific_attributes,
            'custom_fields': persona.custom_fields,
            'avatar_url': persona.avatar_url,
            'avatar_prompt': persona.avatar_prompt,
            'created_at': persona.created_at,
            'updated_at': persona.updated_at,
            'niche_market': niche_market,
            'boutique': boutique,
            'customers': customers
        }
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error getting persona details: {e}")
        return jsonify({'error': str(e)}), 500

with app.app_context():
    # Create tables
    db.create_all()
    
    # Add some default niches if none exist
    if NicheMarket.query.count() == 0:
        default_niches = [
            {
                'name': 'Sustainable Fashion',
                'description': 'Eco-friendly and ethically produced clothing and accessories',
                'key_characteristics': 'Eco-conscious, Ethical, Sustainable materials, Fair trade'
            },
            {
                'name': 'Vintage Boutique',
                'description': 'Curated selection of vintage clothing and accessories',
                'key_characteristics': 'Retro, Nostalgic, Unique, Classic'
            },
            {
                'name': 'Luxury Accessories',
                'description': 'High-end designer accessories for the discerning customer',
                'key_characteristics': 'Premium, Exclusive, Craftsmanship, Status'
            },
            {
                'name': 'Athleisure Wear',
                'description': 'Stylish athletic clothing designed for both workout and casual wear',
                'key_characteristics': 'Active, Comfortable, Versatile, Modern'
            }
        ]
        
        for niche_data in default_niches:
            niche = NicheMarket(**niche_data)
            db.session.add(niche)
        
        db.session.commit()

# --------------------------------------------------------------------------------
# Routes pour les outils OSP (Open Strategy Partners)
# --------------------------------------------------------------------------------
from osp_tools import generate_product_value_map, analyze_content_with_osp_guidelines, apply_seo_guidelines, render_value_map_html

@app.route('/osp-tools')
@login_required
def osp_tools():
    """Page principale des outils OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, NicheMarket, CustomerPersona, OSPAnalysis
    
    # Récupération des données pour les menus déroulants
    boutiques = Boutique.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    products = Product.query.all()
    niche_markets = NicheMarket.query.all()
    
    # Analyses OSP récentes
    recent_analyses = OSPAnalysis.query.order_by(OSPAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('osp_tools.html', 
                          boutiques=boutiques,
                          customers=customers,
                          personas=personas,
                          campaigns=campaigns,
                          products=products,
                          niche_markets=niche_markets,
                          recent_analyses=recent_analyses)

@app.route('/osp-tools/value-map-generator')
@app.route('/osp-tools/value-map-generator/<string:source_type>/<int:source_id>')
@login_required
def value_map_generator(source_type=None, source_id=None):
    """Générateur de carte de valeur produit"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona
    
    # Initialisation des données
    product_name = ""
    product_description = ""
    target_audience = ""
    industry = ""
    niche_market = ""
    key_features = ""
    competitors = ""
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            product_name = product.name
            product_description = product.base_description or ""
            if product.target_audience:
                customer = product.target_audience
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
            if product.boutique:
                niche_market = product.boutique.name
        
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            product_name = campaign.title
            product_description = campaign.content
            target_audience = campaign.target_audience or ""
            if campaign.customer:
                customer = campaign.customer
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
        
        elif source_type == 'persona' and source_id:
            persona = CustomerPersona.query.get_or_404(source_id)
            product_name = f"Produit pour {persona.title}"
            target_audience = persona.description
            if persona.niche_market:
                niche_market = persona.niche_market.name
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='value_map',
                         product_name=product_name,
                         product_description=product_description,
                         target_audience=target_audience,
                         industry=industry,
                         niche_market=niche_market,
                         key_features=key_features,
                         competitors=competitors,
                         boutiques=boutiques,
                         products=products,
                         customers=customers,
                         personas=personas,
                         campaigns=campaigns)

@app.route('/osp-tools/content-analyzer')
@app.route('/osp-tools/content-analyzer/<string:source_type>/<int:source_id>')
@login_required
def content_analyzer(source_type=None, source_id=None):
    """Analyseur de contenu selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona
    
    # Initialisation des données
    content = ""
    content_type = "product_description"
    target_audience = ""
    industry = ""
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            content = product.base_description or product.generated_description or ""
            if product.target_audience:
                customer = product.target_audience
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
            if product.boutique:
                industry = product.boutique.name
        
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            content = campaign.content
            content_type = campaign.campaign_type or "email"
            target_audience = campaign.target_audience or ""
            if campaign.customer:
                customer = campaign.customer
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
        
        elif source_type == 'persona' and source_id:
            persona = CustomerPersona.query.get_or_404(source_id)
            content = persona.description
            target_audience = persona.title
            if persona.niche_market:
                industry = persona.niche_market.name
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='content_analyzer',
                         content=content,
                         content_type=content_type,
                         target_audience=target_audience,
                         industry=industry,
                         boutiques=boutiques,
                         products=products,
                         customers=customers,
                         personas=personas,
                         campaigns=campaigns)

@app.route('/osp-tools/seo-optimizer')
@app.route('/osp-tools/seo-optimizer/<string:source_type>/<int:source_id>')
def seo_optimizer(source_type=None, source_id=None):
    """Optimiseur SEO selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Campaign, Product
    
    # Initialisation des données
    title = ""
    description = ""
    page_type = "product"
    locale = "fr_FR"
    is_local_business = True
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            title = product.name
            description = product.base_description or product.generated_description or ""
            # Si le produit a un méta titre/description, les utiliser
            if product.meta_title:
                title = product.meta_title
            if product.meta_description:
                description = product.meta_description
                
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            title = campaign.title
            description = campaign.content[:200] + "..." if len(campaign.content) > 200 else campaign.content
            if campaign.campaign_type == 'landing_page':
                page_type = 'landing'
            elif campaign.campaign_type == 'product_description':
                page_type = 'product'
            
            # Récupérer la langue de la campagne pour le locale
            if campaign.language:
                if campaign.language == 'fr':
                    locale = 'fr_FR'
                elif campaign.language == 'en':
                    locale = 'en_US'
        
        elif source_type == 'boutique' and source_id:
            boutique = Boutique.query.get_or_404(source_id)
            title = boutique.name
            description = boutique.description or ""
            page_type = 'about'
            
            # Récupérer la langue de la boutique pour le locale
            if boutique.language:
                if boutique.language == 'fr':
                    locale = 'fr_FR'
                elif boutique.language == 'en':
                    locale = 'en_US'
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='seo_optimizer',
                         title=title,
                         description=description,
                         page_type=page_type,
                         locale=locale,
                         is_local_business=is_local_business,
                         boutiques=boutiques,
                         products=products,
                         campaigns=campaigns)

@app.route('/osp-tools/generate-value-map', methods=['POST'])
def generate_value_map():
    """Générer une carte de valeur produit"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona, OSPAnalysis, OSPAnalysisType
    try:
        # Récupérer les données du formulaire
        product_name = request.form.get('product_name')
        product_description = request.form.get('product_description')
        target_audience = request.form.get('target_audience')
        industry = request.form.get('industry')
        niche_market = request.form.get('niche_market')
        
        # Récupérer les IDs des entités associées (s'ils sont fournis)
        product_id = request.form.get('product_id', type=int)
        campaign_id = request.form.get('campaign_id', type=int)
        persona_id = request.form.get('persona_id', type=int)
        customer_id = request.form.get('customer_id', type=int)
        boutique_id = request.form.get('boutique_id', type=int)
        
        # Option de sauvegarde
        should_save = request.form.get('save_result') == 'on'
        title = request.form.get('title', f"Carte de valeur - {product_name}")
        
        # Traiter les listes
        key_features = request.form.get('key_features', '').strip().split('\n') if request.form.get('key_features') else None
        competitors = request.form.get('competitors', '').strip().split('\n') if request.form.get('competitors') else None
        
        # S'assurer que les valeurs ne sont pas None
        product_name = product_name or ""
        product_description = product_description or ""
        target_audience = target_audience or ""
        industry = industry or ""
        niche_market = niche_market or ""
        
        # Générer la carte de valeur
        value_map = generate_product_value_map(
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            industry=industry,
            niche_market=niche_market,
            key_features=key_features,
            competitors=competitors
        )
        
        # Générer le HTML pour l'affichage
        value_map_html = render_value_map_html(value_map)
        
        # Sauvegarder l'analyse si demandé
        if should_save:
            # Créer un nouvel objet OSPAnalysis
            analysis = OSPAnalysis(
                analysis_type=OSPAnalysisType.VALUE_MAP,
                title=title,
                content=value_map,  # Stockage des données JSON
                html_result=value_map_html,  # Stockage du HTML généré
                product_id=product_id,
                campaign_id=campaign_id,
                persona_id=persona_id,
                customer_id=customer_id,
                boutique_id=boutique_id
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            flash(_("Carte de valeur générée et sauvegardée avec succès."), 'success')
        
        # Log de la métrique
        log_metric(
            metric_name="osp_value_map_generation",
            data={"product_name": product_name, "industry": industry, "saved": should_save},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            value_map=value_map,
            value_map_html=value_map_html,
            value_map_json=json.dumps(value_map, indent=2, ensure_ascii=False),
            should_save=should_save,
            title=title
        )
    except Exception as e:
        flash(_("Erreur lors de la génération de la carte de valeur: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_value_map_generation",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))

@app.route('/osp-tools/analyze-content', methods=['POST'])
def analyze_content():
    """Analyser du contenu selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona, OSPAnalysis, OSPAnalysisType
    try:
        # Récupérer les données du formulaire
        content = request.form.get('content')
        content_type = request.form.get('content_type')
        target_audience = request.form.get('target_audience')
        industry = request.form.get('industry')
        
        # Récupérer les IDs des entités associées (s'ils sont fournis)
        product_id = request.form.get('product_id', type=int)
        campaign_id = request.form.get('campaign_id', type=int)
        persona_id = request.form.get('persona_id', type=int)
        customer_id = request.form.get('customer_id', type=int)
        boutique_id = request.form.get('boutique_id', type=int)
        
        # Option de sauvegarde
        should_save = request.form.get('save_result') == 'on'
        title = request.form.get('title', f"Analyse de contenu - {content_type}")
        
        # S'assurer que les valeurs ne sont pas None
        content = content or ""
        content_type = content_type or "product_description"
        target_audience = target_audience or ""
        industry = industry or ""
        
        # Analyser le contenu
        content_analysis = analyze_content_with_osp_guidelines(
            content=content,
            content_type=content_type,
            target_audience=target_audience,
            industry=industry
        )
        
        # Sauvegarder l'analyse si demandé
        if should_save:
            # Créer un nouvel objet OSPAnalysis
            analysis = OSPAnalysis(
                analysis_type=OSPAnalysisType.CONTENT_ANALYSIS,
                title=title,
                content={
                    'input': {
                        'content': content,
                        'content_type': content_type,
                        'target_audience': target_audience,
                        'industry': industry
                    },
                    'results': content_analysis
                },
                html_result=json.dumps(content_analysis, indent=2, ensure_ascii=False),
                product_id=product_id,
                campaign_id=campaign_id,
                persona_id=persona_id,
                customer_id=customer_id,
                boutique_id=boutique_id
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            flash(_("Analyse de contenu générée et sauvegardée avec succès."), 'success')
        
        # Log de la métrique
        log_metric(
            metric_name="osp_content_analysis",
            data={"content_type": content_type, "length": len(content), "saved": should_save},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            form_active='content_analyzer',
            content_analysis=content_analysis,
            content_analysis_json=json.dumps(content_analysis, indent=2, ensure_ascii=False),
            content=content,
            content_type=content_type,
            target_audience=target_audience,
            industry=industry,
            should_save=should_save,
            title=title
        )
    except Exception as e:
        flash(_("Erreur lors de l'analyse du contenu: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_content_analysis",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))

@app.route('/osp-tools/optimize-seo', methods=['POST'])
def optimize_seo():
    """Optimiser du contenu pour le SEO selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Campaign, Product, OSPAnalysis, OSPAnalysisType
    try:
        # Récupérer les données du formulaire
        title = request.form.get('title')
        description = request.form.get('description')
        page_type = request.form.get('page_type')
        locale = request.form.get('locale')
        is_local_business = True if request.form.get('is_local_business') else False
        
        # Récupérer les IDs des entités associées (s'ils sont fournis)
        product_id = request.form.get('product_id', type=int)
        campaign_id = request.form.get('campaign_id', type=int)
        persona_id = request.form.get('persona_id', type=int)
        customer_id = request.form.get('customer_id', type=int)
        boutique_id = request.form.get('boutique_id', type=int)
        
        # Option de sauvegarde
        should_save = request.form.get('save_result') == 'on'
        analysis_title = request.form.get('analysis_title', f"Optimisation SEO - {title}")
        
        # S'assurer que les valeurs ne sont pas None
        title = title or ""
        description = description or ""
        page_type = page_type or "product"
        locale = locale or "fr_FR"
        
        # Optimiser le contenu
        content = {
            "title": title,
            "description": description
        }
        
        seo_optimized = apply_seo_guidelines(
            content=content,
            page_type=page_type,
            locale=locale,
            is_local_business=is_local_business
        )
        
        # Sauvegarder l'analyse si demandé
        if should_save:
            # Créer un nouvel objet OSPAnalysis
            analysis = OSPAnalysis(
                analysis_type=OSPAnalysisType.SEO_OPTIMIZATION,
                title=analysis_title,
                content={
                    'input': {
                        'title': title,
                        'description': description,
                        'page_type': page_type,
                        'locale': locale,
                        'is_local_business': is_local_business
                    },
                    'results': seo_optimized
                },
                html_result=json.dumps(seo_optimized, indent=2, ensure_ascii=False),
                product_id=product_id,
                campaign_id=campaign_id,
                persona_id=persona_id,
                customer_id=customer_id,
                boutique_id=boutique_id
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            flash(_("Optimisation SEO générée et sauvegardée avec succès."), 'success')
        
        # Log de la métrique
        log_metric(
            metric_name="osp_seo_optimization",
            data={"page_type": page_type, "locale": locale, "saved": should_save},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            form_active='seo_optimizer',
            seo_optimized=seo_optimized,
            seo_optimized_json=json.dumps(seo_optimized, indent=2, ensure_ascii=False),
            title=title,
            description=description,
            page_type=page_type,
            locale=locale,
            is_local_business=is_local_business,
            should_save=should_save,
            analysis_title=analysis_title
        )
    except Exception as e:
        flash(_("Erreur lors de l'optimisation SEO: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_seo_optimization",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))
        
@app.route('/osp-analysis/<int:analysis_id>')
def view_osp_analysis(analysis_id):
    """Afficher le détail d'une analyse OSP"""
    from models import OSPAnalysis
    
    analysis = OSPAnalysis.query.get_or_404(analysis_id)
    
    # Détermination du titre en fonction du type d'analyse
    type_titles = {
        'value_map': "Carte de Valeur",
        'content_analysis': "Analyse de Contenu",
        'seo_optimization': "Optimisation SEO"
    }
    
    analysis_type_title = type_titles.get(analysis.analysis_type.value, "Analyse OSP")
    
    return render_template('osp_analysis_detail.html',
                          analysis=analysis,
                          analysis_type_title=analysis_type_title)

@app.route('/osp-analysis/<int:analysis_id>/edit', methods=['GET', 'POST'])
def edit_osp_analysis(analysis_id):
    """Éditer une analyse OSP existante"""
    from models import OSPAnalysis
    
    analysis = OSPAnalysis.query.get_or_404(analysis_id)
    
    if request.method == 'POST':
        # Mise à jour des données de l'analyse
        analysis.title = request.form.get('title', analysis.title)
        
        # Si d'autres champs doivent être modifiables, les ajouter ici
        
        db.session.commit()
        flash(_("L'analyse a été mise à jour avec succès!"), "success")
        return redirect(url_for('view_osp_analysis', analysis_id=analysis.id))
    
    return render_template('osp_analysis_edit.html', analysis=analysis)

@app.route('/osp-analysis/<int:analysis_id>/delete', methods=['POST'])
def delete_osp_analysis(analysis_id):
    """Supprimer une analyse OSP"""
    from models import OSPAnalysis
    
    analysis = OSPAnalysis.query.get_or_404(analysis_id)
    
    # Suppression de l'analyse
    db.session.delete(analysis)
    db.session.commit()
    
    flash(_("L'analyse a été supprimée avec succès."), "success")
    return redirect(url_for('osp_tools'))

@app.route('/campaign/<int:campaign_id>/send', methods=['POST'])
@login_required
def send_campaign(campaign_id):
    """Envoie une campagne marketing"""
    from models import Campaign, UserActivity
    
    try:
        campaign = Campaign.query.filter_by(id=campaign_id, owner_id=current_user.id).first_or_404()
        
        # Log l'activité d'envoi
        activity = UserActivity.log_activity(
            user_id=current_user.id,
            activity_type='campaign_send',
            description=f'Envoi de la campagne: {campaign.title}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Marquer la campagne comme envoyée
        campaign.sent_at = datetime.datetime.utcnow()
        campaign.status = 'sent'
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Campagne envoyée avec succès'
        })
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la campagne: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint principal de vérification de santé"""
    import psutil
    from sqlalchemy import text
    
    # Vérification base de données
    try:
        import time as time_module
        start_time = time_module.time()
        result = db.session.execute(text("SELECT 1")).fetchone()
        db_response_time = (time_module.time() - start_time) * 1000
        db_status = {
            "status": "healthy" if result else "unhealthy",
            "response_time_ms": round(db_response_time, 2),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        db_status = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    
    # Vérification système
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_status = {
            "status": "healthy",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": round((disk.used / disk.total) * 100, 2),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        system_status = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    
    # Vérification services IA
    ai_status = {
        "status": "configured" if (os.environ.get("OPENAI_API_KEY") or os.environ.get("XAI_API_KEY")) else "not_configured",
        "openai": "configured" if os.environ.get("OPENAI_API_KEY") else "not_configured",
        "xai": "configured" if os.environ.get("XAI_API_KEY") else "not_configured",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    
    # Statut global
    overall_status = "healthy"
    if db_status["status"] != "healthy":
        overall_status = "unhealthy"
    elif system_status["status"] != "healthy":
        overall_status = "degraded"
    
    response = {
        "status": overall_status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "application": {
            "name": "NinjaLead.ai",
            "version": os.environ.get("APP_VERSION", "1.0.0"),
            "environment": os.environ.get("ENVIRONMENT", "production")
        },
        "services": {
            "database": db_status,
            "ai_services": ai_status
        },
        "system": system_status
    }
    
    status_code = 200 if overall_status == "healthy" else 503
    return jsonify(response), status_code

@app.route('/health/live', methods=['GET'])
def liveness_check():
    """Endpoint simple pour vérifier si l'application est vivante"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200

@app.route('/health/ready', methods=['GET'])
def readiness_check():
    """Endpoint pour vérifier si l'application est prête"""
    try:
        from sqlalchemy import text
        result = db.session.execute(text("SELECT 1")).fetchone()
        if result:
            return jsonify({
                "status": "ready",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "not_ready",
                "reason": "Database not available",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }), 503
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "reason": f"Database error: {str(e)}",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 503

@app.route('/test-sentry', methods=['GET'])
def test_sentry():
    """Endpoint pour tester le monitoring Sentry selon la documentation officielle"""
    1/0  # raises an error
    return "<p>Hello, World!</p>"

logger.info("Health check routes registered successfully")

# Initialize security enhancements
try:
    talisman, limiter = init_security_extensions(app)
    add_security_headers(app)
    setup_error_handlers(app)
    logger.info("Security enhancements initialized successfully")
except Exception as e:
    logger.error(f"Error initializing security enhancements: {e}")

# Initialize backup system
try:
    from backup_manager import init_backup_system, backup_manager
    init_backup_system()
    
    @app.route('/admin/backups', methods=['GET'])
    @login_required
    def backup_status():
        """Page d'administration des sauvegardes"""
        if current_user.role != 'admin':
            flash('Accès non autorisé', 'error')
            return redirect(url_for('dashboard'))
        
        status = backup_manager.get_backup_status()
        backups = backup_manager.list_backups()
        
        return render_template('admin/backup_status.html', 
                             status=status, 
                             backups=backups)
    
    @app.route('/admin/backups/create', methods=['POST'])
    @login_required
    def manual_backup():
        """Crée une sauvegarde manuelle"""
        if current_user.role != 'admin':
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        success = backup_manager.create_backup()
        if success:
            return jsonify({'success': True, 'message': 'Sauvegarde créée avec succès'})
        else:
            return jsonify({'success': False, 'message': 'Échec de la sauvegarde'}), 500
    
    logger.info("Backup system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize backup system: {str(e)}")

# Initialize feedback system
if feedback_system_loaded:
    try:
        feedback_manager.init_app(app)
        logger.info("User feedback system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize feedback system: {str(e)}")

# Routes pour le tableau de bord des performances
@app.route('/admin/performance')
@login_required
def performance_dashboard():
    """Tableau de bord des performances et optimisations"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    performance_data = {}
    
    # Statistiques de sécurité avancée
    security_status = {
        'encryption': get_encryption_status() if encryption_available else {'status': 'not_configured'},
        'ddos_protection': get_ddos_stats() if ddos_protection_available else {'status': 'not_configured'},
        'cache': cache_manager.get_stats() if cache_available else {'status': 'not_configured'},
        'security_middleware': True,
        'gdpr_compliance': True,
        'audit_trail': True
    }
    
    performance_data['security_status'] = security_status
    
    # Statistiques du cache
    if performance_modules_loaded:
        try:
            performance_data['cache_stats'] = performance_cache.get_cache_stats() if performance_cache else {"status": "not_available"}
        except Exception:
            performance_data['cache_stats'] = {"status": "error"}
        
        # Statistiques de base de données
        try:
            performance_data['db_stats'] = db_index_optimizer.get_index_statistics() if db_index_optimizer else {"status": "not_available"}
        except Exception:
            performance_data['db_stats'] = {"status": "error"}
        
        # Statistiques d'optimisation des assets
        try:
            performance_data['asset_stats'] = asset_optimizer.get_optimization_stats() if asset_optimizer else {"status": "not_available"}
        except Exception:
            performance_data['asset_stats'] = {"message": "Assets optimization not run yet"}
    else:
        performance_data = {
            'cache_stats': {"status": "Performance modules not loaded"},
            'db_stats': {},
            'asset_stats': {"message": "Performance modules not available"}
        }
    
    return render_template('admin/performance_dashboard.html', 
                         performance_data=performance_data)

@app.route('/admin/performance/optimize', methods=['POST'])
@login_required
def run_performance_optimization():
    """Exécute les optimisations de performance"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Non autorisé'}), 403
    
    results = {}
    
    if performance_modules_loaded:
        try:
            # Optimisation des assets
            if asset_optimizer:
                asset_results = asset_optimizer.optimize_all_assets()
                results['assets'] = f"Assets optimisés: {asset_results.get('files_processed', 0)} fichiers"
            
            # Optimisation de la base de données
            if db_index_optimizer:
                db_index_optimizer.create_performance_indexes()
                db_index_optimizer.optimize_table_statistics()
                results['database'] = "Index de performance créés et statistiques mises à jour"
            
            # Nettoyage du cache
            if performance_cache:
                performance_cache.clear_all_cache()
                results['cache'] = "Cache nettoyé avec succès"
                
        except Exception as e:
            results['error'] = f"Erreur d'optimisation: {str(e)}"
    else:
        results['error'] = "Modules de performance non disponibles"
    
    return jsonify(results)

# Routes API pour le système de feedback utilisateur
@app.route('/api/contextual-help', methods=['POST'])
def get_contextual_help():
    """Retourne l'aide contextuelle pour une page"""
    if feedback_system_loaded:
        data = request.get_json()
        page_route = data.get('page_route', '/')
        user_role = current_user.role if current_user.is_authenticated else None
        
        help_data = feedback_manager.get_contextual_help(page_route, user_role)
        return jsonify(help_data)
    else:
        return jsonify({
            'title': 'Aide',
            'description': 'Système d\'aide non disponible',
            'tips': ['Contactez l\'administrateur pour assistance']
        })

@app.route('/api/submit-feedback', methods=['POST'])
def submit_user_feedback():
    """Collecte et traite un feedback utilisateur"""
    if not feedback_system_loaded:
        return jsonify({'success': False, 'error': 'Système de feedback non disponible'}), 503
    
    try:
        data = request.get_json()
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        
        feedback_type = data.get('type')
        priority = data.get('priority', 'medium')
        message = data.get('message')
        context = data.get('context', {})
        
        if not feedback_type or not message:
            return jsonify({'success': False, 'error': 'Type et message requis'}), 400
        
        # Collecte le feedback via le gestionnaire
        result = feedback_manager.collect_feedback(
            user_id=user_id,
            feedback_type=feedback_type,
            message=message,
            context=context,
            priority=priority
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return jsonify({'success': False, 'error': 'Erreur interne du serveur'}), 500

# API endpoint pour le système de feedback ninja
@app.route('/api/feedback', methods=['POST'])
def handle_ninja_feedback():
    """Traite les soumissions du formulaire de feedback ninja personnalisé"""
    try:
        data = request.get_json()
        
        # Validation des données requises
        required_fields = ['type', 'name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False, 
                    'error': f'Le champ {field} est requis'
                }), 400
        
        # Validation de l'email
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, data['email']):
            return jsonify({
                'success': False, 
                'error': 'Format d\'email invalide'
            }), 400
        
        # Structurer les données pour Sentry
        sentry_data = {
            'level': 'info' if data['type'] == 'suggestion' else 'error',
            'message': f"[{data['type'].upper()}] {data['message'][:100]}...",
            'tags': {
                'feedback_type': data['type'],
                'source': 'ninja_feedback_form'
            },
            'user': {
                'email': data['email'],
                'username': data['name']
            },
            'extra': {
                'feedback_type': data['type'],
                'full_message': data['message'],
                'system_info': data.get('systemInfo', {}),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        }
        
        # Envoyer vers Sentry si configuré
        try:
            import sentry_sdk
            sentry_sdk.capture_message(
                sentry_data['message'],
                level=sentry_data['level'],
                tags=sentry_data['tags'],
                user=sentry_data['user'],
                extra=sentry_data['extra']
            )
            logger.info(f"Feedback envoyé vers Sentry: {data['type']} de {data['name']}")
        except Exception as sentry_error:
            logger.warning(f"Erreur lors de l'envoi vers Sentry: {sentry_error}")
        
        # Enregistrer localement dans les logs
        feedback_log = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'type': data['type'],
            'name': data['name'],
            'email': data['email'],
            'message': data['message'],
            'system_info': data.get('systemInfo', {}),
            'user_id': current_user.id if current_user.is_authenticated else None
        }
        
        logger.info(f"Feedback reçu: {json.dumps(feedback_log, ensure_ascii=False)}")
        
        # Réponse de succès
        return jsonify({
            'success': True,
            'message': 'Votre feedback a été envoyé avec succès. Notre équipe ninja l\'examine.',
            'feedback_id': str(uuid.uuid4())
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du feedback: {e}")
        return jsonify({
            'success': False,
            'error': 'Une erreur interne est survenue. Veuillez réessayer.'
        }), 500

# Route de test Sentry pour vérifier l'installation
@app.route("/sentry-debug")
def trigger_error():
    """Route de test pour vérifier que Sentry capture les erreurs"""
    division_by_zero = 1 / 0  # Déclenche intentionnellement une erreur
    return "Cette ligne ne devrait jamais être atteinte"
