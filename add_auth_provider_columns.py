"""
Script de migration pour ajouter les colonnes github_id et google_id à la table User
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, String, MetaData, Table, inspect, text
from sqlalchemy.ext.declarative import declarative_base

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("La variable d'environnement DATABASE_URL n'est pas définie.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Définition de Base pour les modèles SQLAlchemy
Base = declarative_base()


def run_migration():
    """Execute the database migration to add auth provider columns"""
    # Vérifier si les colonnes existent déjà
    inspector = inspect(engine)
    user_columns = [col["name"] for col in inspector.get_columns("users")]
    
    # Liste des colonnes à ajouter
    columns_to_add = []
    if "github_id" not in user_columns:
        columns_to_add.append(("github_id", String(50)))
    if "google_id" not in user_columns:
        columns_to_add.append(("google_id", String(50)))
    
    # Si aucune colonne à ajouter, sortir
    if not columns_to_add:
        print("Les colonnes github_id et google_id existent déjà dans la table users.")
        return
    
    # Connexion à la base de données
    print(f"Connexion à la base de données: {DATABASE_URL}")
    try:
        with engine.begin() as connection:
            # Ajout des colonnes en utilisant les méthodes DDL de SQLAlchemy
            for column_name, column_type in columns_to_add:
                print(f"Ajout de la colonne {column_name} à la table users...")
                # Utilisation des opérations de DDL sécurisées au lieu de SQL brut
                users_table = Table('users', metadata, autoload_with=engine)
                column = Column(column_name, String(50), unique=True)
                column_addition = users_table.append_column(column)
                connection.execute(column_addition)
            
            print("Migration terminée avec succès.")
    except Exception as e:
        print(f"Erreur lors de la migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()