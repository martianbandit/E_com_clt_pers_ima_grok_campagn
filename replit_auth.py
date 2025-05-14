import jwt
import os
import uuid
import datetime
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for, current_app
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

def init_auth(app, sqlalchemy_db):
    """
    Initialise l'authentification avec l'application Flask
    
    Args:
        app: Application Flask
        sqlalchemy_db: Instance SQLAlchemy
    """
    global login_manager, db
    
    # Stockage de l'instance de db
    db = sqlalchemy_db
    
    # Import des modèles nécessaires
    from models import User, OAuth
    
    # Configuration de Flask-Login
    login_manager = LoginManager(app)
    # On définit la vue de login avec une chaîne de caractères
    login_manager.login_view = "replit_auth.login"
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
        
    # Le blueprint est enregistré dans main.py
    # app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")
    
    return login_manager


class UserSessionStorage(BaseStorage):

    def get(self, blueprint):
        from models import OAuth
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        from models import OAuth
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        from models import OAuth
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name).delete()
        db.session.commit()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        return render_template("auth/error.html"), 403

    return replit_bp


def save_user(user_claims):
    from app import db
    from models import User
    
    # Création ou mise à jour de l'utilisateur
    user = User()
    user.id = user_claims['sub']
    user.email = user_claims.get('email')
    user.first_name = user_claims.get('first_name')
    user.last_name = user_claims.get('last_name')
    user.profile_image_url = user_claims.get('profile_image_url')
    
    # Si l'utilisateur a un nom d'utilisateur dans les claims, l'utiliser
    username = user_claims.get('username')
    if username:
        user.username = username
        
    # Fusion avec les données existantes
    merged_user = db.session.merge(user)
    db.session.commit()
    return merged_user


@oauth_authorized.connect
def logged_in(blueprint, token):
    from app import db
    from models import UserActivity
    
    # Décodage du token et récupération des informations utilisateur
    user_claims = jwt.decode(token['id_token'], 
                          options={"verify_signature": False})
    
    # Sauvegarde de l'utilisateur en base de données
    user = save_user(user_claims)
    
    # Connexion de l'utilisateur avec Flask-Login
    login_user(user)
    
    # Enregistrement de l'activité de connexion
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr or '0.0.0.0'
    
    # Enregistrer l'activité de connexion
    try:
        # Si la classe UserActivity a une méthode log_activity, l'utiliser
        if hasattr(UserActivity, 'log_activity'):
            UserActivity.log_activity(
                user_id=user.id,
                activity_type='login',
                description=f'Connexion Replit depuis {ip_address}',
                ip_address=ip_address,
                user_agent=user_agent
            )
        # Sinon, essayer de créer une activité manuellement
        else:
            activity = UserActivity()
            activity.user_id = user.id
            activity.activity_type = 'login'
            activity.description = f'Connexion Replit depuis {ip_address}'
            activity.ip_address = ip_address
            activity.user_agent = user_agent
            activity.created_at = datetime.datetime.utcnow()
            db.session.add(activity)
    except Exception as e:
        # En cas d'erreur, ne pas bloquer la connexion
        print(f"Erreur lors de l'enregistrement de l'activité: {e}")
    
    # Sauvegarde des modifications
    db.session.commit()
    
    # Stockage du token pour les futures requêtes
    blueprint.token = token
    
    # Redirection vers la page demandée initialement
    next_url = session.pop("next_url", None)
    if next_url is not None:
        return redirect(next_url)


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    return redirect(url_for('replit_auth.error'))


def require_login(f):
    """
    Décorateur pour protéger les routes qui nécessitent une connexion.
    Redirige vers la page de connexion si l'utilisateur n'est pas connecté.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))

        # Vérifier si le token a expiré
        expires_in = replit.token.get('expires_in', 0)
        if expires_in < 0:
            # URL du service de token de Replit pour rafraîchir le token
            issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
            refresh_token_url = issuer_url + "/token"
            
            try:
                token = replit.refresh_token(token_url=refresh_token_url,
                                             client_id=os.environ['REPL_ID'])
            except InvalidGrantError:
                # Si le refresh token est invalide, l'utilisateur doit se reconnecter
                session["next_url"] = get_next_navigation_url(request)
                return redirect(url_for('replit_auth.login'))
            
            replit.token_updater(token)

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    """
    Détermine l'URL de redirection après connexion en analysant les en-têtes de la requête.
    """
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)