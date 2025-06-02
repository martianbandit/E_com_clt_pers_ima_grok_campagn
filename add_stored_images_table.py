"""
Script de migration pour ajouter la table StoredImage pour le stockage persistant des images IA
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import logging

# Configuration de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

def run_migration():
    """Execute the database migration to add stored_images table"""
    try:
        # Connexion à la base de données
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
        
        engine = create_engine(database_url)
        
        # Créer la table stored_images
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stored_images (
            id SERIAL PRIMARY KEY,
            hash VARCHAR(32) UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            local_path TEXT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            prompt TEXT NOT NULL,
            model VARCHAR(50) NOT NULL,
            size VARCHAR(20) DEFAULT '1024x1024',
            image_type VARCHAR(50) DEFAULT 'general',
            file_size INTEGER,
            content_type VARCHAR(50),
            user_id VARCHAR REFERENCES users(id),
            entity_id INTEGER,
            is_permanent BOOLEAN DEFAULT FALSE,
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Créer l'index sur le hash
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_stored_images_hash ON stored_images(hash);
        CREATE INDEX IF NOT EXISTS idx_stored_images_user_id ON stored_images(user_id);
        CREATE INDEX IF NOT EXISTS idx_stored_images_type ON stored_images(image_type);
        CREATE INDEX IF NOT EXISTS idx_stored_images_created ON stored_images(created_at);
        """
        
        with engine.connect() as conn:
            # Créer la table
            conn.execute(text(create_table_sql))
            logger.info("Table stored_images créée avec succès")
            
            # Créer les index
            conn.execute(text(create_index_sql))
            logger.info("Index créés avec succès")
            
            # Commit des changements
            conn.commit()
            
        logger.info("Migration de la table stored_images terminée avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la migration: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)