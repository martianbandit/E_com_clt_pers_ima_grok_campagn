import os
import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from trafilatura import fetch_url, extract

# Configuration
GROK_API_KEY = os.environ.get("XAI_API_KEY")
GROK_MODEL = "grok-3"  # Modèle le plus récent de xAI
ALIEXPRESS_BASE_URL = "https://www.aliexpress.com"
ALIEXPRESS_SEARCH_URL = f"{ALIEXPRESS_BASE_URL}/wholesale?SearchText="

logger = logging.getLogger(__name__)

# Client pour l'API xAI (Grok)
grok_client = AsyncOpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1"
)


async def web_search_with_grok(query: str, max_results: int = 5) -> List[Dict]:
    """
    Utilise Grok pour effectuer une recherche web et extraire des informations structurées.
    
    Args:
        query: Requête de recherche
        max_results: Nombre maximum de résultats à retourner
        
    Returns:
        Liste de produits trouvés avec leurs détails
    """
    try:
        # Formater la requête spécifiquement pour AliExpress
        search_query = f"Find {query} on AliExpress with best price and reviews"
        
        prompt = f"""
        Search the web for the following query:
        
        "{search_query}"
        
        Your task is to:
        1. Identify {max_results} highly relevant products on AliExpress matching the query
        2. Extract detailed information about each product
        3. Return a structured list of products with the following format:
        
        For each product, provide:
        - name: Full product name
        - description: Brief product description
        - price: Product price in USD (numeric value only, without currency symbol)
        - image_url: URL to the product image
        - product_url: Direct URL to the product on AliExpress
        - relevance_notes: Why this product might be relevant to the query
        
        Format your response as a JSON array of product objects.
        """
        
        response = await grok_client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": "You are a specialist in e-commerce and product search. You help find relevant products on AliExpress by searching the web and extracting structured information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Extraire les données JSON de la réponse
        result_text = response.choices[0].message.content
        
        # Tentative de conversion en JSON structuré (s'il n'est pas déjà formaté correctement)
        import json
        try:
            result_data = json.loads(result_text)
            if isinstance(result_data, dict) and "products" in result_data:
                products = result_data["products"]
            else:
                # Si le résultat est déjà une liste, l'utiliser directement
                products = result_data if isinstance(result_data, list) else []
        except Exception as e:
            logger.error(f"Error parsing product data: {e}")
            return []
        
        return products[:max_results]
        
    except Exception as e:
        logger.error(f"Error during web search with Grok: {e}")
        return []


async def find_similar_products(
    product_description: str, 
    campaign_id: int,
    niche: str = "", 
    max_results: int = 3
) -> List[Dict]:
    """
    Recherche des produits similaires sur AliExpress et les enregistre dans la base de données.
    
    Args:
        product_description: Description du produit à rechercher
        campaign_id: ID de la campagne associée
        niche: Créneau de marché pour affiner la recherche
        max_results: Nombre maximum de résultats à retourner
        
    Returns:
        Liste des produits similaires trouvés
    """
    from app import db
    from models import SimilarProduct
    
    try:
        # Construire une requête plus pertinente en combinant la description et le créneau
        search_query = f"{product_description} {niche}" if niche else product_description
        
        # Récupérer les produits similaires via Grok
        products = await web_search_with_grok(search_query, max_results)
        
        # Enregistrer les produits trouvés dans la base de données
        saved_products = []
        for product in products:
            similar_product = SimilarProduct(
                name=product.get("name", "Unknown Product"),
                description=product.get("description", ""),
                price=float(product.get("price", 0.0)) if product.get("price") else None,
                image_url=product.get("image_url", ""),
                product_url=product.get("product_url", ""),
                similarity_score=product.get("similarity_score", 0.8),  # Valeur par défaut
                relevance_notes=product.get("relevance_notes", ""),
                campaign_id=campaign_id
            )
            
            db.session.add(similar_product)
            saved_products.append(similar_product)
        
        # Sauvegarder les changements
        db.session.commit()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "image_url": p.image_url,
                "product_url": p.product_url,
                "similarity_score": p.similarity_score,
                "relevance_notes": p.relevance_notes
            }
            for p in saved_products
        ]
        
    except Exception as e:
        # En cas d'erreur, annuler la transaction
        db.session.rollback()
        logger.error(f"Error finding similar products: {e}")
        return []


def search_similar_products(product_description: str, campaign_id: int, niche: str = "", max_results: int = 3) -> List[Dict]:
    """
    Wrapper synchrone pour la fonction de recherche de produits similaires.
    """
    return asyncio.run(find_similar_products(product_description, campaign_id, niche, max_results))