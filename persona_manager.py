"""
Module pour la gestion des personas clients et leur assignation aux profils clients
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import json

from sqlalchemy import func
from app import db
from models import Customer, CustomerPersona, CustomerPersonaAssociation, NicheMarket, Boutique
import boutique_ai as ai_module

def create_persona_from_text(
    title: str,
    description: str,
    niche_market_id: Optional[int] = None,
    boutique_id: Optional[int] = None,
    additional_data: Optional[Dict] = None
) -> CustomerPersona:
    """
    Crée un nouveau persona à partir d'une description textuelle
    
    Args:
        title: Titre du persona (ex: "Jeune maman urbaine", "Entrepreneur tech", "Retraité", "Etudiant" , etc.)
        description: Description détaillée du persona
        niche_market_id: ID de la niche de marché 
        boutique_id: ID de la boutique 
        additional_data: Données supplémentaires pour le persona 
        
    Returns:
        Instance de CustomerPersona créée
    """
    # Valeurs par défaut pour les données supplémentaires
    data = {
        'titre': title,
        'description': description,
        'objectif_principal': None,
        'points_douleur': None,
        'declencheurs_achat': None,
        'tranche_age': None,
        'affinite_genre': None,
        'type_localisation': None,
        'tranche_revenu': None,
        'niveau_etudes': None,
        'valeurs': None,
        'centres_interet': None,
        'mode_vie': None,
        'traits_personnalite': None,
        'habitudes_achat': None,
        'affinites_marques': None,
        'sensibilite_prix': None,
        'facteurs_decision': None,
        'canaux_preferes': None,
        'preferences_contenu': None,
        'comportement_reseaux_sociaux': None,
        'attributs_specifiques': None,
        'champs_personnalises': None,
        'url_avatar': None,
        'prompt_avatar': None
    }
    
    # Mise à jour avec les données supplémentaires fournies
    if additional_data:
        data.update(additional_data)
        
    # Création du persona
    persona = CustomerPersona.create_from_dict(data, niche_market_id, boutique_id)
    db.session.add(persona)
    db.session.commit()
    
    return persona

async def enrich_persona_with_ai(
    persona_id: int, 
    api_key: Optional[str] = None
) -> CustomerPersona:
    """
    Enrichit un persona existant avec l'IA pour ajouter des détails supplémentaires
    
    Args:
        persona_id: ID du persona à enrichir
        api_key: Clé API pour l'IA (optionnel)
        
    Returns:
        Instance de CustomerPersona enrichie
    """
    persona = CustomerPersona.query.get_or_404(persona_id)
    
    # Préparer le contexte pour l'IA
    niche_info = {}
    if persona.niche_market_id:
        niche = NicheMarket.query.get(persona.niche_market_id)
        if niche:
            niche_info = {
                'name': niche.name,
                'description': niche.description,
                'characteristics': niche.get_characteristics_list()
            }
    
    boutique_info = {}
    if persona.boutique_id:
        boutique = Boutique.query.get(persona.boutique_id)
        if boutique:
            boutique_info = {
                'name': boutique.name,
                'description': boutique.description,
                'demographic': boutique.target_demographic
            }
    
    # Construire le contexte complet
    context = {
        'title': persona.title,
        'description': persona.description,
        'niche_market': niche_info,
        'boutique': boutique_info
    }
    
    # Générer l'enrichissement avec l'IA
    try:
        # Si on a un client IA configuré, l'utiliser directement
        openai_client = ai_module.get_openai_client(api_key)
        
        # Construire un prompt spécifique pour enrichir le persona
        prompt = f"""
        Je suis un stratège marketing qui doit enrichir un persona client. Voici le persona actuel:
        
        Titre: {persona.title}
        Description: {persona.description}
        
        {f"Niche de marché: {niche_info.get('name', '')}" if niche_info else ""}
        {f"Description de la niche: {niche_info.get('description', '')}" if niche_info and niche_info.get('description') else ""}
        {f"Boutique: {boutique_info.get('name', '')}" if boutique_info else ""}
        {f"Description de la boutique: {boutique_info.get('description', '')}" if boutique_info and boutique_info.get('description') else ""}
        
        Je voudrais enrichir ce persona avec les éléments suivants:
        1. Objectif principal du persona
        2. Points de douleur/frustrations
        3. Déclencheurs d'achat
        4. Tranche d'âge
        5. Affinité de genre
        6. Type de localisation (urbain, rural, etc.)
        7. Tranche de revenus
        8. Niveau d'éducation
        9. Valeurs importantes (format JSON avec tableau de valeurs)
        10. Centres d'intérêt (format JSON avec tableau d'intérêts)
        11. Style de vie
        12. Traits de personnalité (format JSON avec tableau de traits)
        13. Habitudes d'achat
        14. Affinités de marque (format JSON avec tableau de marques et niveau d'affinité)
        15. Sensibilité aux prix
        16. Facteurs de décision d'achat (format JSON avec tableau de facteurs)
        17. Canaux de communication préférés (format JSON avec tableau de canaux)
        18. Préférences de contenu
        19. Comportement sur les réseaux sociaux (format JSON avec plateforme et fréquence)
        
        Réponds uniquement avec un objet JSON contenant ces éléments.
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Utiliser le modèle le plus récent
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        enrichment = json.loads(response.choices[0].message.content)
        
        # Mettre à jour le persona avec les données enrichies
        for key, value in enrichment.items():
            setattr(persona, key, value)
        
        db.session.commit()
        return persona
        
    except Exception as e:
        print(f"Erreur lors de l'enrichissement du persona: {e}")
        # En cas d'erreur, retourner le persona non modifié
        return persona

def assign_persona_to_customer(
    customer_id: int,
    persona_id: int,
    is_primary: bool = True,
    relevance_score: Optional[float] = None,
    notes: Optional[str] = None
) -> CustomerPersonaAssociation:
    """
    Assigne un persona à un client
    
    Args:
        customer_id: ID du client
        persona_id: ID du persona
        is_primary: Indique si c'est le persona principal du client
        relevance_score: Score de pertinence (0-1)
        notes: Notes sur l'association
        
    Returns:
        Association créée ou mise à jour
    """
    customer = Customer.query.get_or_404(customer_id)
    
    # Vérifier que le persona existe
    persona = CustomerPersona.query.get_or_404(persona_id)
    
    # Créer ou mettre à jour l'association
    association = customer.assign_persona(
        persona_id=persona_id,
        is_primary=is_primary,
        relevance_score=relevance_score,
        notes=notes
    )
    
    db.session.commit()
    return association

def get_customer_personas(customer_id: int) -> List[Dict]:
    """
    Récupère tous les personas associés à un client
    
    Args:
        customer_id: ID du client
        
    Returns:
        Liste de dictionnaires contenant les personas et leur association
    """
    associations = CustomerPersonaAssociation.query.filter_by(customer_id=customer_id).all()
    
    result = []
    for assoc in associations:
        persona = assoc.persona
        result.append({
            'association_id': assoc.id,
            'persona_id': persona.id,
            'title': persona.title,
            'description': persona.description,
            'is_primary': assoc.is_primary,
            'relevance_score': assoc.relevance_score,
            'notes': assoc.notes,
            'created_at': assoc.created_at
        })
    
    return result

def generate_persona_from_customer(
    customer_id: int,
    title: Optional[str] = None,
    save_as_primary: bool = True
) -> CustomerPersona:
    """
    Génère un nouveau persona à partir des données d'un client existant
    
    Args:
        customer_id: ID du client source
        title: Titre du persona (optionnel, généré automatiquement sinon)
        save_as_primary: Indique si le persona généré doit être défini comme persona principal du client
        
    Returns:
        Instance de CustomerPersona créée
    """
    customer = Customer.query.get_or_404(customer_id)
    
    # Générer un titre par défaut si non fourni
    if not title:
        title = f"Persona pour {customer.name}"
    
    # Utiliser le persona existant comme base si disponible
    description = customer.persona or f"Persona basé sur le profil client de {customer.name}."
    
    # Préparer les données supplémentaires à partir du profil client
    interests = []
    if customer.interests:
        interests = customer.get_interests_list()
    
    additional_data = {
        'age_range': f"{customer.age - 5}-{customer.age + 5}" if customer.age else None,
        'gender_affinity': customer.gender,
        'location_type': "Urbain" if customer.location and any(city in customer.location.lower() for city in ["paris", "lyon", "marseille", "lille", "bordeaux"]) else "Périurbain",
        'income_bracket': customer.income_level,
        'education_level': customer.education,
        'interests': interests,
        'niche_specific_attributes': customer.niche_attributes,
        'avatar_url': customer.avatar_url,
        'avatar_prompt': customer.avatar_prompt,
        'social_media_behavior': customer.social_media
    }
    
    # Créer le persona
    persona = create_persona_from_text(
        title=title,
        description=description,
        niche_market_id=customer.niche_market_id,
        boutique_id=customer.boutique_id,
        additional_data=additional_data
    )
    
    # Assigner le persona au client si demandé
    if save_as_primary:
        assign_persona_to_customer(
            customer_id=customer.id,
            persona_id=persona.id,
            is_primary=True,
            relevance_score=1.0,
            notes="Persona généré automatiquement à partir du profil client."
        )
    
    return persona

def find_matching_personas(
    criteria: Dict,
    limit: int = 5,
    niche_market_id: Optional[int] = None,
    boutique_id: Optional[int] = None
) -> List[CustomerPersona]:
    """
    Recherche des personas correspondant à des critères spécifiques
    
    Args:
        criteria: Dictionnaire de critères de recherche
        limit: Nombre maximum de résultats
        niche_market_id: Filtrer par niche de marché (optionnel)
        boutique_id: Filtrer par boutique (optionnel)
        
    Returns:
        Liste de personas correspondant aux critères
    """
    query = CustomerPersona.query
    
    # Appliquer les filtres de base
    if niche_market_id:
        query = query.filter_by(niche_market_id=niche_market_id)
    
    if boutique_id:
        query = query.filter_by(boutique_id=boutique_id)
    
    # Appliquer les critères de recherche
    if 'title' in criteria:
        query = query.filter(CustomerPersona.title.ilike(f"%{criteria['title']}%"))
    
    if 'age_range' in criteria:
        query = query.filter(CustomerPersona.age_range == criteria['age_range'])
    
    if 'gender_affinity' in criteria:
        query = query.filter(CustomerPersona.gender_affinity == criteria['gender_affinity'])
    
    if 'income_bracket' in criteria:
        query = query.filter(CustomerPersona.income_bracket == criteria['income_bracket'])
    
    if 'education_level' in criteria:
        query = query.filter(CustomerPersona.education_level == criteria['education_level'])
    
    if 'price_sensitivity' in criteria:
        query = query.filter(CustomerPersona.price_sensitivity == criteria['price_sensitivity'])
    
    # Appliquer une recherche textuelle sur la description
    if 'description_keywords' in criteria and criteria['description_keywords']:
        keywords = criteria['description_keywords'].split()
        for keyword in keywords:
            query = query.filter(CustomerPersona.description.ilike(f"%{keyword}%"))
    
    # Exécuter la requête avec limite
    personas = query.limit(limit).all()
    return personas

def get_personas_stats() -> Dict:
    """
    Récupère des statistiques sur les personas dans le système
    
    Returns:
        Dictionnaire contenant diverses statistiques
    """
    total_personas = CustomerPersona.query.count()
    total_associations = CustomerPersonaAssociation.query.count()
    personas_with_avatar = CustomerPersona.query.filter(CustomerPersona.avatar_url.isnot(None)).count()
    
    personas_by_niche = db.session.query(
        NicheMarket.name, 
        func.count(CustomerPersona.id)
    ).join(
        CustomerPersona, 
        NicheMarket.id == CustomerPersona.niche_market_id
    ).group_by(
        NicheMarket.name
    ).all()
    
    personas_by_boutique = db.session.query(
        Boutique.name, 
        func.count(CustomerPersona.id)
    ).join(
        CustomerPersona, 
        Boutique.id == CustomerPersona.boutique_id
    ).group_by(
        Boutique.name
    ).all()
    
    return {
        'total_personas': total_personas,
        'total_associations': total_associations,
        'personas_with_avatar': personas_with_avatar,
        'personas_by_niche': dict(personas_by_niche),
        'personas_by_boutique': dict(personas_by_boutique)
    }

def convert_legacy_personas() -> int:
    """
    Convertit les anciens personas (stockés comme texte dans la table Customer) 
    en instances CustomerPersona structurées
    
    Returns:
        Nombre de personas convertis
    """
    # Récupérer tous les clients avec un persona défini
    customers = Customer.query.filter(Customer.persona.isnot(None)).all()
    
    count = 0
    for customer in customers:
        # Vérifier si le client a déjà un persona structuré assigné
        existing_primary = CustomerPersonaAssociation.query.filter_by(
            customer_id=customer.id,
            is_primary=True
        ).first()
        
        # Ne pas créer de nouveau persona si le client a déjà un persona principal
        if existing_primary:
            continue
        
        print(f"Traitement du client: {customer.name}")
            
        # Créer un nouveau persona à partir du texte
        try:
            # Pour éviter les erreurs d'âge négatif
            age_range = None
            if customer.age:
                min_age = max(18, customer.age - 5)  # Minimum 18 ans
                max_age = customer.age + 5
                age_range = f"{min_age}-{max_age}"
            
            persona = create_persona_from_text(
                title=f"Persona pour {customer.name}",
                description=customer.persona or f"Profil de {customer.name}",
                niche_market_id=customer.niche_market_id,
                boutique_id=customer.boutique_id,
                additional_data={
                    'age_range': age_range,
                    'gender_affinity': customer.gender,
                    'income_bracket': customer.income_level,
                    'education_level': customer.education,
                    'avatar_url': customer.avatar_url,
                    'avatar_prompt': customer.avatar_prompt
                }
            )
            
            # Assigner le persona au client
            assign_persona_to_customer(
                customer_id=customer.id,
                persona_id=persona.id,
                is_primary=True,
                relevance_score=1.0,
                notes="Persona converti depuis l'ancien format."
            )
            
            # Commit après chaque persona pour éviter une longue transaction
            db.session.commit()
            
            count += 1
            print(f"Persona créé et assigné avec succès pour {customer.name}")
        except Exception as e:
            print(f"Erreur lors de la conversion du persona pour le client {customer.id}: {e}")
            # Continuer malgré l'erreur
            db.session.rollback()
    
    return count