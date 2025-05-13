"""
Utilitaires pour les appels API d'IA avec gestion robuste des erreurs
et journalisation des métriques
"""
import json
import time
import logging
import traceback
from typing import Dict, Any, Optional, Union, Callable
from functools import wraps

# Gestion des importations des clients AI
try:
    from openai import OpenAI
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = object  # Type fictif
    AsyncOpenAI = object  # Type fictif
    OPENAI_AVAILABLE = False

# Implémenter notre propre version de log_metric pour éviter une dépendance circulaire
def log_metric(metric_name, data, category=None, status=None, response_time=None, customer_id=None):
    """
    Version simplifiée de log_metric pour éviter les références circulaires.
    Cette version enregistre simplement les métriques dans les logs.
    
    Args:
        metric_name: Nom de la métrique
        data: Données à enregistrer (dictionnaire)
        category: Catégorie de la métrique (ai, user, system, etc.)
        status: État (success, error, warning, info)
        response_time: Temps de réponse en ms (pour les appels API)
        customer_id: ID du client associé (si pertinent)
    """
    try:
        # Extraire automatiquement le statut des données si non spécifié
        if status is None and isinstance(data, dict) and 'success' in data:
            status = True if data['success'] else False
        elif status == 'success':
            status = True
        elif status == 'error':
            status = False
        
        # Extraire automatiquement la catégorie si non spécifiée
        if category is None:
            # Détection basée sur le nom de la métrique
            if 'ai_' in metric_name or 'grok_' in metric_name or 'openai_' in metric_name:
                category = 'ai'
            elif 'user_' in metric_name:
                category = 'user'
            elif 'system_' in metric_name:
                category = 'system'
            elif 'generation' in metric_name:
                category = 'generation'
            elif 'import' in metric_name:
                category = 'import'
            else:
                category = 'misc'
                
        # Journal des métriques importantes ou des erreurs uniquement
        if status is False:
            logging.error(f"Metric Error: {metric_name} - {json.dumps(data)}")
        else:
            logging.info(f"Metric: {metric_name} ({category}) - Status: {status}")
            
    except Exception as e:
        logging.error(f"Failed to log metric {metric_name}: {e}")

# Constantes pour les modèles
GROK_MODEL = "grok-2-1212"
GROK_VISION_MODEL = "grok-2-vision-1212"
OPENAI_MODEL = "gpt-4o"
DALL_E_MODEL = "dall-e-3"
GROK_IMAGE_MODEL = "grok-2-vision-1212"  # Modèle Grok pour les images

