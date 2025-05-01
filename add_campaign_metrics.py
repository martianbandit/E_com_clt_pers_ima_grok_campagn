"""
Script pour ajouter les nouvelles colonnes de métriques à la table Campaign
"""
import os
import sys
import logging
from sqlalchemy import text
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from app import app, db  # Importer l'application et la BD déjà configurées

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    """Exécute les requêtes SQL pour ajouter les colonnes à Campaign"""
    with app.app_context():
        try:
            # Liste des colonnes à ajouter
            columns = [
                ("target_audience", "VARCHAR(100) NULL"),
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'draft'"),
                ("prompt_used", "TEXT NULL"),
                ("ai_model_used", "VARCHAR(50) NULL"),
                ("generation_params", "JSONB NULL"),
                ("view_count", "INTEGER NOT NULL DEFAULT 0"),
                ("click_count", "INTEGER NOT NULL DEFAULT 0"),
                ("conversion_count", "INTEGER NOT NULL DEFAULT 0"),
                ("scheduled_at", "TIMESTAMP NULL"),
                ("published_at", "TIMESTAMP NULL"),
                ("platforms", "JSONB NULL"),
                ("persona_id", "INTEGER NULL REFERENCES customer_persona(id)")
            ]
            
            conn = db.engine.connect()
            
            # Vérifier les colonnes existantes
            existing_columns = []
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'campaign'"))
            for row in result:
                existing_columns.append(row[0])
            
            logging.info(f"Colonnes existantes: {existing_columns}")
            
            # Ajouter les colonnes manquantes
            for column_name, column_definition in columns:
                if column_name not in existing_columns:
                    sql = f"ALTER TABLE campaign ADD COLUMN {column_name} {column_definition};"
                    logging.info(f"Exécution: {sql}")
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        logging.info(f"Colonne '{column_name}' ajoutée avec succès.")
                    except Exception as e:
                        logging.error(f"Erreur lors de l'ajout de la colonne '{column_name}': {e}")
                else:
                    logging.info(f"Colonne '{column_name}' existe déjà.")
            
            # Mettre à jour les statuts par défaut
            if "status" in [col[0] for col in columns]:
                try:
                    sql = "UPDATE campaign SET status = 'draft' WHERE status IS NULL;"
                    conn.execute(text(sql))
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