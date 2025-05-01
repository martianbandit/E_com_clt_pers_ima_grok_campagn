"""
Script de migration pour ajouter la colonne boutique_id à la table Campaign
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("Erreur: La variable d'environnement DATABASE_URL n'est pas définie")
    sys.exit(1)

# Création du moteur SQLAlchemy
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

def run_migration():
    """Execute the database migration to add boutique_id column"""
    try:
        # Vérifier si la colonne existe déjà
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'campaign' AND column_name = 'boutique_id'")
            )
            if result.rowcount > 0:
                print("La colonne boutique_id existe déjà dans la table Campaign")
                return False
            
            # Ajouter la colonne boutique_id
            conn.execute(text("ALTER TABLE campaign ADD COLUMN boutique_id INTEGER REFERENCES boutique(id)"))
            conn.commit()
            print("✅ Colonne boutique_id ajoutée avec succès à la table Campaign")
            return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {str(e)}")
        return False

if __name__ == "__main__":
    successful = run_migration()
    sys.exit(0 if successful else 1)