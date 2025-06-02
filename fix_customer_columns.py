
#!/usr/bin/env python3
"""
Script pour corriger les colonnes manquantes dans la table Customer
"""

import os
import sys
from sqlalchemy import text

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_customer_columns():
    """Ajouter les colonnes manquantes à la table Customer"""
    with app.app_context():
        try:
            # Vérifier et ajouter la colonne objectif si elle n'existe pas
            db.session.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'customer' AND column_name = 'objectif'
                    ) THEN
                        ALTER TABLE customer ADD COLUMN objectif TEXT;
                    END IF;
                END $$;
            """))
            
            # Vérifier et ajouter la colonne user_id si elle n'existe pas
            db.session.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'customer' AND column_name = 'user_id'
                    ) THEN
                        ALTER TABLE customer ADD COLUMN user_id VARCHAR(36);
                    END IF;
                END $$;
            """))
            
            db.session.commit()
            print("✅ Colonnes Customer mises à jour avec succès")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la mise à jour: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = fix_customer_columns()
    sys.exit(0 if success else 1)
