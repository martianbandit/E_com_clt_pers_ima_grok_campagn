"""
Script pour vérifier que toutes les tables et colonnes nécessaires existent
"""
import os
import logging
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tables():
    """Vérifier que toutes les tables et colonnes nécessaires existent"""
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
        
        # Vérifier que la table customer existe
        with engine.connect() as conn:
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='customer')"))
            exists = result.scalar()
            
            if not exists:
                logger.error("Table 'customer' does not exist")
                return False
            
            # Vérifier que les colonnes nécessaires existent
            required_columns = [
                'persona', 'avatar_url', 'avatar_prompt', 'purchased_products', 'niche_attributes', 
                'profile_data', 'usage_count'
            ]
            
            for column in required_columns:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name='customer' AND column_name=:column)"), {"column": column})
                exists = result.scalar()
                
                if not exists:
                    logger.error(f"Column '{column}' does not exist in table 'customer'")
                    return False
                else:
                    logger.info(f"Column '{column}' exists in table 'customer'")
            
            # Vérifier les type des colonnes JSONB
            jsonb_columns = ['profile_data', 'purchased_products', 'niche_attributes', 'social_media']
            for column in jsonb_columns:
                result = conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name='customer' AND column_name=:column"), {"column": column})
                data_type = result.scalar()
                
                if data_type != 'jsonb':
                    logger.warning(f"Column '{column}' is of type '{data_type}', should be 'jsonb'")
            
            # Vérifier la table campaign
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='campaign')"))
            exists = result.scalar()
            
            if not exists:
                logger.error("Table 'campaign' does not exist")
                return False
            
            # Vérifier que les colonnes nécessaires dans campaign existent
            campaign_required_columns = [
                'image_url', 'image_alt_text', 'image_title', 'image_description', 
                'image_keywords', 'image_prompt', 'profile_data'
            ]
            
            for column in campaign_required_columns:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name='campaign' AND column_name=:column)"), {"column": column})
                exists = result.scalar()
                
                if not exists:
                    logger.error(f"Column '{column}' does not exist in table 'campaign'")
                    return False
                else:
                    logger.info(f"Column '{column}' exists in table 'campaign'")
        
        logger.info("All required tables and columns exist")
        return True
        
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return False

if __name__ == "__main__":
    # Vérifier les tables
    success = check_tables()
    
    if success:
        print("All required tables and columns exist")
    else:
        print("Some required tables or columns are missing")
        
        # Exécuter les scripts de migration
        print("Running migration scripts...")
        
        # Importer et exécuter les migrations
        from add_usage_count import run_migration as add_usage_count_migration
        from add_avatar_prompt import run_migration as add_avatar_prompt_migration
        from db_migrate import run_migration as db_migrate_migration
        
        add_usage_count_migration()
        add_avatar_prompt_migration()
        db_migrate_migration()
        
        # Vérifier à nouveau
        print("Checking tables after migrations...")
        if check_tables():
            print("All required tables and columns now exist")
        else:
            print("Still missing some required tables or columns")