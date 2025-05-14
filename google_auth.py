import json
import os

import requests
from flask import Blueprint, redirect, request, url_for, flash, current_app
from flask_login import login_required, login_user, logout_user, current_user
from models import User
from app import db
from oauthlib.oauth2 import WebApplicationClient

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL. It has to match the one in the whitelist
DEV_REDIRECT_URL = f'https://{os.environ.get("REPLIT_DOMAIN", "localhost")}/google_login/callback'

# ALWAYS display setup instructions to the user:
print(f"""Pour finaliser l'authentification Google:
1. Allez sur https://console.cloud.google.com/apis/credentials
2. Créez un nouvel ID client OAuth 2.0
3. Ajoutez {DEV_REDIRECT_URL} aux URI de redirection autorisés

Pour des instructions détaillées, voir:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)


@google_auth.route("/google_login")
def login():
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        # Replacing http:// with https:// is important as the external
        # protocol must be https to match the URI whitelisted
        authorization_response=request.url.replace("http://", "https://"),
        redirect_url=request.base_url.replace("http://", "https://"),
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    userinfo = userinfo_response.json()
    if userinfo.get("email_verified"):
        users_email = userinfo["email"]
        users_name = userinfo.get("given_name", "")
        users_family_name = userinfo.get("family_name", "")
        picture = userinfo.get("picture", "")
    else:
        flash("L'email de l'utilisateur n'est pas vérifié par Google.", "danger")
        return redirect(url_for("index"))

    user = User.query.filter_by(email=users_email).first()
    if not user:
        # Création d'un nouvel utilisateur
        user = User()
        user.email = users_email
        user.first_name = users_name
        user.last_name = users_family_name
        user.profile_image_url = picture
        user.username = users_email.split("@")[0]
        user.role = "user"
        db.session.add(user)
        db.session.commit()
        flash(f"Bienvenue, {users_name}! Votre compte a été créé avec succès.", "success")
    else:
        # Mise à jour des informations de l'utilisateur existant
        user.first_name = users_name
        user.last_name = users_family_name
        if picture and not user.profile_image_url:
            user.profile_image_url = picture
        db.session.commit()
        flash(f"Bienvenue, {users_name}! Vous êtes connecté avec succès.", "success")

    login_user(user)
    
    # Enregistrement de l'activité de connexion
    try:
        from models import UserActivity
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr or '0.0.0.0'
        
        # Si UserActivity a une méthode log_activity, l'utiliser
        if hasattr(UserActivity, 'log_activity'):
            UserActivity.log_activity(
                user_id=user.id,
                activity_type='login',
                description=f'Connexion Google depuis {ip_address}',
                ip_address=ip_address,
                user_agent=user_agent
            )
        else:
            # Sinon, créer manuellement une entrée d'activité
            activity = UserActivity()
            activity.user_id = user.id
            activity.activity_type = 'login'
            activity.description = f'Connexion Google depuis {ip_address}'
            activity.ip_address = ip_address
            activity.user_agent = user_agent
            db.session.add(activity)
            
        if hasattr(user, 'login_count'):
            user.login_count = (user.login_count or 0) + 1
        if hasattr(user, 'last_login_at'):
            from datetime import datetime
            user.last_login_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'activité de connexion : {e}")
        # Ne pas bloquer la connexion en cas d'erreur de journalisation

    return redirect(url_for("index"))