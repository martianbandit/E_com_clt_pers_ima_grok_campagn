import os
import logging
from openai import OpenAI

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Obtenir la clé API
XAI_API_KEY = os.environ.get("XAI_API_KEY")
if not XAI_API_KEY:
    logger.error("La clé API XAI n'est pas définie dans les variables d'environnement.")
    exit(1)

# Créer le client xAI
client = OpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)

# Définir un prompt simple pour tester
prompt = "A professional portrait of a business woman with a modern background, suitable for a profile picture"

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