
"""
Script de migration pour ajouter les tables d'audit SEO
"""
from app import app, db
from models import SEOAudit, SEOKeyword
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_seo_audit_tables():
    """Ajoute les tables pour le système d'audit SEO"""
    try:
        with app.app_context():
            # Créer les tables
            db.create_all()
            logger.info("Tables d'audit SEO créées avec succès")
            
            # Effectuer d'autres migrations si nécessaire ici
            
            return True
    except Exception as e:
        logger.error(f"Erreur lors de la création des tables d'audit SEO: {e}")
        return False

if __name__ == "__main__":
    success = add_seo_audit_tables()
    if success:
        print("Migration terminée avec succès")
    else:
        print("Migration échouée, vérifiez les logs")
