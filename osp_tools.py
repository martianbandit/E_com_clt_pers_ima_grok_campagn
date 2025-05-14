"""
Module d'outils marketing basés sur les standards OSP (Open Strategy Partners)
Intègre les bonnes pratiques en matière de marketing stratégique et de SEO
"""
from typing import Dict, List, Optional, Union
import json
import os
from flask import render_template

from ai_utils import AIManager

# Initialisation du gestionnaire d'IA
ai_manager = AIManager(
    openai_api_key=os.environ.get("OPENAI_API_KEY"), 
    xai_api_key=os.environ.get("XAI_API_KEY")
)

def generate_product_value_map(
    product_name: str,
    product_description: str,
    target_audience: str,
    industry: str,
    niche_market: Optional[str] = None,
    key_features: Optional[List[str]] = None,
    competitors: Optional[List[str]] = None,
) -> Dict:
    """
    Génère une carte de valeur produit selon la méthodologie OSP
    
    Args:
        product_name: Nom du produit
        product_description: Description détaillée du produit
        target_audience: Description de l'audience cible
        industry: Secteur d'activité principal
        niche_market: Créneau de marché spécifique (optionnel)
        key_features: Liste des fonctionnalités clés (optionnel)
        competitors: Liste des concurrents principaux (optionnel)
    
    Returns:
        Dictionnaire contenant la carte de valeur complète
    """
    # Construction du prompt
    prompt = f"""
    Crée une carte de valeur complète pour le produit suivant selon la méthodologie OSP.
    
    ## Informations sur le produit
    - Nom du produit: {product_name}
    - Description: {product_description}
    - Audience cible: {target_audience}
    - Secteur: {industry}
    """
    
    if niche_market:
        prompt += f"- Créneau de marché: {niche_market}\n"
    if key_features:
        prompt += f"- Fonctionnalités clés: {', '.join(key_features)}\n"
    if competitors:
        prompt += f"- Concurrents: {', '.join(competitors)}\n"
    
    prompt += """
    ## Structure de la carte de valeur requise
    Renvoie un objet JSON structuré contenant:
    
    1. taglines: Liste de 3 phrases d'accroche percutantes (max 15 mots chacune)
    2. position_statements: Liste de 2 déclarations de positionnement complètes (format "Pour [audience], [nom du produit] est [avantage clé] qui [différenciation]."
    3. value_propositions: Liste de 4-6 propositions de valeur avec pour chacune:
       - title: Titre court (3-5 mots)
       - description: Description de la proposition de valeur (1-2 phrases)
       - benefits: Liste de 2-3 avantages spécifiques
    4. unique_selling_points: Liste de 3-4 points de vente uniques, chacun avec:
       - title: Titre court du point de vente unique
       - comparative_advantage: Avantage par rapport à la concurrence
    5. audiences: Liste de 2-3 segments d'audience, chacun avec:
       - segment: Nom du segment (ex: "Propriétaires de boutiques en ligne")
       - needs: Liste de 2-3 besoins spécifiques
       - pain_points: Liste de 2-3 points de douleur
       - journey_stage: Étape du parcours client qui correspond le mieux à ce segment
    6. keywords: Liste de 8-10 mots-clés pertinents pour le SEO, classés par priorité

    Réponds uniquement avec l'objet JSON, sans texte supplémentaire.
    """
    
    # Génération du contenu avec l'IA
    try:
        value_map = ai_manager.generate_json(
            prompt=prompt,
            metric_name="osp_product_value_map_generation",
            max_tokens=1500
        )
        
        # Validation de la structure
        validate_value_map(value_map)
        
        return value_map
    except Exception as e:
        print(f"Erreur lors de la génération de la carte de valeur: {str(e)}")
        # Renvoyer une structure minimale en cas d'erreur
        return {
            "taglines": ["Erreur lors de la génération de la carte de valeur"],
            "position_statements": [],
            "value_propositions": [],
            "unique_selling_points": [],
            "audiences": [],
            "keywords": []
        }

def validate_value_map(value_map: Dict) -> bool:
    """
    Valide la structure de la carte de valeur
    
    Args:
        value_map: Dictionnaire contenant la carte de valeur
        
    Returns:
        True si la structure est valide
        
    Raises:
        ValueError: Si la structure n'est pas valide
    """
    required_keys = [
        "taglines", 
        "position_statements", 
        "value_propositions",
        "unique_selling_points",
        "audiences",
        "keywords"
    ]
    
    for key in required_keys:
        if key not in value_map:
            raise ValueError(f"La clé '{key}' est manquante dans la carte de valeur")
        
        if not isinstance(value_map[key], list):
            raise ValueError(f"La valeur de '{key}' doit être une liste")
    
    # Validation des structures imbriquées
    for vp in value_map["value_propositions"]:
        if not all(k in vp for k in ["title", "description", "benefits"]):
            raise ValueError("Structure invalide dans value_propositions")
    
    for usp in value_map["unique_selling_points"]:
        if not all(k in usp for k in ["title", "comparative_advantage"]):
            raise ValueError("Structure invalide dans unique_selling_points")
    
    for audience in value_map["audiences"]:
        if not all(k in audience for k in ["segment", "needs", "pain_points"]):
            raise ValueError("Structure invalide dans audiences")
    
    return True

