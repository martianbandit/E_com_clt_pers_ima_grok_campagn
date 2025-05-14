"""
Script pour mettre à jour la structure de la base de données
et assurer qu'elle correspond aux modèles définis dans l'application.
"""

import os
import logging
from sqlalchemy import inspect, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurez le logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Récupérer l'URL de la base de données depuis les variables d'environnement
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# Assurez-vous que l'URL commence par postgresql:// (et non postgres://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Créez un moteur SQLAlchemy pour la connexion à la base de données
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()
inspector = inspect(engine)

def execute_sql(sql, params=None):
    """Exécute une requête SQL avec gestion d'erreurs robuste"""
    try:
        if params:
            session.execute(sql, params)
        else:
            session.execute(sql)
        session.commit()
        logger.info(f"SQL executed successfully: {sql}")
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"SQL error: {e}")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error: {e}")
        return False

def table_exists(table_name):
    """Vérifie si une table existe dans la base de données"""
    return inspector.has_table(table_name)

def column_exists(table_name, column_name):
    """Vérifie si une colonne existe dans une table"""
    if not table_exists(table_name):
        return False
    
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_column_if_not_exists(table_name, column_name, column_type):
    """Ajoute une colonne à une table si elle n'existe pas déjà"""
    if not table_exists(table_name):
        logger.error(f"Table {table_name} does not exist")
        return False
    
    if column_exists(table_name, column_name):
        logger.info(f"Column {column_name} already exists in table {table_name}")
        return True
    
    sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    return execute_sql(sql)

def update_database_schema():
    """Met à jour le schéma de la base de données pour correspondre aux modèles"""
    # Mise à jour de la table campaign
    add_column_if_not_exists("campaign", "language", "VARCHAR(5) DEFAULT 'fr'")
    add_column_if_not_exists("campaign", "multilingual_campaign", "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists("campaign", "target_languages", "JSON DEFAULT '[]'::jsonb")
    add_column_if_not_exists("campaign", "impressions", "INTEGER DEFAULT 0")
    add_column_if_not_exists("campaign", "clicks", "INTEGER DEFAULT 0")
    add_column_if_not_exists("campaign", "conversions", "INTEGER DEFAULT 0")
    add_column_if_not_exists("campaign", "engagement_rate", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("campaign", "roi", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("campaign", "cost_per_acquisition", "FLOAT DEFAULT 0.0")
    
    # Mise à jour de la table boutique
    add_column_if_not_exists("boutique", "language", "VARCHAR(5) DEFAULT 'fr'")
    add_column_if_not_exists("boutique", "multilingual_enabled", "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists("boutique", "supported_languages", "JSON DEFAULT '[]'::jsonb")
    
    # Mise à jour de la table product
    add_column_if_not_exists("product", "html_description", "TEXT")
    add_column_if_not_exists("product", "html_details", "TEXT")
    add_column_if_not_exists("product", "html_features", "TEXT")
    
    # Mise à jour de la table customer
    add_column_if_not_exists("customer", "usage_count", "INTEGER DEFAULT 0")
    add_column_if_not_exists("customer", "avatar_prompt", "TEXT")
    
    # Mise à jour de la table imported_product s'il existe
    if table_exists("imported_product"):
        add_column_if_not_exists("imported_product", "import_status", "VARCHAR(20) DEFAULT 'pending'")
        add_column_if_not_exists("imported_product", "source_id", "VARCHAR(50)")
    
    logger.info("Database schema update completed")

if __name__ == "__main__":
    update_database_schema()