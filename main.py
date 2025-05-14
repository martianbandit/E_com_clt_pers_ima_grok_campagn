from app import app
from replit_auth import make_replit_blueprint

# Enregistrement du blueprint d'authentification Replit
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
