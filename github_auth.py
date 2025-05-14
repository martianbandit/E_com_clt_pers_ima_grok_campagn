import os
import uuid
import datetime
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for, flash
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.consumer.storage import BaseStorage
from flask_login import login_user, logout_user, current_user
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

# Variable globale db accessible depuis les fonctions
db = None

def init_github_auth(app, sqlalchemy_db):
    """
    Initialise l'authentification GitHub avec l'application Flask
    
    Args:
        app: Application Flask
        sqlalchemy_db: Instance SQLAlchemy
    """
    global db
    
    # Stockage de l'instance de db
    db = sqlalchemy_db
    
    # Enregistrement du blueprint GitHub
    github_bp = make_github_blueprint()
    app.register_blueprint(github_bp, url_prefix="/github")
    
    return github_bp


class GithubUserSessionStorage(BaseStorage):
    """Storage for GitHub authentication tokens in database"""

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


def make_github_blueprint():
    """
    Crée un blueprint OAuth2 pour l'authentification GitHub
    
    Returns:
        OAuth2ConsumerBlueprint: Blueprint pour l'authentification GitHub
    """
    # Récupération des variables d'environnement
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
    
    # Création du blueprint
    github_bp = OAuth2ConsumerBlueprint(
        "github",
        __name__,
        client_id=client_id,
        client_secret=client_secret,
        base_url="https://api.github.com/",
        authorization_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scope=["user:email"],  # Accès à l'email de l'utilisateur
        storage=GithubUserSessionStorage(),
    )
    
    @github_bp.before_app_request
    def set_applocal_session():
        """
        Configure la session locale pour le blueprint
        """
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_github = github_bp.session
    
    @github_bp.route("/login")
    def login():
        """
        Route de connexion GitHub
        """
        # Si l'utilisateur n'est pas connecté à GitHub
        if not github.authorized:
            # Sauvegarde de l'URL de redirection après connexion
            session["next_url"] = request.args.get("next") or url_for("index")
            # Redirection vers l'autorisation GitHub
            return redirect(url_for("github.login"))
        
        # Si l'utilisateur est déjà connecté à GitHub, récupération des informations
        resp = github.get("/user")
        if resp.ok:
            # Récupération des informations utilisateur
            user_info = resp.json()
            # Sauvegarde des informations utilisateur
            user = save_github_user(user_info)
            # Connexion de l'utilisateur avec Flask-Login
            login_user(user)
            # Redirection vers la page demandée initialement
            next_url = session.pop("next_url", None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for("index"))
        
        # Si une erreur s'est produite
        flash("Une erreur s'est produite lors de la connexion avec GitHub.", "danger")
        return redirect(url_for("login"))
    
    @github_bp.route("/logout")
    def logout():
        """
        Route de déconnexion GitHub
        """
        # Suppression du token et déconnexion de l'utilisateur
        logout_user()
        # Redirection vers la page d'accueil
        return redirect(url_for("index"))
    
    return github_bp


def get_github_user_email(github_client):
    """
    Récupère l'email de l'utilisateur GitHub
    
    Args:
        github_client: Client GitHub
        
    Returns:
        str: Email de l'utilisateur ou None si non trouvé
    """
    # Récupération des emails de l'utilisateur
    resp = github_client.get("/user/emails")
    if resp.ok:
        emails = resp.json()
        # Récupération de l'email principal et vérifié
        for email_data in emails:
            if email_data.get("primary") and email_data.get("verified"):
                return email_data.get("email")
        # Si aucun email principal et vérifié, prendre le premier vérifié
        for email_data in emails:
            if email_data.get("verified"):
                return email_data.get("email")
    return None


def save_github_user(user_info):
    """
    Sauvegarde les informations de l'utilisateur GitHub en base de données
    
    Args:
        user_info: Informations de l'utilisateur GitHub
        
    Returns:
        User: Utilisateur créé ou mis à jour
    """
    from models import User, UserActivity
    
    # Récupération des informations utilisateur
    github_id = str(user_info.get("id"))
    login = user_info.get("login")
    name = user_info.get("name")
    email = user_info.get("email")
    avatar_url = user_info.get("avatar_url")
    
    # Si l'email n'est pas disponible, essayer de le récupérer
    if not email:
        email = get_github_user_email(github)
    
    # Séparation du nom en prénom et nom de famille
    first_name = name
    last_name = None
    if name and " " in name:
        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1]
    
    # Recherche de l'utilisateur existant par GitHub ID
    user = User.query.filter_by(github_id=github_id).first()
    
    # Si l'utilisateur n'existe pas, le créer
    if not user:
        user = User()
        user.id = str(uuid.uuid4())
        user.github_id = github_id
    
    # Mise à jour des informations utilisateur
    user.username = login
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.profile_image_url = avatar_url
    
    # Sauvegarde de l'utilisateur
    db.session.add(user)
    
    # Enregistrement de l'activité de connexion
    try:
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr or '0.0.0.0'
        
        activity = UserActivity()
        activity.user_id = user.id
        activity.activity_type = 'login'
        activity.description = f'Connexion GitHub depuis {ip_address}'
        activity.ip_address = ip_address
        activity.user_agent = user_agent
        activity.created_at = datetime.datetime.utcnow()
        db.session.add(activity)
    except Exception as e:
        # En cas d'erreur, ne pas bloquer la connexion
        print(f"Erreur lors de l'enregistrement de l'activité: {e}")
    
    # Sauvegarde des modifications
    db.session.commit()
    
    return user


# Connexion réussie GitHub
@oauth_authorized.connect_via("github")
def github_logged_in(blueprint, token):
    """
    Fonction appelée lorsque l'authentification GitHub est réussie
    
    Args:
        blueprint: Blueprint OAuth2
        token: Token d'authentification
    """
    if not token:
        flash("Échec de la connexion avec GitHub.", "danger")
        return False
    
    # Récupération des informations utilisateur
    resp = blueprint.session.get("/user")
    if not resp.ok:
        flash("Échec de la récupération des informations utilisateur GitHub.", "danger")
        return False
    
    # Récupération des informations utilisateur
    user_info = resp.json()
    
    # Sauvegarde des informations utilisateur
    user = save_github_user(user_info)
    
    # Connexion de l'utilisateur avec Flask-Login
    login_user(user)
    
    # Stockage du token pour les futures requêtes
    blueprint.token = token
    
    # Redirection vers la page demandée initialement
    next_url = session.pop("next_url", None)
    if next_url:
        return redirect(next_url)


# Erreur GitHub
@oauth_error.connect_via("github")
def github_error(blueprint, error, error_description=None, error_uri=None):
    """
    Fonction appelée lorsqu'une erreur se produit lors de l'authentification GitHub
    """
    msg = f"OAuth error from GitHub: {error}"
    if error_description:
        msg = f"{msg} - {error_description}"
    flash(msg, "danger")
    return redirect(url_for("login"))


# Proxy pour accéder à la session GitHub
github = LocalProxy(lambda: g.flask_dance_github)