def analyze_content_with_osp_guidelines(
    content: str,
    content_type: str = "product_description",
    target_audience: Optional[str] = None,
    industry: Optional[str] = None
) -> Dict:
    """
    Analyse le contenu selon les directives OSP et fournit des recommandations
    
    Args:
        content: Le contenu à analyser
        content_type: Type de contenu (product_description, landing_page, email, etc.)
        target_audience: Description de l'audience cible (optionnel)
        industry: Secteur d'activité (optionnel)
        
    Returns:
        Dictionnaire contenant l'analyse et les recommandations
    """
    prompt = f"""
    Analyse le contenu suivant selon les directives OSP et fournit des recommandations d'amélioration.
    
    ## Contenu à analyser ({content_type})
    {content}
    
    """
    
    if target_audience:
        prompt += f"\n## Audience cible\n{target_audience}\n"
    if industry:
        prompt += f"\n## Secteur d'activité\n{industry}\n"
    
    prompt += """
    ## Directives d'analyse OSP
    Analyse le contenu selon les critères suivants et fournit des recommandations précises:
    
    1. Clarté et concision: Le message est-il clair et direct?
    2. Structure et organisation: Le contenu est-il bien structuré?
    3. Tonalité et voix: Le ton est-il approprié pour l'audience?
    4. Positionnement: Le contenu positionne-t-il correctement le produit/service?
    5. Appel à l'action: Les actions souhaitées sont-elles clairement définies?
    6. SEO optimisation: Le contenu utilise-t-il efficacement les mots-clés?
    7. Adaptation à l'audience: Le contenu répond-il aux besoins spécifiques de l'audience?
    
    Pour chaque point, noter de 1-5 et fournir des suggestions d'amélioration avec exemples concrets.
    
    Réponds avec un objet JSON contenant:
    
    1. scores: Objet avec les notes pour chaque critère
    2. strengths: Liste des points forts du contenu (3-5 éléments)
    3. weaknesses: Liste des points à améliorer (3-5 éléments)
    4. recommendations: Liste de recommandations spécifiques (4-6 éléments)
    5. improved_examples: Exemples de passages améliorés (2-3 exemples)
    """
    
    try:
        analysis = ai_manager.generate_json(
            prompt=prompt,
            metric_name="osp_content_analysis",
            max_tokens=1500
        )
        
        return analysis
    except Exception as e:
        print(f"Erreur lors de l'analyse du contenu: {str(e)}")
        return {
            "scores": {"overall": 0},
            "strengths": ["Erreur lors de l'analyse"],
            "weaknesses": ["Erreur lors de l'analyse"],
            "recommendations": ["Erreur lors de l'analyse"],
            "improved_examples": []
        }

def apply_seo_guidelines(
    content: Dict,
    page_type: str = "product",
    locale: str = "fr_FR",
    is_local_business: bool = True
) -> Dict:
    """
    Applique les directives SEO d'OSP au contenu
    
    Args:
        content: Dictionnaire contenant le contenu à optimiser
        page_type: Type de page (product, category, landing, blog, etc.)
        locale: Code de langue et pays (fr_FR, en_US, etc.)
        is_local_business: Indique si l'entreprise est locale
        
    Returns:
        Dictionnaire contenant le contenu optimisé avec métadonnées SEO
    """
    # Extraction des éléments pertinents du contenu
    title = content.get("title", "")
    description = content.get("description", "")
    
    # Construction du prompt
    prompt = f"""
    Optimise les métadonnées SEO pour le contenu suivant selon les directives OSP.
    
    ## Contenu
    - Titre: {title}
    - Description: {description}
    - Type de page: {page_type}
    - Locale: {locale}
    - Entreprise locale: {"Oui" if is_local_business else "Non"}
    
    ## Directives SEO OSP
    Génère un objet JSON contenant les éléments suivants optimisés pour le SEO:
    
    1. meta_title: Titre meta optimisé (max 60 caractères)
    2. meta_description: Description meta (max 160 caractères)
    3. h1: Titre principal optimisé
    4. schema_markup: Structure de données schema.org appropriée pour ce type de page
    5. alt_text_suggestions: Suggestions de texte alternatif pour les images
    6. structured_data: Données structurées supplémentaires si nécessaires
    7. url_slug: Slug d'URL optimisé pour le SEO
    8. keywords: Liste de mots-clés pertinents (primaires et secondaires)
    9. local_seo: Optimisations spécifiques pour le SEO local (si applicable)
    
    Réponds uniquement avec l'objet JSON, sans texte supplémentaire.
    """
    
    try:
        seo_optimized = ai_manager.generate_json(
            prompt=prompt,
            metric_name="osp_seo_optimization",
            max_tokens=1000
        )
        
        # Fusion avec le contenu original
        optimized_content = content.copy()
        optimized_content.update({
            "seo": seo_optimized
        })
        
        return optimized_content
    except Exception as e:
        print(f"Erreur lors de l'optimisation SEO: {str(e)}")
        return content  # Retourne le contenu original en cas d'erreur

