"""
Script de migration pour ajouter la colonne avatar_prompt à la table Customer
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configure the PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    raise RuntimeError("DATABASE_URL environment variable is not set")
    
# Check if DATABASE_URL starts with postgres://, and if so, replace with postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

def run_migration():
    """Execute the database migration"""
    with app.app_context():
        try:
            # Vérifier si la colonne existe déjà
            check_query = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'customer' AND column_name = 'avatar_prompt'
            """)
            result = db.session.execute(check_query).fetchone()
            
            if not result:
                # La colonne n'existe pas, on la crée
                logger.info("Ajout de la colonne 'avatar_prompt' à la table 'customer'")
                alter_query = text("""
                    ALTER TABLE customer 
                    ADD COLUMN avatar_prompt TEXT
                """)
                db.session.execute(alter_query)
                db.session.commit()
                logger.info("Migration terminée avec succès")
            else:
                logger.info("La colonne 'avatar_prompt' existe déjà")
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    if run_migration():
        print("Migration completed successfully")
    else:
        print("Migration failed")