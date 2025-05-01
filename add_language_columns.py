"""
Script de migration pour ajouter les colonnes linguistiques aux tables Boutique et Campaign
"""
import os
import logging
from datetime import datetime
from sqlalchemy import Column, String, Boolean, create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# No need for Base class in migration script

def run_migration():
    """Execute the database migration to add language columns"""
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connexion à la base de données
        engine = create_engine(database_url)
        metadata = MetaData()
        metadata.reflect(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Vérifier si la table boutique existe
        if 'boutique' in metadata.tables:
            # Ajouter la colonne language si elle n'existe pas déjà
            if 'language' not in metadata.tables['boutique'].columns:
                logger.info("Ajout de la colonne 'language' à la table 'boutique'")
                # Import local text import already available global
                session.execute(text("""
                    ALTER TABLE boutique
                    ADD COLUMN language VARCHAR(10) DEFAULT 'en';
                """))
                
                # Ajouter la colonne multilingual_enabled
                logger.info("Ajout de la colonne 'multilingual_enabled' à la table 'boutique'")
                session.execute(text("""
                    ALTER TABLE boutique
                    ADD COLUMN multilingual_enabled BOOLEAN DEFAULT false;
                """))
                
                # Ajouter la colonne supported_languages (JSON array)
                logger.info("Ajout de la colonne 'supported_languages' à la table 'boutique'")
                session.execute(text("""
                    ALTER TABLE boutique
                    ADD COLUMN supported_languages JSONB DEFAULT '["en", "fr"]'::jsonb;
                """))
                
                session.commit()
                logger.info("Colonnes linguistiques ajoutées avec succès à la table 'boutique'")
            else:
                logger.info("La colonne 'language' existe déjà dans la table 'boutique'")
        else:
            logger.error("La table 'boutique' n'existe pas dans la base de données")
            return False
            
        # Vérifier si la table campaign existe
        if 'campaign' in metadata.tables:
            # Ajouter la colonne language si elle n'existe pas déjà
            if 'language' not in metadata.tables['campaign'].columns:
                logger.info("Ajout de la colonne 'language' à la table 'campaign'")
                session.execute(text("""
                    ALTER TABLE campaign
                    ADD COLUMN language VARCHAR(10) DEFAULT 'en';
                """))
                
                # Ajouter la colonne multilingual_campaign (pour les campagnes multilingues)
                logger.info("Ajout de la colonne 'multilingual_campaign' à la table 'campaign'")
                session.execute(text("""
                    ALTER TABLE campaign
                    ADD COLUMN multilingual_campaign BOOLEAN DEFAULT false;
                """))
                
                # Ajouter la colonne target_languages (JSON array)
                logger.info("Ajout de la colonne 'target_languages' à la table 'campaign'")
                session.execute(text("""
                    ALTER TABLE campaign
                    ADD COLUMN target_languages JSONB DEFAULT '["en"]'::jsonb;
                """))
                
                session.commit()
                logger.info("Colonnes linguistiques ajoutées avec succès à la table 'campaign'")
            else:
                logger.info("La colonne 'language' existe déjà dans la table 'campaign'")
        else:
            logger.warning("La table 'campaign' n'existe pas dans la base de données")
            
        # Vérifier si la table customer existe
        if 'customer' in metadata.tables:
            # Ajouter la colonne preferred_language si elle n'existe pas déjà
            if 'preferred_language' not in metadata.tables['customer'].columns:
                logger.info("Ajout de la colonne 'preferred_language' à la table 'customer'")
                session.execute(text("""
                    ALTER TABLE customer
                    ADD COLUMN preferred_language VARCHAR(10) DEFAULT NULL;
                """))
                
                session.commit()
                logger.info("Colonne linguistique ajoutée avec succès à la table 'customer'")
            else:
                logger.info("La colonne 'preferred_language' existe déjà dans la table 'customer'")
        else:
            logger.warning("La table 'customer' n'existe pas dans la base de données")
            
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la migration: {str(e)}")
        return False

if __name__ == "__main__":
    # Exécuter la migration
    success = run_migration()
    if success:
        print("Migration réussie!")
    else:
        print("Échec de la migration.")