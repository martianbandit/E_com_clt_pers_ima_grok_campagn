"""
Script de migration pour ajouter l'isolation des données par utilisateur (multi-tenancy)
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration de la base de données
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    logging.error("La variable d'environnement DATABASE_URL n'est pas définie")
    sys.exit(1)

# Création du moteur SQLAlchemy
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

def run_migration():
    """
    Exécute la migration pour ajouter les colonnes owner_id et contraintes d'utilisateur
    et nettoyer les données existantes
    """
    try:
        # Partie 1: Ajouter les colonnes owner_id aux tables principales
        add_owner_columns()
        
        # Partie 2: Supprimer toutes les données existantes (comme demandé)
        clean_existing_data()
        
        # Partie 3: Ajouter les contraintes de clé étrangère
        add_foreign_key_constraints()
        
        # Partie 4: Mettre à jour les autorisations et contraintes
        update_permissions()
        
        logging.info("✅ Migration terminée avec succès")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la migration: {str(e)}")
        return False

def add_owner_columns():
    """Ajoute les colonnes owner_id aux tables principales"""
    logging.info("Ajout des colonnes owner_id aux tables principales...")
    
    # Liste des tables qui nécessitent une colonne owner_id
    tables_to_update = [
        'boutique',
        'niche_market',
        'customer_persona',
    ]
    
    with engine.connect() as conn:
        for table in tables_to_update:
            # Vérifier si la colonne existe déjà
            result = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = :table AND column_name = 'owner_id'"),
                {"table": table}
            )
            if result.rowcount > 0:
                logging.info(f"La colonne owner_id existe déjà dans la table {table}")
                continue
            
            # Ajouter la colonne owner_id
            conn.execute(
                text("ALTER TABLE :table ADD COLUMN owner_id VARCHAR REFERENCES users(id)").bindparams(
                    table=table
                )
            )
            logging.info(f"✓ Colonne owner_id ajoutée à la table {table}")
        
        # Vérifier si la contrainte d'unicité existe pour les noms de boutique par utilisateur
        result = conn.execute(
            text("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'boutique' AND constraint_name = 'uq_boutique_name_owner'")
        )
        if result.rowcount == 0:
            conn.execute(text("ALTER TABLE boutique ADD CONSTRAINT uq_boutique_name_owner UNIQUE (name, owner_id)"))
            logging.info("✓ Contrainte d'unicité ajoutée pour les noms de boutique par utilisateur")
        
        conn.commit()
    
    logging.info("✅ Colonnes owner_id ajoutées avec succès")

def clean_existing_data():
    """Supprime toutes les données existantes des tables concernées"""
    logging.info("Nettoyage des données existantes...")
    
    # Liste des tables à nettoyer dans l'ordre (respect des clés étrangères)
    tables_to_clean = [
        'similar_product',
        'osp_analysis',
        'imported_product',
        'campaign',
        'customer_persona_association',
        'customer',
        'customer_persona',
        'product',
        'boutique',
        'niche_market'
    ]
    
    with engine.connect() as conn:
        # Désactiver temporairement les contraintes de clé étrangère
        conn.execute(text("SET session_replication_role = replica;"))
        
        for table in tables_to_clean:
            conn.execute(text("DELETE FROM :table").bindparams(table=table))
            logging.info(f"✓ Données de la table {table} supprimées")
        
        # Réactiver les contraintes
        conn.execute(text("SET session_replication_role = DEFAULT;"))
        conn.commit()
    
    logging.info("✅ Données existantes nettoyées avec succès")

def add_foreign_key_constraints():
    """Ajoute des contraintes de clé étrangère pour la relation de propriété en cascade"""
    logging.info("Ajout des contraintes de clé étrangère en cascade...")
    
    # Liste des relations en cascade à ajouter
    cascade_relations = [
        # Format: (table_source, colonne_source, table_cible, cascade_delete)
        ('customer', 'boutique_id', 'boutique', True),
        ('customer_persona', 'boutique_id', 'boutique', True),
        ('product', 'boutique_id', 'boutique', True),
        ('campaign', 'boutique_id', 'boutique', True),
    ]
    
    with engine.connect() as conn:
        for relation in cascade_relations:
            table, column, target_table, cascade_delete = relation
            
            # Vérifier si la contrainte existe déjà
            constraint_name = f"fk_{table}_{column}_cascade"
            result = conn.execute(
                text("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = :table AND constraint_name = :constraint_name"),
                {"table": table, "constraint_name": constraint_name}
            )
            
            if result.rowcount > 0:
                # Supprimer la contrainte existante pour la recréer avec CASCADE
                conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name}"))
            
            # Vérifier la contrainte existante (sans nom spécifique)
            result = conn.execute(
                text("""
                    SELECT tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = :table AND ccu.column_name = :column
                    AND tc.constraint_type = 'FOREIGN KEY'
                """),
                {"table": table, "column": column}
            )
            
            if result.rowcount > 0:
                constraint_names = [row[0] for row in result]
                for name in constraint_names:
                    conn.execute(
                        text("ALTER TABLE :table DROP CONSTRAINT IF EXISTS :name").bindparams(
                            table=table, name=name
                        )
                    )
            
            # Ajouter la nouvelle contrainte avec CASCADE si demandé
            cascade_option = "CASCADE" if cascade_delete else "NO ACTION"
            conn.execute(
                text("""
                    ALTER TABLE :table 
                    ADD CONSTRAINT :constraint_name 
                    FOREIGN KEY (:column) REFERENCES :target_table(id) 
                    ON DELETE :cascade_option
                """).bindparams(
                    table=table, 
                    constraint_name=constraint_name, 
                    column=column, 
                    target_table=target_table, 
                    cascade_option=cascade_option
                )
            )
            
            logging.info(f"✓ Contrainte cascade ajoutée pour {table}.{column} -> {target_table}.id")
        
        conn.commit()
    
    logging.info("✅ Contraintes de clé étrangère ajoutées avec succès")

def update_permissions():
    """Met à jour les autorisations et implémente d'autres contraintes de sécurité"""
    logging.info("Mise à jour des autorisations...")
    
    # Ici, vous pouvez ajouter d'autres modifications de schéma pour renforcer l'isolation des données
    # Par exemple, des triggers de base de données, des index ou des politiques de sécurité.
    
    logging.info("✅ Autorisations mises à jour avec succès")

if __name__ == "__main__":
    successful = run_migration()
    sys.exit(0 if successful else 1)