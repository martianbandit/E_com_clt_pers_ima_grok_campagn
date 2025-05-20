"""
Script de migration pour mettre à jour la table de campagnes avec les nouveaux champs
"""
import os
import sys
import datetime
import json
import logging
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy import create_engine, MetaData, Table, ForeignKey
from sqlalchemy.exc import OperationalError, ProgrammingError
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URL de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logging.error("La variable d'environnement DATABASE_URL n'est pas définie.")
    sys.exit(1)

# Créer une application Flask minimale et une instance SQLAlchemy
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

def run_migration():
    """Exécute la migration pour mettre à jour la table Campaign"""
    with app.app_context():
        try:
            # Afficher l'état actuel de la table Campaign
            engine = db.engine
            metadata = MetaData()
            metadata.reflect(bind=engine, only=['campaign'])
            
            if 'campaign' not in metadata.tables:
                logging.error("La table 'campaign' n'existe pas dans la base de données.")
                return
                
            campaign_table = metadata.tables['campaign']
            logging.info("État actuel de la table campaign:")
            for column in campaign_table.columns:
                logging.info(f"  {column.name}: {column.type}")
                
            # Liste des colonnes à ajouter
            new_columns = [
                {'name': 'target_audience', 'type': String(100), 'nullable': True},
                {'name': 'status', 'type': String(20), 'nullable': False, 'default': "draft"},
                {'name': 'prompt_used', 'type': Text(), 'nullable': True},
                {'name': 'ai_model_used', 'type': String(50), 'nullable': True},
                {'name': 'generation_params', 'type': JSONB(), 'nullable': True},
                {'name': 'view_count', 'type': Integer(), 'nullable': False, 'default': 0},
                {'name': 'click_count', 'type': Integer(), 'nullable': False, 'default': 0},
                {'name': 'conversion_count', 'type': Integer(), 'nullable': False, 'default': 0},
                {'name': 'scheduled_at', 'type': DateTime(), 'nullable': True},
                {'name': 'published_at', 'type': DateTime(), 'nullable': True},
                {'name': 'platforms', 'type': JSONB(), 'nullable': True},
                {'name': 'persona_id', 'type': Integer(), 'nullable': True},
            ]
            
            # Compter les colonnes existantes/manquantes
            existing_columns = [col.name for col in campaign_table.columns]
            columns_to_add = [col for col in new_columns if col['name'] not in existing_columns]
            
            logging.info(f"Colonnes à ajouter: {len(columns_to_add)}")
            
            if not columns_to_add:
                logging.info("Aucune nouvelle colonne à ajouter. La migration est déjà à jour.")
                return
                
            # Exécuter les commandes ALTER TABLE
            for column_info in columns_to_add:
                column_name = column_info['name']
                column_type = column_info['type']
                nullable = 'NULL' if column_info.get('nullable', True) else 'NOT NULL'
                
                default_clause = ""
                if 'default' in column_info:
                    default_value = column_info['default']
                    if isinstance(default_value, str):
                        default_clause = f" DEFAULT '{default_value}'"
                    elif isinstance(default_value, (int, float, bool)):
                        default_clause = f" DEFAULT {default_value}"
                    elif default_value is None:
                        default_clause = " DEFAULT NULL"
                
                # Utiliser l'API SQLAlchemy au lieu d'exécuter directement SQL
                logging.info(f"Ajout de la colonne '{column_name}' de type {column_type}")
                try:
                    with engine.connect() as conn:
                        # Vérifier si la colonne existe déjà
                        from sqlalchemy import text
                        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'campaign' AND column_name = :column_name"), {"column_name": column_name})
                        if result.rowcount == 0:
                            # Convertir le type SQLAlchemy en type SQL
                            sql_type = str(column_type.compile(dialect=engine.dialect))
                            # Construire et exécuter la commande ALTER TABLE en utilisant text() avec paramètres sécurisés
                            from sqlalchemy import text
                            alter_sql = text("ALTER TABLE campaign ADD COLUMN :column_name :sql_type :nullable:default_clause;")
                            conn.execute(alter_sql, {
                                "column_name": column_name,
                                "sql_type": sql_type,
                                "nullable": nullable,
                                "default_clause": default_clause
                            })
                            logging.info(f"Colonne '{column_name}' ajoutée avec succès.")
                        else:
                            logging.info(f"Colonne '{column_name}' existe déjà, ignorée.")
                except Exception as e:
                    logging.error(f"Erreur lors de l'ajout de la colonne '{column_name}': {e}")
            
            # Ajouter la contrainte foreign key pour persona_id si elle n'existe pas déjà
            if 'persona_id' in [col['name'] for col in columns_to_add]:
                try:
                    # Vérifier d'abord si la contrainte existe déjà
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'campaign' AND constraint_name = 'fk_campaign_persona'"))
                        if result.rowcount == 0:
                            fk_sql = text("ALTER TABLE campaign ADD CONSTRAINT fk_campaign_persona FOREIGN KEY (persona_id) REFERENCES customer_persona (id)")
                            conn.execute(fk_sql)
                            logging.info("Foreign key pour persona_id ajoutée avec succès.")
                        else:
                            logging.info("Foreign key pour persona_id existe déjà.")
                except Exception as e:
                    logging.error(f"Erreur lors de l'ajout de la foreign key: {e}")
            
            # Mettre à jour les statuts par défaut pour les campagnes existantes
            if 'status' in [col['name'] for col in columns_to_add]:
                try:
                    with engine.connect() as conn:
                        update_sql = text("UPDATE campaign SET status = :status WHERE status IS NULL")
                        conn.execute(update_sql, {"status": "draft"})
                        logging.info("Statuts par défaut mis à jour pour les campagnes existantes.")
                except Exception as e:
                    logging.error(f"Erreur lors de la mise à jour des statuts: {e}")
            
            logging.info("Migration terminée avec succès.")
            
        except Exception as e:
            logging.error(f"Erreur lors de la migration: {e}")
            raise

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logging.error(f"La migration a échoué: {e}")
        sys.exit(1)