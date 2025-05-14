"""
Script de migration pour mettre à jour la table osp_analysis
"""
import os
from datetime import datetime
from app import db

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSON, JSONB
import enum


class Base(declarative_base()):
    pass


def run_migration():
    """Execute the database migration to update osp_analysis table"""
    try:
        print("Début de la migration pour mettre à jour la table osp_analysis...")
        
        # Créer une connexion à la base de données
        engine = db.engine
        connection = engine.connect()
        
        # Vérifier l'existence de la colonne html_result
        html_result_exists = False
        check_html_result = connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'osp_analysis' AND column_name = 'html_result'"
        ).fetchall()
        html_result_exists = len(check_html_result) > 0
        
        # Exécuter les requêtes SQL pour modifier la table
        if not html_result_exists:
            print("Ajout de la colonne html_result...")
            connection.execute("ALTER TABLE osp_analysis ADD COLUMN html_result TEXT")
        
        print("Migration terminée avec succès!")
        connection.close()
        return True
    except Exception as e:
        print(f"Erreur lors de la migration: {str(e)}")
        return False


if __name__ == "__main__":
    run_migration()