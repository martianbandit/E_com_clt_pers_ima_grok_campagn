"""
Script de migration pour mettre à jour la table Metric
- Ajouter la colonne execution_time
- Modifier le type de la colonne status de String à Boolean
"""
import os
import sys
import logging
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData, Table, Column, inspect
from sqlalchemy.exc import SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy.orm import DeclarativeBase

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Base(DeclarativeBase):
    pass

def run_migration():
    """Execute la migration de base de données pour mettre à jour la table Metric"""
    try:
        # Créer une application Flask temporaire
        app = Flask(__name__)
        
        # Configurer la base de données
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        
        # Initialiser SQLAlchemy
        db = SQLAlchemy(model_class=Base)
        db.init_app(app)
        
        # Exécuter dans le contexte de l'application
        with app.app_context():
            # Créer une connexion à la base de données
            engine = db.engine
            connection = engine.connect()
            
            # Vérifier si la table metric existe
            inspector = inspect(engine)
            if 'metric' not in inspector.get_table_names():
                logging.error("La table metric n'existe pas dans la base de données.")
                return False
            
            # Vérifier si la colonne execution_time existe déjà
            columns = [c['name'] for c in inspector.get_columns('metric')]
            
            # Début de la transaction
            trans = connection.begin()
            
            try:
                # 1. Ajouter la colonne execution_time si elle n'existe pas
                if 'execution_time' not in columns:
                    logging.info("Ajout de la colonne execution_time à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric 
                        ADD COLUMN execution_time FLOAT;
                    """))
                    logging.info("Colonne execution_time ajoutée avec succès.")
                else:
                    logging.info("La colonne execution_time existe déjà.")
                
                # 2. Ajout de la colonne status si elle n'existe pas
                if 'status' not in columns:
                    logging.info("Ajout de la colonne status (BOOLEAN) à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric ADD COLUMN status BOOLEAN DEFAULT TRUE;
                    """))
                    logging.info("Colonne status (BOOLEAN) ajoutée avec succès.")
                else:
                    # Vérification du type de colonne status
                    connection.execute(text("""
                        ALTER TABLE metric ALTER COLUMN status TYPE BOOLEAN USING 
                        CASE 
                            WHEN status::text = 'success' THEN TRUE
                            ELSE FALSE
                        END;
                    """))
                    logging.info("Colonne status convertie en BOOLEAN si nécessaire.")
                
                # 3. Ajout de la colonne category si elle n'existe pas
                if 'category' not in columns:
                    logging.info("Ajout de la colonne category à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric ADD COLUMN category VARCHAR(50);
                    """))
                    logging.info("Colonne category ajoutée avec succès.")
                    
                # 4. Ajout de la colonne response_time si elle n'existe pas
                if 'response_time' not in columns:
                    logging.info("Ajout de la colonne response_time à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric ADD COLUMN response_time FLOAT;
                    """))
                    logging.info("Colonne response_time ajoutée avec succès.")
                    
                # 5. Ajout de la colonne user_id si elle n'existe pas
                if 'user_id' not in columns:
                    logging.info("Ajout de la colonne user_id à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric ADD COLUMN user_id INTEGER;
                    """))
                    logging.info("Colonne user_id ajoutée avec succès.")
                    
                # 6. Ajout de la colonne customer_id si elle n'existe pas
                if 'customer_id' not in columns:
                    logging.info("Ajout de la colonne customer_id à la table metric...")
                    connection.execute(text("""
                        ALTER TABLE metric ADD COLUMN customer_id INTEGER;
                    """))
                    logging.info("Colonne customer_id ajoutée avec succès.")
                
                # Commit de la transaction
                trans.commit()
                logging.info("Migration de la table Metric terminée avec succès.")
                return True
            
            except SQLAlchemyError as e:
                # Rollback en cas d'erreur
                trans.rollback()
                logging.error(f"Erreur lors de la migration: {e}")
                return False
            
            finally:
                # Fermer la connexion
                connection.close()
    
    except Exception as e:
        logging.error(f"Erreur lors de la migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)