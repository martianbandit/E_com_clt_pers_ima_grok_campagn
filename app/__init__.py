import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialisation des extensions
babel = Babel()
db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    if test_config:
        app.config.update(test_config)

    # Configuration DB
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }
        else:
            # Si pas de DATABASE_URL, lever une erreur SEULEMENT en dehors du mode test
            if not app.config.get("TESTING"):
                raise RuntimeError("DATABASE_URL environment variable is not set. PostgreSQL database is required.")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    babel.init_app(app)

    # Importer et enregistrer les blueprints ici
    from app.routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix="/products")
    # TODO: Register other blueprints (campaigns, personas, etc.)

    return app
