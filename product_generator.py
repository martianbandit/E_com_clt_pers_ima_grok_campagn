"""
Module pour la génération de fiches produits optimisées pour le SEO et le marketing
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Optional, Union

# Configuration du client AI
from boutique_ai import AsyncOpenAI, GROK_3, grok_client

async def generate_product_description_async(
    client: AsyncOpenAI,
    product_info: Dict,
    target_audience: Dict,
    language: str = "fr",
    style: str = "descriptif",
    model: str = GROK_3
) -> Dict:
    """
    Génère une description de produit optimisée pour le SEO et le marketing
    
    Args:
        client: Client AsyncOpenAI
        product_info: Informations sur le produit (nom, catégorie, caractéristiques, etc.)
        target_audience: Données sur le public cible (persona)
        language: Code de langue (fr, en, etc.)
        style: Style de la description (descriptif, technique, émotionnel, etc.)
        model: Modèle Grok à utiliser
    
    Returns:
        Dict contenant la description, méta-title, méta-description et texte alternatif
    """
    try:
        # Construire le prompt pour la génération de contenu
        prompt = f"""
        Génère une fiche produit complète et optimisée pour le e-commerce en {language.upper()}.
        
        INFORMATIONS SUR LE PRODUIT:
        {json.dumps(product_info, indent=2, ensure_ascii=False)}
        
        CLIENT CIBLE:
        {json.dumps(target_audience, indent=2, ensure_ascii=False)}
        
        STYLE DE DESCRIPTION: {style}
        
        FORMAT DEMANDÉ (RESPECTER STRICTEMENT CE FORMAT JSON):
        {{
            "titre": "Titre accrocheur du produit (max 60 caractères)",
            "description_courte": "Résumé impactant en 1-2 phrases (max 160 caractères)",
            "description_complete": "Description détaillée du produit, structurée en plusieurs paragraphes",
            "points_forts": ["Liste des 3-5 points forts du produit"],
            "meta_title": "Titre SEO optimisé (max 60 caractères)",
            "meta_description": "Description SEO optimisée (max 160 caractères)", 
            "alt_text": "Texte alternatif pour l'image principale (max 125 caractères)",
            "mots_cles": ["Liste de 5-7 mots-clés pertinents pour le SEO"],
            "public_cible": "Description du public cible idéal pour ce produit"
        }}
        
        CONSIGNES IMPORTANTES:
        - Le contenu doit être UNIQUEMENT en {language.upper()}, adaptée au marché francophone
        - Utiliser un ton professionnel mais accessible, adapté au style {style}
        - Inclure des termes spécifiques à la niche et au produit
        - Rendre le contenu persuasif et orienté conversion
        - Respecter STRICTEMENT les limites de caractères indiquées
        """
        
        # Appeler l'API pour générer la description
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un expert en marketing de contenu e-commerce et SEO qui génère des fiches produits optimisées."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        # Extraire et traiter la réponse
        content = json.loads(response.choices[0].message.content)
        
        # Ajouter des informations complémentaires
        content["langue"] = language
        content["style_description"] = style
        
        return content
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération de la description produit: {e}")
        raise

async def generate_product_variants_async(
    client: AsyncOpenAI,
    base_product: Dict,
    variant_types: List[str],
    language: str = "fr",
    model: str = GROK_3
) -> Dict:
    """
    Génère des variantes pour un produit (tailles, couleurs, matériaux, etc.)
    
    Args:
        client: Client AsyncOpenAI
        base_product: Informations sur le produit de base
        variant_types: Types de variantes à générer (couleurs, tailles, etc.)
        language: Code de langue (fr, en, etc.)
        model: Modèle Grok à utiliser
    
    Returns:
        Dict contenant les variantes du produit
    """
    try:
        # Construire le prompt pour la génération de variantes
        prompt = f"""
        Génère des variantes réalistes pour ce produit en {language.upper()}.
        
        INFORMATIONS SUR LE PRODUIT DE BASE:
        {json.dumps(base_product, indent=2, ensure_ascii=False)}
        
        TYPES DE VARIANTES DEMANDÉES:
        {', '.join(variant_types)}
        
        FORMAT DEMANDÉ (RESPECTER STRICTEMENT CE FORMAT JSON):
        {{
            "variantes": [
                {{
                    "id": "identifiant-unique-variante-1",
                    "titre": "Titre de la variante 1",
                    "attributs": {{"type_attribut1": "valeur1", "type_attribut2": "valeur2"}},
                    "prix": "Prix spécifique à cette variante (ou vide si même prix)",
                    "disponibilite": "En stock / Rupture de stock / Sur commande",
                    "delai_livraison": "Délai estimé pour cette variante (si différent)"
                }}
            ],
            "grille_tailles": {{}},  // Si applicable, tableau des tailles disponibles
            "guide_couleurs": {{}},  // Si applicable, correspondance des couleurs
            "attributs_personnalisables": [] // Liste des attributs que le client peut personnaliser
        }}
        
        CONSIGNES:
        - Crée entre 3 et 8 variantes réalistes pour ce produit
        - Les variantes doivent respecter la logique du produit et de sa catégorie
        - Pour les vêtements, inclure une grille de tailles appropriée
        - Pour les produits avec couleurs, fournir des descriptions précises des teintes
        - Tous les attributs doivent être en {language.upper()}
        - Attribuer des prix cohérents si les variantes ont des prix différents
        """
        
        # Appeler l'API pour générer les variantes
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un expert en e-commerce spécialisé dans la création de variantes de produits optimisées pour les conversions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        # Extraire et traiter la réponse
        content = json.loads(response.choices[0].message.content)
        
        # Ajouter des métadonnées
        content["produit_base"] = base_product.get("nom", "Produit sans nom")
        content["types_variantes"] = variant_types
        content["nombre_variantes"] = len(content.get("variantes", []))
        
        return content
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération des variantes produit: {e}")
        raise

async def generate_product_comparison_async(
    client: AsyncOpenAI,
    product_info: Dict,
    competitors: List[Dict],
    language: str = "fr",
    model: str = GROK_3
) -> Dict:
    """
    Génère une analyse comparative du produit avec ses concurrents
    
    Args:
        client: Client AsyncOpenAI
        product_info: Informations sur le produit principal
        competitors: Liste des informations sur les produits concurrents
        language: Code de langue (fr, en, etc.)
        model: Modèle Grok à utiliser
    
    Returns:
        Dict contenant l'analyse comparative et les points forts/faibles
    """
    try:
        # Construire le prompt pour l'analyse comparative
        prompt = f"""
        Réalise une analyse comparative détaillée entre ce produit et ses concurrents en {language.upper()}.
        
        NOTRE PRODUIT:
        {json.dumps(product_info, indent=2, ensure_ascii=False)}
        
        PRODUITS CONCURRENTS:
        {json.dumps(competitors, indent=2, ensure_ascii=False)}
        
        FORMAT DEMANDÉ (RESPECTER STRICTEMENT CE FORMAT JSON):
        {{
            "tableau_comparatif": [
                {{
                    "critere": "Nom du critère de comparaison",
                    "notre_produit": "Performance de notre produit",
                    "concurrent_1": "Performance du concurrent 1",
                    "concurrent_2": "Performance du concurrent 2"
                }}
            ],
            "avantages_concurrentiels": [
                "Liste des 3-5 avantages majeurs de notre produit par rapport aux concurrents"
            ],
            "elements_amelioration": [
                "Points sur lesquels notre produit pourrait s'améliorer (1-3 points)"
            ],
            "argument_vente_unique": "Proposition de valeur unique du produit en une phrase",
            "recommandation_marketing": "Conseil stratégique pour mettre en avant ce produit"
        }}
        
        CONSIGNES:
        - Analyse objective des forces et faiblesses de chaque produit
        - Identification des avantages concurrentiels les plus significatifs
        - Entre 5 et 8 critères de comparaison pertinents pour cette catégorie de produit
        - Contenu UNIQUEMENT en {language.upper()}
        - Orienter l'analyse pour mettre en valeur notre produit de façon honnête
        """
        
        # Appeler l'API pour générer l'analyse
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse concurrentielle et positionnement marketing de produits e-commerce."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        # Extraire et traiter la réponse
        content = json.loads(response.choices[0].message.content)
        
        return content
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération de l'analyse comparative: {e}")
        raise

# Fonctions synchrones (wrappers) pour faciliter l'utilisation

def generate_product_description(
    product_info: Dict,
    target_audience: Dict,
    language: str = "fr",
    style: str = "descriptif"
) -> Dict:
    """Wrapper synchrone pour la génération de description produit"""
    return asyncio.run(generate_product_description_async(
        client=grok_client,
        product_info=product_info,
        target_audience=target_audience,
        language=language,
        style=style
    ))

def generate_product_variants(
    base_product: Dict,
    variant_types: List[str],
    language: str = "fr"
) -> Dict:
    """Wrapper synchrone pour la génération de variantes produit"""
    return asyncio.run(generate_product_variants_async(
        client=grok_client,
        base_product=base_product,
        variant_types=variant_types,
        language=language
    ))

def generate_product_comparison(
    product_info: Dict,
    competitors: List[Dict],
    language: str = "fr"
) -> Dict:
    """Wrapper synchrone pour la génération d'analyse comparative"""
    return asyncio.run(generate_product_comparison_async(
        client=grok_client,
        product_info=product_info,
        competitors=competitors,
        language=language
    ))