def render_value_map_html(value_map: Dict) -> str:
    """
    Génère une représentation HTML de la carte de valeur
    
    Args:
        value_map: Dictionnaire contenant la carte de valeur
        
    Returns:
        HTML formaté pour afficher la carte de valeur
    """
    html = """
    <div class="osp-value-map">
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Phrases d'accroche</h3>
            <ul class="taglines-list" style="color: var(--bs-dark);">
    """
    
    # Taglines
    for tagline in value_map.get("taglines", []):
        html += f'<li class="value-map-item">{tagline}</li>\n'
    
    html += """
            </ul>
        </div>
        
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Déclarations de positionnement</h3>
            <ul class="position-statements-list" style="color: var(--bs-dark);">
    """
    
    # Position statements
    for statement in value_map.get("position_statements", []):
        html += f'<li class="value-map-item">{statement}</li>\n'
    
    html += """
            </ul>
        </div>
        
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Propositions de valeur</h3>
            <div class="row">
    """
    
    # Value propositions
    for vp in value_map.get("value_propositions", []):
        html += f"""
            <div class="col-md-4 mb-4">
                <div class="card h-100 bg-light">
                    <div class="card-header" style="background-color: var(--bs-light); border-bottom: 2px solid var(--bs-primary);">
                        <h4 style="color: var(--bs-dark);">{vp.get("title", "")}</h4>
                    </div>
                    <div class="card-body" style="color: var(--bs-dark);">
                        <p style="color: var(--bs-dark);">{vp.get("description", "")}</p>
                        <ul style="color: var(--bs-dark);">
        """
        
        for benefit in vp.get("benefits", []):
            html += f'<li style="color: var(--bs-dark);">{benefit}</li>\n'
        
        html += """
                        </ul>
                    </div>
                </div>
            </div>
        """
    
    html += """
            </div>
        </div>
        
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Points de vente uniques</h3>
            <div class="row">
    """
    
    # USPs
    for usp in value_map.get("unique_selling_points", []):
        html += f"""
            <div class="col-md-6 mb-3">
                <div class="card h-100 bg-light">
                    <div class="card-header" style="background-color: var(--bs-light); border-bottom: 2px solid var(--bs-success);">
                        <h4 style="color: var(--bs-dark);">{usp.get("title", "")}</h4>
                    </div>
                    <div class="card-body" style="color: var(--bs-dark);">
                        <p style="color: var(--bs-dark);"><strong>Avantage comparatif:</strong> {usp.get("comparative_advantage", "")}</p>
                    </div>
                </div>
            </div>
        """
    
    html += """
            </div>
        </div>
        
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Segments d'audience</h3>
            <div class="row">
    """
    
    # Audiences
    for audience in value_map.get("audiences", []):
        html += f"""
            <div class="col-md-4 mb-4">
                <div class="card h-100 bg-light">
                    <div class="card-header" style="background-color: var(--bs-light); border-bottom: 2px solid var(--bs-info);">
                        <h4 style="color: var(--bs-dark);">{audience.get("segment", "")}</h4>
                    </div>
                    <div class="card-body" style="color: var(--bs-dark);">
                        <h5 style="color: var(--bs-dark);">Besoins</h5>
                        <ul style="color: var(--bs-dark);">
        """
        
        for need in audience.get("needs", []):
            html += f'<li style="color: var(--bs-dark);">{need}</li>\n'
        
        html += """
                        </ul>
                        <h5 style="color: var(--bs-dark);">Points de douleur</h5>
                        <ul style="color: var(--bs-dark);">
        """
        
        for pain in audience.get("pain_points", []):
            html += f'<li style="color: var(--bs-dark);">{pain}</li>\n'
        
        html += """
                        </ul>
        """
        
        if audience.get("journey_stage"):
            html += f'<p style="color: var(--bs-dark);"><strong>Étape du parcours:</strong> {audience.get("journey_stage")}</p>\n'
        
        html += """
                    </div>
                </div>
            </div>
        """
    
    html += """
            </div>
        </div>
        
        <div class="value-map-section">
            <h3 style="color: var(--bs-dark);">Mots-clés prioritaires</h3>
            <div class="keyword-tags" style="color: var(--bs-dark);">
    """
    
    # Keywords
    for keyword in value_map.get("keywords", []):
        html += f'<span class="badge bg-primary text-light me-2 mb-2">{keyword}</span>\n'
    
    html += """
            </div>
        </div>
    </div>
    """
    
    return html