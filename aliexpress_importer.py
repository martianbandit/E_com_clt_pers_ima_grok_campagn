"""
Module pour extraire et traiter les données de produits AliExpress
"""

import re
import json
import logging
import asyncio
import urllib.parse
import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
import random
import trafilatura
from urllib.parse import urlparse, parse_qs

# Configuration du client AI
from boutique_ai import AsyncOpenAI, GROK_3, grok_client

# Pattern pour extraire l'ID du produit AliExpress
ALIEXPRESS_ID_PATTERN = r'/item/(\d+)\.html'
ALIEXPRESS_ITEM_API_URL = "https://www.aliexpress.com/item/{item_id}.html"

logger = logging.getLogger(__name__)

async def extract_aliexpress_product_data(url: str) -> Dict:
    """
    Extrait les données d'un produit AliExpress à partir de l'URL
    
    Args:
        url: URL du produit AliExpress
        
    Returns:
        Dictionnaire contenant les données du produit
    """
    try:
        # Extraire l'ID du produit à partir de l'URL
        match = re.search(ALIEXPRESS_ID_PATTERN, url)
        if not match:
            raise ValueError(f"Format d'URL AliExpress non valide: {url}")
        
        item_id = match.group(1)
        
        # Télécharger le contenu HTML
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"Impossible de télécharger la page: {url}")
        
        # Extraction du texte principal et du contenu HTML
        main_text = trafilatura.extract(downloaded)
        
        # Utiliser Grok pour extraire les informations structurées
        prompt = f"""
        J'ai besoin d'extraire des informations structurées à partir de cette page produit AliExpress. 
        Voici le contenu de la page:
        
        {main_text[:5000]}... (contenu tronqué)
        
        Extrais les informations suivantes de manière précise et complète. Réponds strictement au format JSON suivant:
        {{
            "titre": "titre complet du produit",
            "prix": "prix principal affiché (juste le nombre)",
            "devise": "EUR/USD/etc.",
            "description": "description principale du produit",
            "caracteristiques": ["liste des caractéristiques principales"],
            "variantes": ["liste des variantes disponibles (couleurs, tailles, etc.)"],
            "images_urls": ["liste des URLs d'images principales si détectées"],
            "note_moyenne": "note moyenne sur 5 si disponible",
            "nombre_commandes": "nombre de commandes/ventes si disponible",
            "id_produit": "{item_id}",
            "url_source": "{url}"
        }}
        
        Si une information n'est pas trouvée, utilise une chaîne vide ou un tableau vide selon le format attendu.
        """
        
        # Appeler l'API pour extraire les informations
        response = await grok_client.chat.completions.create(
            model=GROK_3,
            messages=[
                {"role": "system", "content": "Tu es un assistant expert en extraction de données e-commerce à partir de pages web."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        # Extraire et traiter la réponse
        product_data = json.loads(response.choices[0].message.content)
        
        # Ajouter des informations supplémentaires pour le traitement
        product_data["source"] = "aliexpress"
        product_data["item_id"] = item_id
        
        return product_data
        
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction des données AliExpress: {e}")
        raise

async def optimize_pricing_strategy(product_data: Dict, target_market: str = "moyenne_gamme") -> Dict:
    """
    Optimise la stratégie de prix pour un produit importé
    
    Args:
        product_data: Données du produit
        target_market: Marché cible (entrée_gamme, moyenne_gamme, haut_de_gamme, luxe)
        
    Returns:
        Dictionnaire contenant la stratégie de prix optimisée
    """
    try:
        # Extraire le prix de base
        base_price = 0
        try:
            if isinstance(product_data.get("prix"), str):
                # Nettoyer le prix (supprimer les symboles de devise et convertir en float)
                base_price = float(re.sub(r'[^\d.,]', '', product_data.get("prix", "0").replace(',', '.')))
            else:
                base_price = float(product_data.get("prix", 0))
        except (ValueError, TypeError):
            base_price = 0
        
        # Coefficients par marché cible
        markup_coefficients = {
            "entrée_gamme": 1.5,  # +50%
            "moyenne_gamme": 2.0,  # +100%
            "haut_de_gamme": 2.5,  # +150%
            "luxe": 3.5  # +250%
        }
        
        # Appliquer le coefficient de base
        coefficient = markup_coefficients.get(target_market, 2.0)
        
        # Facteurs de correction
        popularity_factor = 1.0
        if product_data.get("nombre_commandes"):
            try:
                orders = int(re.sub(r'[^\d]', '', str(product_data.get("nombre_commandes", "0"))))
                if orders > 1000:
                    popularity_factor = 1.1  # Produits populaires +10%
                elif orders > 5000:
                    popularity_factor = 1.15  # Produits très populaires +15%
            except (ValueError, TypeError):
                pass
        
        rating_factor = 1.0
        if product_data.get("note_moyenne"):
            try:
                rating = float(str(product_data.get("note_moyenne", "0")).replace(',', '.'))
                if rating >= 4.8:
                    rating_factor = 1.1  # Produits très bien notés +10%
                elif rating >= 4.5:
                    rating_factor = 1.05  # Produits bien notés +5%
            except (ValueError, TypeError):
                pass
        
        # Calcul du prix optimisé
        optimal_price = base_price * coefficient * popularity_factor * rating_factor
        
        # Arrondir à un prix psychologique
        def psychological_rounding(price):
            # Arrondir aux .99 ou .95
            if price < 50:
                return int(price) - 0.01
            elif price < 100:
                return int(price) - 0.05
            else:
                return int(price / 10) * 10 - 0.01
        
        psychological_price = psychological_rounding(optimal_price)
        
        # Calculer les potentielles promos
        promo_percent = random.choice([0, 5, 10, 15, 20]) if random.random() < 0.7 else 0
        promo_price = round(psychological_price * (1 - promo_percent/100), 2)
        
        # Générer différentes stratégies de prix
        return {
            "base_price": base_price,
            "optimal_price": round(optimal_price, 2),
            "psychological_price": psychological_price,
            "promo_percent": promo_percent,
            "promo_price": promo_price,
            "market_segment": target_market,
            "profit_margin": round((psychological_price - base_price) / psychological_price * 100, 2),
            "price_factors": {
                "base_coefficient": coefficient,
                "popularity_factor": popularity_factor,
                "rating_factor": rating_factor
            },
            "price_recommendations": [
                {"name": "Prix compétitif", "price": round(optimal_price * 0.9, 2)},
                {"name": "Prix standard", "price": round(optimal_price, 2)},
                {"name": "Prix premium", "price": round(optimal_price * 1.1, 2)}
            ]
        }
    
    except Exception as e:
        logging.error(f"Erreur lors de l'optimisation de la stratégie de prix: {e}")
        # Retourner une stratégie de prix par défaut en cas d'erreur
        default_price = 29.99  # Prix par défaut si la base_price n'est pas disponible
        try:
            # Essayer d'utiliser base_price s'il est défini
            price_base = base_price
        except NameError:
            # Sinon utiliser le prix par défaut
            price_base = default_price
            
        return {
            "original_price": price_base,
            "optimal_price": price_base * 2,
            "psychological_price": price_base * 2,
            "promo_percent": 0,
            "promo_price": price_base * 2,
            "market_segment": target_market,
            "profit_margin": 50,
            "price_factors": {
                "base_coefficient": 2.0,
                "popularity_factor": 1.0,
                "rating_factor": 1.0
            },
            "price_recommendations": [
                {"name": "Prix compétitif", "price": price_base * 1.8},
                {"name": "Prix standard", "price": price_base * 2},
                {"name": "Prix premium", "price": price_base * 2.2}
            ]
        }

async def generate_shopify_html_template(product_data: Dict, pricing_data: Dict) -> Dict:
    """
    Génère un modèle HTML optimisé pour Shopify à partir des données du produit
    
    Args:
        product_data: Données du produit
        pricing_data: Stratégie de prix optimisée
        
    Returns:
        Dictionnaire contenant le code HTML et les métadonnées
    """
    try:
        # Préparer le contexte pour la génération
        context = {
            "product": product_data,
            "pricing": pricing_data
        }
        
        prompt = f"""
        Je dois créer du contenu HTML optimisé pour une boutique Shopify à partir de ces données de produit AliExpress:
        
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
        
        4. Les méta-données optimisées:
           - Meta title (60 caractères max)
           - Meta description (160 caractères max)
           - Alt text pour l'image principale (125 caractères max)
           - Balises/tags pour le produit (5-7 balises pertinentes)
        
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
            "html_faq": "HTML pour la section FAQ",
            "meta_title": "Meta title optimisé",
            "meta_description": "Meta description optimisée",
            "alt_text": "Texte alternatif pour l'image principale",
            "tags": ["liste", "des", "balises", "recommandées"]
        }
        """
        
        # Appeler l'API pour générer le contenu
        response = await grok_client.chat.completions.create(
            model=GROK_3,
            messages=[
                {"role": "system", "content": "Tu es un expert en optimisation e-commerce pour Shopify avec une expertise en SEO, HTML et conversion."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        # Extraire et retourner le contenu généré
        result = json.loads(response.choices[0].message.content)
        
        # Ajouter des informations sur la source et le produit
        result["product_id"] = product_data.get("id_produit")
        result["product_url"] = product_data.get("url_source")
        result["generated_date"] = str(datetime.datetime.now())
        
        return result
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération du template HTML: {e}")
        raise

def extract_aliexpress_product_id(url: str) -> Optional[str]:
    """
    Extrait l'ID du produit à partir d'une URL AliExpress
    
    Args:
        url: URL du produit AliExpress
        
    Returns:
        ID du produit ou None si non trouvé
    """
    if not url:
        return None
        
    # Ajout de log pour le débogage
    logger.info(f"Tentative d'extraction de l'ID du produit depuis l'URL: {url}")
    
    # Essayer plusieurs patterns pour plus de robustesse
    patterns = [
        r'/item/(\d+)\.html',
        r'item_id=(\d+)',
        r'_(\d+)\.html',
        r'/(\d+)\.html',
        r'aliexpress\.com/.*?/(\d+)',
        r'product/(\d+)',
        r'/(\d+)(?:\?|$)',
        r'id=(\d+)',
        r'p_(\d+)',
        r'product_id=(\d+)',
        r'a\.aliexpress\.com/_m([a-zA-Z0-9]+)', # Format d'URL courte a.aliexpress.com/_mXXXXXX
        r'item/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            product_id = match.group(1)
            logger.info(f"ID de produit extrait avec pattern {pattern}: {product_id}")
            return product_id
    
    # Essayer d'extraire à partir des paramètres d'URL
    try:
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        
        # Vérifier les paramètres communs pour l'ID
        param_keys = ['item_id', 'itemId', 'productId', 'id', 'product_id', 'pid', 'skuId']
        for key in param_keys:
            if key in params and params[key]:
                product_id = params[key][0]
                logger.info(f"ID de produit extrait du paramètre {key}: {product_id}")
                return product_id
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des paramètres d'URL: {e}")
    
    # Si nous n'avons pas pu extraire l'ID, notifier le problème
    logger.warning(f"Impossible d'extraire l'ID du produit depuis l'URL: {url}")
    return None

# Fonctions synchrones (wrappers) pour faciliter l'utilisation
def import_aliexpress_product(url: str, target_market: str = "moyenne_gamme") -> Dict:
    """
    Importe et optimise un produit AliExpress à partir de son URL
    
    Args:
        url: URL du produit AliExpress
        target_market: Marché cible pour la stratégie de prix
        
    Returns:
        Dictionnaire contenant toutes les données optimisées du produit
    """
    async def process_import():
        product_data = await extract_aliexpress_product_data(url)
        pricing_data = await optimize_pricing_strategy(product_data, target_market)
        template_data = await generate_shopify_html_template(product_data, pricing_data)
        
        # Combinaison des résultats
        return {
            "product": product_data,
            "pricing": pricing_data,
            "template": template_data
        }
    
    return asyncio.run(process_import())


class AliExpressProductManager:
    """
    Classe agissant comme un product manager pour analyser des produits AliExpress et
    générer des fiches produits optimisées avec recommandations marketing.
    """
    
    def __init__(self):
        """Initialise le product manager"""
        self.client = grok_client
        self.model = GROK_3
        
    async def analyze_product_url(self, url: str) -> Dict[str, Any]:
        """
        Analyse complète d'un produit AliExpress à partir de son URL.
        Agit comme un product manager complet qui fournit une analyse approfondie.
        
        Args:
            url: URL du produit AliExpress
            
        Returns:
            Dict contenant l'analyse complète
        """
        logger.info(f"Démarrage de l'analyse du produit: {url}")
        
        try:
            # 1. Extraire l'ID du produit
            product_id = extract_aliexpress_product_id(url)
            if not product_id:
                raise ValueError(f"Format d'URL AliExpress invalide: {url}")
                
            # 2. Extraire les données brutes avec trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                raise ValueError(f"Impossible de télécharger la page produit: {url}")
                
            main_text = trafilatura.extract(downloaded)
            
            # 3. Demander à Grok d'agir comme un product manager et de faire une analyse complète
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """Tu es un product manager expert en e-commerce qui analyse des produits 
                     AliExpress pour les transformer en fiches produits optimisées pour la revente. Tu fournis des insights 
                     stratégiques et marketing, tu identifies les forces et faiblesses du produit, et tu recommandes 
                     des optimisations."""},
                    {"role": "user", "content": self._build_product_manager_prompt(url, product_id, main_text)}
                ],
                response_format={"type": "json_object"},
                max_tokens=4000
            )
            
            # 4. Extraire et traiter l'analyse
            analysis = json.loads(response.choices[0].message.content)
            
            # 5. Ajouter des métadonnées
            analysis["source_url"] = url
            analysis["source_id"] = product_id
            analysis["analysis_timestamp"] = datetime.datetime.now().isoformat()
            
            logger.info(f"Analyse du produit {product_id} complétée avec succès")
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du produit: {e}")
            raise
    
    def _build_product_manager_prompt(self, url: str, product_id: str, content: str) -> str:
        """
        Construit un prompt détaillé pour que Grok agisse comme un product manager
        
        Args:
            url: URL du produit
            product_id: ID du produit
            content: Contenu textuel extrait de la page
            
        Returns:
            Prompt formaté
        """
        # Diviser le prompt en parties pour éviter les f-strings trop complexes
        product_info = f"""
        ## MISSION: PRODUCT MANAGER ALIEXPRESS

        Tu es un product manager expérimenté chargé d'analyser un produit AliExpress et de fournir une fiche produit optimisée
        avec une stratégie marketing complète pour la revente sur un site e-commerce.

        ### PRODUIT À ANALYSER
        
        URL: {url}
        ID Produit: {product_id}
        
        ### CONTENU DE LA PAGE
        
        ```
        {content[:8000]}... (contenu tronqué)
        ```
        """
        
        tasks = """
        ### TÂCHES À ACCOMPLIR
        
        1. **DONNÉES PRODUIT DE BASE**
           - Extraire le titre, prix, devise, et caractéristiques principales
           - Identifier la catégorie principale et sous-catégories
           - Détecter les variantes disponibles (couleurs, tailles, etc.)
        
        2. **ANALYSE MARKETING**
           - Points forts du produit (minimum 5)
           - Points faibles ou limitations (minimum 3)
           - Public cible idéal (qui achèterait ce produit et pourquoi)
           - Positionnement de marché recommandé (entrée de gamme, milieu de gamme, haut de gamme, luxe)
           - Occasions d'achat (quand les clients achèteraient ce produit)
        
        3. **OPTIMISATION POUR LA REVENTE**
           - Titre optimisé pour le SEO et la vente (max 100 caractères)
           - Description marketing optimisée (minimum 200 mots)
           - 3-5 arguments de vente uniques
           - Stratégie de prix recommandée (prix de vente suggéré et marge)
           - Mots-clés SEO pertinents (10-15)
        
        4. **RECOMMANDATIONS STRATÉGIQUES**
           - Idées de produits complémentaires
           - Améliorations recommandées pour la présentation
           - Objections d'achat potentielles et comment y répondre
           - Idées de contenu marketing pour promouvoir ce produit
           - Conseils pour différencier ce produit de la concurrence
        
        5. **MÉTADONNÉES TECHNIQUES**
           - Meta titre (max 60 caractères)
           - Meta description (max 155 caractères)
           - Alt text pour image principale (max 125 caractères)
           - Balises de produit recommandées
        """
        
        response_format = """
        ### FORMAT DE RÉPONSE
        
        Réponds strictement en format JSON selon cette structure:
        ```json
        {
            "basic_data": {
                "extracted_title": "Titre extrait de la page",
                "extracted_price": "Prix extrait",
                "extracted_currency": "Devise",
                "main_category": "Catégorie principale",
                "sub_categories": ["Sous-catégorie 1", "Sous-catégorie 2"],
                "available_variants": ["Variante 1", "Variante 2"]
            },
            "marketing_analysis": {
                "strengths": ["Point fort 1", "Point fort 2", ...],
                "weaknesses": ["Point faible 1", "Point faible 2", ...],
                "target_audience": {
                    "demographic": "Description démographique",
                    "interests": ["Intérêt 1", "Intérêt 2", ...],
                    "pain_points": ["Problème résolu 1", "Problème résolu 2", ...]
                },
                "market_positioning": "Positionnement recommandé",
                "purchase_occasions": ["Occasion 1", "Occasion 2", ...]
            },
            "resale_optimization": {
                "optimized_title": "Titre optimisé pour la vente",
                "marketing_description": "Description marketing complète",
                "unique_selling_points": ["Argument 1", "Argument 2", ...],
                "pricing_strategy": {
                    "recommended_price": "Prix recommandé",
                    "suggested_margin": "Marge suggérée en %"
                },
                "seo_keywords": ["Mot-clé 1", "Mot-clé 2", ...]
            },
            "strategic_recommendations": {
                "complementary_products": ["Produit 1", "Produit 2", ...],
                "presentation_improvements": ["Amélioration 1", "Amélioration 2", ...],
                "objection_handling": [
                    {"objection": "Objection 1", "response": "Réponse 1"},
                    {"objection": "Objection 2", "response": "Réponse 2"}
                ],
                "marketing_content_ideas": ["Idée 1", "Idée 2", ...],
                "differentiation_strategies": ["Stratégie 1", "Stratégie 2", ...]
            },
            "technical_metadata": {
                "meta_title": "Meta titre optimisé",
                "meta_description": "Meta description optimisée",
                "image_alt_text": "Texte alternatif pour l'image principale",
                "product_tags": ["Tag 1", "Tag 2", ...]
            }
        }
        ```
        """
        
        # Combiner toutes les parties du prompt
        return product_info + tasks + response_format
            
    async def generate_product_templates(self, analysis: Dict[str, Any], target_market: str = "moyenne_gamme") -> Dict[str, str]:
        """
        Génère des templates HTML optimisés pour la fiche produit basés sur l'analyse
        
        Args:
            analysis: Analyse produit générée par analyze_product_url
            target_market: Positionnement du marché cible
            
        Returns:
            Dict contenant les templates HTML générés
        """
        try:
            from product_generator import generate_product_html_templates
            
            # Préparer les données pour le générateur de templates
            product_data = {
                "name": analysis["resale_optimization"]["optimized_title"],
                "base_description": analysis["resale_optimization"]["marketing_description"],
                "category": analysis["basic_data"]["main_category"],
                "price": analysis["resale_optimization"]["pricing_strategy"]["recommended_price"],
                "features": analysis["marketing_analysis"]["strengths"],
                "keywords": analysis["resale_optimization"]["seo_keywords"],
                "meta_title": analysis["technical_metadata"]["meta_title"],
                "meta_description": analysis["technical_metadata"]["meta_description"],
                "alt_text": analysis["technical_metadata"]["image_alt_text"],
                "variants": analysis["basic_data"]["available_variants"],
                "target_audience": analysis["marketing_analysis"]["target_audience"],
                "unique_selling_points": analysis["resale_optimization"]["unique_selling_points"]
            }
            
            # Utiliser le générateur de templates existant
            templates = await generate_product_html_templates(product_data, target_market)
            
            # Ajouter un template pour les objections fréquentes
            objection_html = "<div class='product-faq'><h3>Questions fréquentes</h3><dl>"
            for obj in analysis["strategic_recommendations"]["objection_handling"]:
                objection_html += f"<dt>{obj['objection']}</dt><dd>{obj['response']}</dd>"
            objection_html += "</dl></div>"
            
            templates["html_objections"] = objection_html
            
            return templates
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des templates: {e}")
            raise