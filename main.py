import sys
import logging
import traceback
from app import app, logger

def handle_exception(exc_type, exc_value, exc_traceback):
    """Fonction pour gérer les exceptions non interceptées pour éviter les redémarrages en boucle"""
    # Ignorer les interruptions par clavier (KeyboardInterrupt)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    # Log l'exception
    logger.error("Exception non gérée:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Afficher un message utilisateur
    print("Une erreur s'est produite. Veuillez consulter les logs pour plus de détails.")
    
    # Si nous sommes en mode interactif, ne pas quitter
    if hasattr(sys, 'ps1'):
        return
    
    # En production, attendre avant de quitter pour éviter les cycles de redémarrage rapides
    import time
    time.sleep(2)  # Pause de 2 secondes

# Configuration du handler d'exceptions
sys.excepthook = handle_exception

if __name__ == "__main__":
    try:
        logger.info("Démarrage de NinjaMark")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'application: {e}")
        logger.error(traceback.format_exc())
        # Attendre avant de quitter pour éviter les redémarrages en boucle
        import time
        time.sleep(5)
        sys.exit(1)
