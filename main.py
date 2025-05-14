from app import app, db
from flask_login import LoginManager
from replit_auth import make_replit_blueprint, init_auth

# Initialisation de l'authentification Replit
login_manager = init_auth(app, db)

# Enregistrement du blueprint d'authentification Replit
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
