"""
Module pour la génération de contenu de produit optimisé avec AI
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Any

from boutique_ai import grok_client, GROK_3

async def generate_product_content(
    product_data: Dict[str, Any],
    target_audience: Optional[Dict[str, Any]] = None,
    generate_options: Optional[Dict[str, bool]] = None,
    instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Génère du contenu optimisé pour un produit
    
    Args:
        product_data: Données du produit
        target_audience: Données du persona client cible (optionnel)
        generate_options: Options de génération
        instructions: Instructions spécifiques pour la génération
        
    Returns:
        Dictionnaire contenant le contenu généré
    """
    # Options par défaut
    options = {
        "generate_description": True,
        "generate_meta": True,
        "generate_variants": True,
        "generate_comparative": False
    }
    
    # Fusionner avec les options fournies
    if generate_options:
        options.update(generate_options)
    
    # Construire le contexte
    context = {
        "product": product_data,
        "target_audience": target_audience,
        "options": options,
        "instructions": instructions
    }
    
    # Générer le prompt
    prompt = _build_product_content_prompt(context)
    
    try:
        # Appeler l'API
        response = await grok_client.chat.completions.create(
            model=GROK_3,
            messages=[
                {"role": "system", "content": "Tu es un expert en copywriting, e-commerce et SEO spécialisé dans la création de fiches produits optimisées."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=3000
        )
        
        # Extraire la réponse
        content = json.loads(response.choices[0].message.content)
        
        # Ajouter des métadonnées
        content["generation_timestamp"] = datetime.datetime.now().isoformat()
        
        return content
    
    except Exception as e:
        logging.error(f"Erreur lors de la génération du contenu produit: {e}")
        raise

def _build_product_content_prompt(context: Dict[str, Any]) -> str:
    """
    Construit le prompt pour la génération de contenu produit
    
    Args:
        context: Contexte pour la génération
        
    Returns:
        Prompt formaté
    """
    product = context["product"]
    target_audience = context.get("target_audience")
    options = context.get("options", {})
    instructions = context.get("instructions", "")
    
    # Construire le prompt principal
    prompt = f"""
    Je dois créer du contenu optimisé pour ce produit:
    
    PRODUIT:
    - Nom: {product.get('name', '')}
    - Catégorie: {product.get('category', '')}
    - Prix: {product.get('price', '0')}€
    - Description actuelle: {product.get('base_description', '')}
    """
    
    # Ajouter des informations sur l'audience cible si disponible
    if target_audience:
        prompt += f"""
        
        PUBLIC CIBLE:
        - Nom: {target_audience.get('name', '')}
        - Âge: {target_audience.get('age', '')}
        - Localisation: {target_audience.get('location', '')}
        - Genre: {target_audience.get('gender', '')}
        - Intérêts: {', '.join(target_audience.get('interests', []))}
        - Persona: {target_audience.get('persona', '')}
        """
    
    # Ajouter des instructions spécifiques
    if instructions:
        prompt += f"""
        
        INSTRUCTIONS SPÉCIFIQUES:
        {instructions}
        """
    
    # Spécifier les éléments à générer
    prompt += """
    
    ÉLÉMENTS À GÉNÉRER:
    """
    
    if options.get("generate_description", True):
        prompt += """
        1. DESCRIPTION OPTIMISÉE:
           - Un titre optimisé SEO et marketing pour le produit (max 100 caractères)
           - Une description détaillée et persuasive qui met en valeur les avantages et caractéristiques principales
           - Le texte doit être optimisé pour le référencement et la conversion
        """
    
    if options.get("generate_meta", True):
        prompt += """
        2. MÉTADONNÉES SEO:
           - Meta title (60 caractères max)
           - Meta description (160 caractères max)
           - Alt text pour l'image principale (125 caractères max)
           - 5-8 mots-clés/tags pertinents
        """
    
    if options.get("generate_variants", True):
        prompt += """
        3. VARIANTES DU PRODUIT:
           - Suggestions de 3-5 variantes potentielles (couleurs, tailles, matériaux, etc.)
           - Description courte pour chaque variante
        """
    
    if options.get("generate_comparative", False):
        prompt += """
        4. ANALYSE COMPARATIVE:
           - Positionnement par rapport à la concurrence
           - 3-5 points forts par rapport aux produits similaires
           - Arguments de vente uniques
        """
    
    # Format de sortie demandé
    prompt += """
    
    Réponds strictement au format JSON suivant:
    {
        "generated_title": "Titre optimisé du produit",
        "generated_description": "Description détaillée et optimisée",
        "meta_title": "Meta title SEO",
        "meta_description": "Meta description SEO",
        "alt_text": "Texte alternatif pour l'image principale",
        "keywords": ["mot-clé1", "mot-clé2", ...],
    """
    
    if options.get("generate_variants", True):
        prompt += """
        "variants": [
            {"name": "Nom de la variante", "description": "Description courte"},
            ...
        ],
    """
    
    if options.get("generate_comparative", False):
        prompt += """
        "comparative_analysis": {
            "positioning": "Positionnement marché",
            "strengths": ["Point fort 1", "Point fort 2", ...],
            "unique_selling_points": ["Argument unique 1", "Argument unique 2", ...]
        },
    """
    
    prompt += """
        "optimization_notes": "Notes sur l'optimisation effectuée"
    }
    """
    
    return prompt

async def generate_product_html_templates(
    product_data: Dict[str, Any],
    target_market: str = "moyenne_gamme"
) -> Dict[str, str]:
    """
    Génère des templates HTML optimisés pour Shopify
    
    Args:
        product_data: Données du produit
        target_market: Marché cible (entrée_gamme, moyenne_gamme, haut_de_gamme, luxe)
        
    Returns:
        Dictionnaire contenant les templates HTML générés
    """
    try:
        # Construire le contexte
        context = {
            "product": product_data,
            "target_market": target_market
        }
        
        prompt = f"""
        Je dois créer du contenu HTML optimisé pour Shopify à partir de ces données de produit:
        
        {json.dumps(context, indent=2, ensure_ascii=False)}
        
        Génère un template HTML complet pour Shopify avec les sections suivantes:
        
        1. Un bloc HTML principal de description produit avec:
           - Titre H1 optimisé pour le SEO
           - Description enrichie avec des éléments de mise en valeur
           - Liste des caractéristiques principales dans un format attrayant
           - Appels à l'action persuasifs
           - Mise en forme professionnelle avec CSS intégré
         
        2. Un bloc HTML séparé optimisé pour les spécifications techniques
        
        3. Un bloc HTML supplémentaire pour la section FAQ du produit (génère des questions/réponses pertinentes)
        
        Respecte ces consignes:
        - Utilise seulement des éléments HTML valides et compatibles avec l'éditeur Shopify
        - Inclus les classes CSS nécessaires pour un bon rendu
        - Optimise le contenu pour le SEO et la conversion
        - Ajoute des microdonnées schema.org pour le référencement
        - Utilise des éléments HTML5 sémantiques (section, article, etc.)
        
        Fournis UNIQUEMENT le résultat au format JSON suivant:
        {
            "html_description": "HTML complet pour la description principale",
            "html_specifications": "HTML pour les spécifications techniques",
            "html_faq": "HTML pour la section FAQ"
        }
        """
        
        # Appeler l'API pour générer le contenu
        response = await grok_client.chat.completions.create(
            model=GROK_3,
            messages=[
                {"role": "system", "content": "Tu es un expert en optimisation e-commerce pour Shopify avec une expertise en HTML, CSS et SEO."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        # Extraire et retourner le contenu généré
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération des templates HTML: {e}")
        raise