def with_ai_error_handling(func):
    """
    Décorateur pour gérer de manière robuste les erreurs des appels API d'IA
    
    Ce décorateur:
    1. Mesure le temps d'exécution
    2. Gère les exceptions de manière robuste
    3. Enregistre les métriques de performance et d'erreur
    
    Args:
        func: Fonction à décorer (doit avoir un paramètre 'metric_name')
        
    Returns:
        Fonction décorée avec gestion d'erreurs
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        metric_name = kwargs.get('metric_name', f"ai_call_{func.__name__}")
        start_time = time.time()
        result = None
        error = None
        status = 'success'
        
        try:
            # Exécuter la fonction
            result = func(*args, **kwargs)
            
            # Vérifier si le résultat est None alors qu'il ne devrait pas l'être
            if result is None and not kwargs.get('allow_none', False):
                error = "API returned None"
                status = 'error'
                
            return result
            
        except Exception as e:
            error = str(e)
            error_type = type(e).__name__
            status = 'error'
            stack_trace = traceback.format_exc()
            
            # Logger l'erreur
            logging.error(f"AI API Error in {func.__name__}: {error_type} - {error}")
            logging.debug(f"Stack trace: {stack_trace}")
            
            # Retourner une valeur par défaut ou ré-lever l'exception
            if not kwargs.get('raise_exceptions', True):
                fallback_result = kwargs.get('fallback_result', None)
                logging.info(f"Using fallback result: {fallback_result}")
                return fallback_result
            raise
            
        finally:
            # Calculer le temps d'exécution
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # en ms
            
            # Construire les données de métrique
            metric_data = {
                'success': status == 'success',
                'function': func.__name__,
                'response_time_ms': response_time
            }
            
            # Ajouter les détails d'erreur si applicable
            if error:
                metric_data['error'] = error
                metric_data['error_type'] = error_type if 'error_type' in locals() else 'Unknown'
            
            # Ajouter des informations spécifiques aux paramètres
            if 'prompt' in kwargs:
                # Tronquer le prompt pour la métrique
                prompt = kwargs['prompt']
                metric_data['prompt_length'] = len(prompt) if isinstance(prompt, str) else "non-string"
                metric_data['prompt_preview'] = prompt[:100] + "..." if isinstance(prompt, str) and len(prompt) > 100 else prompt
                
            # Ajouter des métriques spécifiques au modèle
            if 'model' in kwargs:
                metric_data['model'] = kwargs['model']
                
            # Enregistrer la métrique
            try:
                log_metric(
                    metric_name=metric_name,
                    data=metric_data,
                    category='ai',
                    status=status,
                    response_time=response_time,
                    customer_id=kwargs.get('customer_id')
                )
            except Exception as log_error:
                logging.error(f"Failed to log AI metric: {log_error}")
    
    return wrapper


class AIManager:
    """
    Gestionnaire pour les appels aux différentes API d'IA avec fallback
    et mesure de performances
    """
    
    def __init__(self, openai_api_key=None, xai_api_key=None):
        self.openai_client = None
        self.grok_client = None
        self._init_clients(openai_api_key, xai_api_key)
        
    def _init_clients(self, openai_api_key=None, xai_api_key=None):
        """Initialise les clients API si les clés sont disponibles"""
        if OPENAI_AVAILABLE:
            if openai_api_key:
                self.openai_client = OpenAI(api_key=openai_api_key)
                logging.info("OpenAI client initialized")
            if xai_api_key:
                self.grok_client = OpenAI(base_url="https://api.x.ai/v1", api_key=xai_api_key)
                logging.info("xAI (Grok) client initialized")
    
    @with_ai_error_handling
    def generate_text(self, 
                    prompt: str, 
                    model: str = GROK_MODEL,
                    max_tokens: int = 500,
                    temperature: float = 0.7,
                    use_fallback: bool = True,
                    metric_name: str = "ai_text_generation",
                    **kwargs) -> str:
        """
        Génère du texte avec le modèle spécifié, avec fallback automatique
        
        Args:
            prompt: Texte de prompt pour l'IA
            model: Modèle à utiliser (GROK_MODEL ou OPENAI_MODEL par défaut)
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (créativité) de la génération
            use_fallback: Utiliser OpenAI comme fallback si Grok échoue
            metric_name: Nom de la métrique à enregistrer
            **kwargs: Arguments supplémentaires
            
        Returns:
            Texte généré ou message d'erreur si les deux APIs échouent
        """
        # Choix du client en fonction du modèle
        is_grok = GROK_MODEL in model
        
        # Paramètres communs pour les deux APIs
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Si le format JSON est requis
        if kwargs.get('json_format', False):
            params["response_format"] = {"type": "json_object"}
        
        # Tentative avec le client principal
        client = self.grok_client if is_grok else self.openai_client
        if client:
            try:
                response = client.chat.completions.create(**params)
                return response.choices[0].message.content
            except Exception as e:
                logging.error(f"Primary AI API error ({model}): {e}")
                if not use_fallback:
                    raise
        elif not use_fallback:
            return "Error: Primary AI client not initialized"
            
        # Fallback vers l'autre client si disponible
        fallback_client = self.openai_client if is_grok else self.grok_client
        fallback_model = OPENAI_MODEL if is_grok else GROK_MODEL
        
        if fallback_client:
            try:
                logging.info(f"Using fallback model {fallback_model}")
                params["model"] = fallback_model
                response = fallback_client.chat.completions.create(**params)
                return response.choices[0].message.content
            except Exception as e:
                logging.error(f"Fallback AI API error ({fallback_model}): {e}")
                raise
        
        return "Error: No AI clients available"
    
    @with_ai_error_handling
    def generate_json(self, 
                     prompt: str,
                     model: str = GROK_MODEL,
                     schema: Dict = None,
                     max_tokens: int = 1000,
                     metric_name: str = "ai_json_generation",
                     **kwargs) -> Dict:
        """
        Génère une réponse au format JSON structuré
        
        Args:
            prompt: Texte de prompt pour l'IA
            model: Modèle à utiliser
            schema: Schéma JSON attendu (optionnel)
            max_tokens: Nombre maximum de tokens
            metric_name: Nom de la métrique à enregistrer
            **kwargs: Arguments supplémentaires
            
        Returns:
            Dictionnaire contenant la réponse JSON
        """
        # Ajouter des instructions sur le format JSON
        system_message = "Output must be formatted as valid JSON. "
        
        if schema:
            system_message += f"Use the following JSON schema: {json.dumps(schema)}"
        
        # Générer le texte avec format JSON activé
        json_text = self.generate_text(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            json_format=True,
            system_message=system_message,
            metric_name=metric_name,
            **kwargs
        )
        
        # Parsing du JSON
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}. Response: {json_text}")
            # Tentative de nettoyage et re-parsing
            cleaned_text = json_text.strip()
            # Trouver le début et la fin du JSON si entouré de texte
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}') + 1
            if start >= 0 and end > start:
                cleaned_text = cleaned_text[start:end]
                try:
                    return json.loads(cleaned_text)
                except:
                    pass
            raise
    
    @with_ai_error_handling
    def generate_image(self,
                      prompt: str,
                      model: str = GROK_IMAGE_MODEL,
                      size: str = "1024x1024",
                      metric_name: str = "ai_image_generation",
                      use_fallback: bool = True,
                      **kwargs) -> str:
        """
        Génère une image en utilisant l'API d'images de xAI (Grok) ou OpenAI
        
        Args:
            prompt: Description textuelle de l'image à générer
            model: Modèle d'image à utiliser (GROK_IMAGE_MODEL ou DALL_E_MODEL)
            size: Taille de l'image (1024x1024 par défaut)
            metric_name: Nom de la métrique à enregistrer
            use_fallback: Si True, utilise OpenAI comme fallback si Grok échoue
            **kwargs: Arguments supplémentaires
            
        Returns:
            URL de l'image générée
        """
        # Détermine le client à utiliser en fonction du modèle
        is_grok_model = model in [GROK_IMAGE_MODEL, GROK_VISION_MODEL, "grok-2-vision-1212", "grok-vision-beta"]
        
        # Préparer les paramètres communs
        params = {
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        
        # Nettoyer et préparer le prompt selon les exigences des différents modèles
        if len(prompt) > 1000:
            logging.warning(f"Prompt too long ({len(prompt)} chars). Truncating.")
            params["prompt"] = prompt[:1000]
        
        # Tentative avec le client principal
        primary_client = self.grok_client if is_grok_model else self.openai_client
        primary_model = model if is_grok_model else DALL_E_MODEL
        
        if primary_client:
            try:
                logging.info(f"Generating image with {primary_model}")
                
                # Si c'est un modèle Grok, utiliser la vision API  
                if is_grok_model:
                    # Pour les modèles Grok, nous utilisons l'API de chat avec entrée texte et sortie image
                    chat_response = primary_client.chat.completions.create(
                        model=primary_model,
                        messages=[
                            {
                                "role": "user", 
                                "content": [
                                    {"type": "text", "text": f"Generate an image based on this description: {prompt}"}
                                ]
                            }
                        ],
                        max_tokens=1000
                    )
                    
                    # Vérifier si la réponse contient une URL d'image valide
                    if hasattr(chat_response.choices[0].message, 'content'):
                        # Extraire l'URL de l'image générée - pourrait nécessiter un parsing
                        content = chat_response.choices[0].message.content
                        # Vérifier si le contenu est une URL d'image
                        if content and (content.startswith('http://') or content.startswith('https://')):
                            return content
                        else:
                            logging.warning(f"Grok didn't return a valid image URL: {content[:100]}...")
                            if not use_fallback:
                                raise ValueError(f"Invalid image URL from Grok: {content[:100]}...")
                    else:
                        logging.warning("Grok didn't return valid content.")
                        if not use_fallback:
                            raise ValueError("No valid content returned from Grok.")
                else:
                    # Pour OpenAI, utiliser l'API d'images standard
                    response = primary_client.images.generate(
                        model=primary_model,
                        prompt=params["prompt"],
                        n=params["n"],
                        size=params["size"],
                        **kwargs
                    )
                    if response.data and len(response.data) > 0 and hasattr(response.data[0], 'url'):
                        return response.data[0].url
                    else:
                        logging.warning("OpenAI didn't return a valid image URL.")
                        if not use_fallback:
                            raise ValueError("No valid URL returned from OpenAI.")
            except Exception as e:
                logging.error(f"Primary image generation error ({primary_model}): {e}")
                if not use_fallback:
                    raise
                    
        # Fallback vers l'autre client si disponible
        if use_fallback:
            fallback_client = self.openai_client if is_grok_model else self.grok_client
            fallback_model = DALL_E_MODEL if is_grok_model else GROK_IMAGE_MODEL
            
            if fallback_client:
                try:
                    logging.info(f"Using fallback model {fallback_model}")
                    
                    # Si c'est un fallback vers Grok
                    if fallback_model in [GROK_IMAGE_MODEL, GROK_VISION_MODEL]:
                        chat_response = fallback_client.chat.completions.create(
                            model=fallback_model,
                            messages=[
                                {
                                    "role": "user", 
                                    "content": [
                                        {"type": "text", "text": f"Generate an image based on this description: {prompt}"}
                                    ]
                                }
                            ],
                            max_tokens=1000
                        )
                        
                        if hasattr(chat_response.choices[0].message, 'content'):
                            content = chat_response.choices[0].message.content
                            if content and (content.startswith('http://') or content.startswith('https://')):
                                return content
                    else:
                        # Fallback vers OpenAI
                        response = fallback_client.images.generate(
                            model=fallback_model,
                            prompt=params["prompt"],
                            n=params["n"],
                            size=params["size"],
                            **kwargs
                        )
                        if response.data and len(response.data) > 0 and hasattr(response.data[0], 'url'):
                            return response.data[0].url
                except Exception as e:
                    logging.error(f"Fallback image generation error ({fallback_model}): {e}")
                    raise
        
        # Si on arrive ici, c'est que ni le client principal ni le fallback n'ont fonctionné
        raise ValueError("Failed to generate image with both primary and fallback models.")
            
    def extract_json_safely(self, text):
        """Extrait proprement un objet JSON d'un texte, même s'il est entouré d'autres contenus"""
        try:
            # Si c'est déjà un JSON valide
            return json.loads(text)
        except:
            pass
            
        # Chercher les accolades de début et de fin
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
                
        # Essayer d'extraire avec une regex plus robuste
        import re
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
                
        # Si toutes les tentatives échouent
        raise ValueError(f"Unable to extract valid JSON from text: {text[:100]}...")