"""
Script de migration pour ajouter la colonne usage_count à la table Customer
"""
import os
import logging
import psycopg2
from sqlalchemy import create_engine, Column, Integer, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Définir la classe de base pour les modèles
class Base(DeclarativeBase):
    pass

def run_migration():
    """Execute the database migration"""
    try:
        # Récupérer l'URL de la base de données depuis les variables d'environnement
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        # Créer un moteur de base de données
        engine = create_engine(db_url)
        
        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Vérifier si la colonne existe déjà
        with engine.connect() as conn:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='customer' AND column_name='usage_count'"))
            exists = result.fetchone() is not None
            
            if exists:
                logger.info("Column 'usage_count' already exists in table 'customer'")
                return True
        
        # Ajouter la colonne usage_count
        logger.info("Adding 'usage_count' column to 'customer' table")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE customer ADD COLUMN usage_count INTEGER DEFAULT 0"))
            conn.commit()
            
        logger.info("Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    # Execute migration
    success = run_migration()
    
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed")