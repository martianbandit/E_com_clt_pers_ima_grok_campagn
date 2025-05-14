"""
Script de migration pour ajouter la colonne numeric_id à la table User
"""

import os
import sys
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine, text
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import Table, MetaData

Base = declarative_base()

def run_migration():
    """Execute the database migration to add numeric_id column"""
    # Connexion à la base de données
    database_url = os.environ.get("DATABASE_URL")
    engine = create_engine(database_url)
    
    # Session et métadonnées
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Vérification de l'existence de la colonne
        metadata = MetaData()
        users_table = Table('users', metadata, autoload_with=engine)
        if 'numeric_id' not in users_table.columns:
            # Ajout de la colonne
            print("Ajout de la colonne numeric_id à la table users...")
            session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN numeric_id INTEGER NULL;
            """))
            print("Colonne numeric_id ajoutée avec succès.")
            
            # Mise à jour des users existants avec ID numérique
            print("Migration des ID numériques...")
            session.execute(text("""
                UPDATE users 
                SET numeric_id = CASE 
                    WHEN id ~ E'^\\d+$' THEN id::INTEGER 
                    ELSE NULL 
                END;
            """))
            print("Migration des ID numériques terminée.")
        else:
            print("La colonne numeric_id existe déjà dans la table users.")
        
        session.commit()
        print("Migration terminée avec succès.")
    except Exception as e:
        session.rollback()
        print(f"Erreur lors de la migration : {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()