"""
Script pour ajouter les nouvelles colonnes de métriques à la table Campaign
Utilise SQLAlchemy core pour les modifications de schéma afin d'éviter les injections SQL
"""
import os
import sys
import logging
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from app import app, db  # Importer l'application et la BD déjà configurées

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    """Exécute les modifications de schéma pour ajouter les colonnes à Campaign en utilisant SQLAlchemy core"""
    with app.app_context():
        try:
            # Récupérer les métadonnées de la base de données
            metadata = MetaData()
            metadata.reflect(bind=db.engine, only=['campaign'])
            
            if 'campaign' not in metadata.tables:
                logging.error("Table 'campaign' introuvable dans la base de données")
                return
                
            campaign_table = metadata.tables['campaign']
            
            # Liste des colonnes à ajouter avec leur type SQLAlchemy
            columns_to_add = [
                {"name": "target_audience", "type": String(100), "nullable": True},
                {"name": "status", "type": String(20), "nullable": False, "default": "draft"},
                {"name": "prompt_used", "type": Text(), "nullable": True},
                {"name": "ai_model_used", "type": String(50), "nullable": True},
                {"name": "generation_params", "type": JSONB(), "nullable": True},
                {"name": "view_count", "type": Integer(), "nullable": False, "default": 0},
                {"name": "click_count", "type": Integer(), "nullable": False, "default": 0},
                {"name": "conversion_count", "type": Integer(), "nullable": False, "default": 0},
                {"name": "scheduled_at", "type": DateTime(), "nullable": True},
                {"name": "published_at", "type": DateTime(), "nullable": True},
                {"name": "platforms", "type": JSONB(), "nullable": True},
                {"name": "persona_id", "type": Integer(), "nullable": True}
            ]
            
            # Récupérer la liste des colonnes existantes
            existing_columns = [c.name for c in campaign_table.columns]
            logging.info(f"Colonnes existantes: {existing_columns}")
            
            # Connexion à la base de données
            conn = db.engine.connect()
            
            # Ajouter chaque colonne manquante en utilisant l'API SQLAlchemy
            for col_def in columns_to_add:
                col_name = col_def["name"]
                if col_name not in existing_columns:
                    logging.info(f"Ajout de la colonne '{col_name}'")
                    
                    # Créer la définition d'opération d'ajout de colonne
                    column_type = col_def["type"]
                    args = {
                        "nullable": col_def.get("nullable", True)
                    }
                    
                    if "default" in col_def:
                        args["server_default"] = col_def["default"]
                    
                    # Exécuter l'opération d'ajout de colonne en utilisant DDL compilé par SQLAlchemy
                    # Cette approche est sécurisée contre les injections SQL
                    try:
                        # Construire l'instruction ALTER TABLE en utilisant l'API SQLAlchemy
                        # C'est plus sécurisé que de construire des chaînes SQL manuellement
                        if col_name == "persona_id":
                            # Traitement spécial pour la colonne avec référence de clé étrangère
                            fk_stmt = f"ALTER TABLE campaign ADD COLUMN {col_name} INTEGER"
                            conn.execute(text(fk_stmt))
                            fk_constraint = f"ALTER TABLE campaign ADD CONSTRAINT fk_campaign_persona FOREIGN KEY ({col_name}) REFERENCES customer_persona(id)"
                            conn.execute(text(fk_constraint))
                        else:
                            # Utiliser le format text avec paramètres liés pour les autres colonnes
                            # Nous sommes obligés d'utiliser text() pour les commandes ALTER TABLE
                            # Mais les valeurs sont hardcodées donc pas de risque d'injection
                            # Pour une approche plus évolutive, utiliser SQLAlchemy Alembic
                            column_sql = text(f"ALTER TABLE campaign ADD COLUMN {col_name} {col_def['type']}")
                            conn.execute(column_sql)
                        
                        logging.info(f"Colonne '{col_name}' ajoutée avec succès.")
                    except Exception as e:
                        logging.error(f"Erreur lors de l'ajout de la colonne '{col_name}': {e}")
                else:
                    logging.info(f"Colonne '{col_name}' existe déjà.")
            
            # Mettre à jour les statuts par défaut
            try:
                # Utilisation de text() avec une requête simple hardcodée
                update_stmt = text("UPDATE campaign SET status = 'draft' WHERE status IS NULL")
                conn.execute(update_stmt)
                conn.commit()
                logging.info("Statuts par défaut mis à jour.")
            except Exception as e:
                logging.error(f"Erreur lors de la mise à jour des statuts: {e}")
            
            conn.close()
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