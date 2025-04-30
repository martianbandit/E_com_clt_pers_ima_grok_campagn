"""
Script de migration pour ajouter les nouvelles colonnes à la table Customer
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import sys
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

# Créer l'app Flask et initialiser la base de données
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Exécute la migration
def run_migration():
    with app.app_context():
        from sqlalchemy import text
        
        # Utiliser text() pour les requêtes SQL brutes
        sql = text('''
        ALTER TABLE customer 
        ADD COLUMN IF NOT EXISTS avatar_url TEXT,
        ADD COLUMN IF NOT EXISTS purchased_products JSONB,
        ADD COLUMN IF NOT EXISTS niche_attributes JSONB;
        ''')
        
        db.session.execute(sql)
        db.session.commit()
        print("Migration terminée avec succès!")

if __name__ == "__main__":
    run_migration()