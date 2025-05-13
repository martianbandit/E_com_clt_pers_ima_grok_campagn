import os
import logging
import signal
from openai import OpenAI
from functools import wraps
import errno
import time

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Définir un décorateur pour limiter le temps d'exécution d'une fonction
class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message="Timeout dépassé"):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            return result
        return wrapper
    return decorator

# Obtenir la clé API
XAI_API_KEY = os.environ.get("XAI_API_KEY")
if not XAI_API_KEY:
    logger.error("La clé API XAI n'est pas définie dans les variables d'environnement.")
    exit(1)
=======
if __name__ == "__main__":
    # Obtenir la clé API
    XAI_API_KEY = os.environ.get("XAI_API_KEY")
    if not XAI_API_KEY:
        logger.error("La clé API XAI n'est pas définie dans les variables d'environnement.")
        exit(1)
>>>>>>> a7d8894f88392812329555f9657008a79f629030

    # Créer le client xAI
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)

    # Définir un prompt simple pour tester
    prompt = "A professional portrait of a business woman with a modern background, suitable for a profile picture"

<<<<<<< HEAD
@timeout(20, "La génération d'image a pris trop de temps et a été interrompue")
def generate_image(client, prompt):
    logger.info(f"Début de la génération d'image xAI avec le prompt: {prompt}")
    response = client.images.generate(
        model="grok-2-image",
        prompt=prompt,
        n=1
        # Suppression du paramètre size qui n'est pas supporté par xAI
    )
    return response

try:
    # Génération avec timeout
    response = generate_image(client, prompt)
    
    # Vérifier la réponse
    if response.data and len(response.data) > 0:
        image_url = response.data[0].url
        logger.info(f"Image générée avec succès. URL: {image_url}")
        print(f"Image URL: {image_url}")
    else:
        logger.error("Pas de données d'image dans la réponse")
        print("Erreur: Pas de données d'image dans la réponse")
        
except TimeoutError as te:
    logger.error(f"Timeout: {te}")
    print(f"Timeout après 20 secondes: {te}")
        
except Exception as e:
    logger.error(f"Erreur lors de la génération d'image: {e}")
    print(f"Erreur: {e}")
=======
    try:
        # Générer l'image en utilisant l'API xAI
        logger.info(f"Début de la génération d'image xAI avec le prompt: {prompt}")
        response = client.images.generate(
            model="grok-2-image-1212",
            prompt=prompt,
            n=1
            # Suppression du paramètre size qui n'est pas supporté par xAI
        )
        
        # Vérifier la réponse
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            logger.info(f"Image générée avec succès. URL: {image_url}")
            print(f"Image URL: {image_url}")
        else:
            logger.error("Pas de données d'image dans la réponse")
            print("Erreur: Pas de données d'image dans la réponse")
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'image: {e}")
        print(f"Erreur: {e}")
>>>>>>> a7d8894f88392812329555f9657008a79f629030
