import os
import json
import asyncio
import logging
from enum import Enum
from typing import List, Dict, Optional, Union
import random
import time
from flask import session, current_app
from flask_babel import gettext as _

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    logger.warning("OpenAI package not found. Some functionality may be limited.")
    
try:
    from pydantic import BaseModel, Field
except ImportError:
    logger.warning("Pydantic package not found. Some functionality may be limited.")
    # Create stub class for compatibility
    class BaseModel:
        pass
    Field = lambda *args, **kwargs: None

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv package not found. Skipping .env loading.")

# Grok model constants
GROK_3 = "grok-3-fast"
GROK_2_IMAGE = "grok-2-image-1212"  # le modèle d'image correct de xAI (Grok)

def get_prompt_language():
    """
    Récupère la langue active pour les prompts en fonction de la session
    
    Returns:
        Code de langue (fr, en, etc.) ou 'en' par défaut
    """
    try:
        # Récupérer la langue de la session si disponible
        if session and 'language' in session:
            return session['language']
        return 'en'  # Langue par défaut
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de la langue: {e}")
        return 'en'  # Fallback à l'anglais en cas d'erreur

# Dictionnaire de traductions pour les prompts
PROMPT_TRANSLATIONS = {
    # Prompts pour la génération de personas clients
    "customer_persona": {
        "en": """
        Create a detailed customer persona for {name}, a {age}-year-old {gender} from {location}.

        Include the following sections in your response:

        1. BACKGROUND & OVERVIEW
        - Brief background story (2-3 sentences)
        - Personality traits and general outlook
        - Life situation and daily challenges

        2. SHOPPING PSYCHOLOGY
        - Primary motivations for shopping in the {niche} niche
        - Key pain points and frustrations when shopping
        - Decision-making factors (price sensitivity, quality focus, etc.)
        - How they discover new products (social media, word of mouth, etc.)

        3. MARKET SEGMENT INSIGHTS
        - Where they fit in the overall {niche} market
        - Specific preferences within the {niche} category
        - Typical purchase frequency and spending patterns
        - Brand affinities and loyalty characteristics

        4. CONTENT & MARKETING RECEPTIVITY
        - Type of marketing messages most likely to resonate
        - Preferred communication channels
        - Content format preferences (video, text, visual, etc.)
        - Tone of voice that appeals to them
                
        ADDITIONAL CONTEXT:
        - Interests: {interests}
        - Recent purchases: {purchases}
        
        STYLE GUIDELINES:
        - Write in a clear, insightful manner
        - Create a realistic, three-dimensional person (not a stereotype)
        - Include specific, memorable details that bring the persona to life
        - Make the persona feel unique and distinct from other standard customer profiles
        
        {existing_personas_summary}
        {boutique_context}
        """,
        
        "fr": """
        Créez un persona client détaillé pour {name}, {gender} de {age} ans vivant à {location}.

        Incluez les sections suivantes dans votre réponse:

        1. CONTEXTE & VUE D'ENSEMBLE
        - Bref récit de fond (2-3 phrases)
        - Traits de personnalité et perspective générale
        - Situation de vie et défis quotidiens

        2. PSYCHOLOGIE D'ACHAT
        - Motivations principales pour acheter dans la niche {niche}
        - Points de douleur et frustrations lors des achats
        - Facteurs de décision (sensibilité au prix, focus sur la qualité, etc.)
        - Comment ils découvrent de nouveaux produits (réseaux sociaux, bouche à oreille, etc.)

        3. APERÇU DU SEGMENT DE MARCHÉ
        - Où ils se situent dans le marché global de {niche}
        - Préférences spécifiques dans la catégorie {niche}
        - Fréquence d'achat typique et habitudes de dépenses
        - Affinités de marque et caractéristiques de fidélité

        4. RÉCEPTIVITÉ AU CONTENU & MARKETING
        - Types de messages marketing qui résonnent le plus
        - Canaux de communication préférés
        - Préférences de format de contenu (vidéo, texte, visuel, etc.)
        - Ton de voix qui les attire
                
        CONTEXTE SUPPLÉMENTAIRE:
        - Intérêts: {interests}
        - Achats récents: {purchases}
        
        DIRECTIVES DE STYLE:
        - Écrivez de manière claire et perspicace
        - Créez une personne réaliste et tridimensionnelle (pas un stéréotype)
        - Incluez des détails spécifiques et mémorables qui donnent vie au persona
        - Faites en sorte que le persona soit unique et distinct des autres profils clients standards
        
        {existing_personas_summary}
        {boutique_context}
        """
    },
    
    # Prompts pour la génération d'avatar
    "avatar_generation": {
        "en": """
        Create a detailed prompt for generating a profile picture avatar for this specific customer persona:
        
        Customer Name: {name}
        Age: {age}
        Gender: {gender}
        Location: {location}
        Interests: {interests}
        Niche Market: {niche}
        
        Persona: 
        {persona_excerpt}
        
        Create an avatar prompt that:
        1. Describes a professional headshot/portrait style image
        2. Includes distinctive visual characteristics based on the persona
        3. Suggests appropriate clothing and accessories related to the {niche} niche
        4. Specifies background elements that reflect their lifestyle or interests
        5. Indicates appropriate lighting and mood that matches their personality
        6. DOES NOT include any text or words in the image itself
        
        The prompt should be detailed yet concise (maximum 100 words), focusing on visual elements only.
        Format your response as just the prompt text, without explanations or extra information.
        """,
        
        "fr": """
        Créez un prompt détaillé pour générer une photo de profil avatar pour ce persona client spécifique:
        
        Nom du client: {name}
        Âge: {age}
        Genre: {gender}
        Lieu: {location}
        Intérêts: {interests}
        Marché de niche: {niche}
        
        Persona: 
        {persona_excerpt}
        
        Créez un prompt d'avatar qui:
        1. Décrit une image de style portrait/photo de profil professionnelle
        2. Inclut des caractéristiques visuelles distinctives basées sur le persona
        3. Suggère des vêtements et accessoires appropriés liés à la niche {niche}
        4. Spécifie des éléments d'arrière-plan qui reflètent son style de vie ou ses intérêts
        5. Indique un éclairage et une ambiance appropriés qui correspondent à sa personnalité
        6. NE contient PAS de texte ou de mots dans l'image elle-même
        
        Le prompt doit être détaillé mais concis (maximum 100 mots), en se concentrant uniquement sur les éléments visuels.
        Formatez votre réponse avec uniquement le texte du prompt, sans explications ni informations supplémentaires.
        """
    },
    
    # Prompts pour la génération de contenu marketing
    "marketing_content": {
        "en": """
        Create personalized {campaign_type} marketing content for {name} based on their customer profile:
        
        CUSTOMER PROFILE:
        {persona}
        
        MARKETING CONTENT SPECIFICATIONS:
        - Campaign Type: {campaign_type}
        - Target: {name}
        - Niche Market: {niche}
        - Key Interests: {interests}
        - Language: {language}
        
        {boutique_context}
        
        CONTENT GUIDELINES:
        1. Create content that speaks directly to this specific customer's needs and motivations
        2. Address their specific pain points and preferences
        3. Highlight benefits that would resonate with their particular situation
        4. Use language, tone and style that will appeal specifically to them
        5. Include a clear call-to-action that would motivate this specific customer
        6. Keep the content concise, engaging and emotionally resonant
        
        FORMAT FOR DIFFERENT CHANNELS:
        - Email: Include subject line, greeting, body text and sign-off
        - Social Media: Create post copy optimized for the platform most relevant to this customer
        - SMS: Create a brief, compelling message (160 characters max) with clear value proposition
        - Ad: Include headline, main copy, and call-to-action for digital advertising
        - Product Description: Create compelling product copy tailored to this customer's interests
        
        The content should feel personally created for this specific customer, not generic marketing.
        """,
        
        "fr": """
        Créez un contenu marketing {campaign_type} personnalisé pour {name} basé sur son profil client:
        
        PROFIL CLIENT:
        {persona}
        
        SPÉCIFICATIONS DU CONTENU MARKETING:
        - Type de campagne: {campaign_type}
        - Cible: {name}
        - Marché de niche: {niche}
        - Intérêts clés: {interests}
        - Langue: {language}
        
        {boutique_context}
        
        DIRECTIVES DE CONTENU:
        1. Créez un contenu qui parle directement aux besoins et motivations de ce client spécifique
        2. Adressez ses points de douleur et préférences spécifiques
        3. Soulignez les avantages qui résonneraient avec sa situation particulière
        4. Utilisez un langage, ton et style qui lui plairont spécifiquement
        5. Incluez un appel à l'action clair qui motiverait ce client spécifique
        6. Gardez le contenu concis, engageant et émotionnellement résonnant
        
        FORMAT POUR DIFFÉRENTS CANAUX:
        - Email: Inclure objet, salutation, corps du texte et signature
        - Médias sociaux: Créer un texte de publication optimisé pour la plateforme la plus pertinente pour ce client
        - SMS: Créer un message bref et convaincant (160 caractères max) avec une proposition de valeur claire
        - Publicité: Inclure un titre, texte principal et appel à l'action pour la publicité numérique
        - Description de produit: Créer un texte de produit convaincant adapté aux intérêts de ce client
        
        Le contenu doit sembler personnellement créé pour ce client spécifique, pas un marketing générique.
        """
    },
    
    # Prompt pour la génération d'image de campagne
    "campaign_image": {
        "en": """
        Create a detailed image prompt for a marketing campaign in the {niche} niche targeted at {customer_name}.
        
        CAMPAIGN CONTEXT:
        {campaign_description}
        
        CUSTOMER PROFILE:
        {customer_profile}
        
        BOUTIQUE INFORMATION:
        {boutique_info}
        
        IMAGE REQUIREMENTS:
        1. Create a vivid, professional marketing image that would resonate with this specific customer
        2. The image should represent the {niche} niche in an authentic, appealing way
        3. Focus on visual elements that would attract this specific customer based on their profile
        4. Include relevant products, environments, or lifestyle elements that connect with their interests
        5. The image style should match the boutique's branding and aesthetic
        6. Ensure the image could be used effectively for {campaign_type} marketing
        7. Do NOT include any text or words in the image itself
        
        Create a detailed image prompt (200-300 words) that describes exactly what this marketing image should contain.
        Focus on visual details, composition, mood, colors, and elements that would make this image effective for this specific customer.
        """,
        
        "fr": """
        Créez un prompt d'image détaillé pour une campagne marketing dans la niche {niche} ciblant {customer_name}.
        
        CONTEXTE DE LA CAMPAGNE:
        {campaign_description}
        
        PROFIL CLIENT:
        {customer_profile}
        
        INFORMATION SUR LA BOUTIQUE:
        {boutique_info}
        
        EXIGENCES D'IMAGE:
        1. Créez une image marketing vivante et professionnelle qui résonne avec ce client spécifique
        2. L'image doit représenter la niche {niche} de manière authentique et attrayante
        3. Concentrez-vous sur les éléments visuels qui attireraient ce client spécifique en fonction de son profil
        4. Incluez des produits, environnements ou éléments de style de vie pertinents qui correspondent à ses intérêts
        5. Le style de l'image doit correspondre à l'image de marque et à l'esthétique de la boutique
        6. Assurez-vous que l'image pourrait être utilisée efficacement pour le marketing {campaign_type}
        7. N'incluez PAS de texte ou de mots dans l'image elle-même
        
        Créez un prompt d'image détaillé (200-300 mots) qui décrit exactement ce que cette image marketing devrait contenir.
        Concentrez-vous sur les détails visuels, la composition, l'ambiance, les couleurs et les éléments qui rendraient cette image efficace pour ce client spécifique.
        """
    },
    
    # Prompts pour la génération d'attributs spécifiques à la niche
    "niche_attributes": {
        "en": """
        Based on this customer persona in the {niche} niche, create a JSON object with specialized attributes 
        specific to this niche and customer. Include:
        
        1. Preferred sub-categories within {niche}
        2. Ideal price range/budget for {niche} purchases
        3. Favorite brands or designers in the {niche} space
        4. Special requirements or preferences (sizes, materials, styles, etc.)
        5. Collection focus or themes they're building
        
        Persona summary:
        {persona_excerpt}
        
        Return ONLY a valid JSON object with these attributes. Example format:
        {
            "preferred_subcategories": ["example1", "example2"],
            "price_range": "Description of their budget level",
            "favorite_brands": ["brand1", "brand2"],
            "special_preferences": {
                "key1": "value1",
                "key2": "value2"
            },
            "collection_themes": ["theme1", "theme2"]
        }
        """,
        
        "fr": """
        Basé sur ce persona client dans la niche {niche}, créez un objet JSON avec des attributs spécialisés 
        spécifiques à cette niche et à ce client. Incluez:
        
        1. Sous-catégories préférées dans la niche {niche}
        2. Fourchette de prix/budget idéal pour les achats dans la niche {niche}
        3. Marques ou créateurs préférés dans l'espace de niche {niche}
        4. Exigences ou préférences spéciales (tailles, matériaux, styles, etc.)
        5. Thèmes ou focus de collection qu'ils développent
        
        Résumé du persona:
        {persona_excerpt}
        
        Retournez UNIQUEMENT un objet JSON valide avec ces attributs. Format d'exemple:
        {
            "sous_categories_preferees": ["exemple1", "exemple2"],
            "fourchette_prix": "Description de leur niveau de budget",
            "marques_preferees": ["marque1", "marque2"],
            "preferences_speciales": {
                "cle1": "valeur1",
                "cle2": "valeur2"
            },
            "themes_collection": ["theme1", "theme2"]
        }
        """
    },
    
    # Prompts pour la génération d'historique d'achat
    "purchase_history": {
        "en": """
        Based on this customer persona in the {niche} niche, create a JSON array of 3-5 products they have 
        purchased in the past. Each product should include:
        
        1. Product name
        2. Category
        3. Brand
        4. Price range
        5. When they purchased it (approximate date)
        6. Brief reason for purchase
        
        Persona summary:
        {persona_excerpt}
        
        Return ONLY a valid JSON array with these products. Example format:
        [
            {
                "name": "Product Name",
                "category": "Category",
                "brand": "Brand Name",
                "price": "$XX-$XXX",
                "purchase_date": "Month Year",
                "purchase_reason": "Brief reason"
            },
            ...
        ]
        """,
        
        "fr": """
        Basé sur ce persona client dans la niche {niche}, créez un tableau JSON de 3-5 produits qu'ils ont 
        achetés dans le passé. Chaque produit doit inclure:
        
        1. Nom du produit
        2. Catégorie
        3. Marque
        4. Fourchette de prix
        5. Quand ils l'ont acheté (date approximative)
        6. Brève raison de l'achat
        
        Résumé du persona:
        {persona_excerpt}
        
        Retournez UNIQUEMENT un tableau JSON valide avec ces produits. Format d'exemple:
        [
            {
                "nom": "Nom du Produit",
                "categorie": "Catégorie",
                "marque": "Nom de la Marque",
                "prix": "XX€-XXX€",
                "date_achat": "Mois Année",
                "raison_achat": "Raison brève"
            },
            ...
        ]
        """
    }
}

def get_translated_prompt(prompt_key, language=None, **kwargs):
    """
    Récupère un prompt traduit dans la langue spécifiée
    
    Args:
        prompt_key: Clé du prompt dans le dictionnaire PROMPT_TRANSLATIONS
        language: Code de langue (fr, en, etc.) ou None pour utiliser la langue active
        **kwargs: Variables à formater dans le template du prompt
        
    Returns:
        Prompt traduit et formaté
    """
    if language is None:
        language = get_prompt_language()
    
    # Fallback à l'anglais si la langue n'est pas supportée
    if language not in PROMPT_TRANSLATIONS.get(prompt_key, {}):
        language = 'en'
    
    prompt_template = PROMPT_TRANSLATIONS.get(prompt_key, {}).get(language, "")
    
    if not prompt_template:
        logger.warning(f"No translation found for prompt {prompt_key} in language {language}")
        # Fallback à l'anglais si aucune traduction n'est trouvée
        prompt_template = PROMPT_TRANSLATIONS.get(prompt_key, {}).get('en', "")
    
    # Formater le template avec les variables fournies
    try:
        return prompt_template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing key in prompt formatting: {e}")
        return prompt_template

# Initialize Grok client
grok_client = AsyncOpenAI(
    base_url="https://api.x.ai/v1", 
    api_key=os.environ.get("XAI_API_KEY")
)

# Initialize OpenAI client
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

def get_openai_client(api_key=None):
    """
    Get an OpenAI client instance
    
    Args:
        api_key: Optional API key to use instead of environment variable
        
    Returns:
        OpenAI client instance
    """
    if api_key:
        return OpenAI(api_key=api_key)
    return openai_client

def get_grok_client(api_key=None):
    """
    Get a Grok client instance
    
    Args:
        api_key: Optional API key to use instead of environment variable
        
    Returns:
        AsyncOpenAI client instance configured for X.AI API
    """
    if api_key:
        return AsyncOpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
    return grok_client

# Define data models for structured outputs
class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class Item(BaseModel):
    name: str
    category: str
    price: float
    purchase_date: str

class Customer(BaseModel):
    name: str
    age: int
    location: str
    country_code: Optional[str] = None
    gender: Gender
    language: str
    purchase_history: List[Item]
    interests: List[str]
    search_history: Dict[str, str]
    preferred_device: str
    income_level: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    social_media: Optional[Dict[str, str]] = None
    shopping_frequency: Optional[str] = None
    persona: Optional[str] = None

class Customers(BaseModel):
    customers: List[Customer]

# Enhanced prompt for generating boutique-specific customer profiles
async def generate_boutique_customers(
    client: AsyncOpenAI, 
    niche: str,
    niche_description: str,
    num_customers: int = 5, 
    model: str = GROK_3,
    target_country: str = "",
    age_range: str = "",
    income_level: str = ""
) -> Customers:
    # Préparer les contraintes de localisation
    location_constraint = ""
    if target_country:
        # Obtenir le nom du pays à partir du code
        country_name = ""
        if target_country == "US":
            country_name = "United States"
        elif target_country == "CA":
            country_name = "Canada"
        elif target_country == "GB":
            country_name = "United Kingdom"
        elif target_country == "FR":
            country_name = "France"
        elif target_country == "DE":
            country_name = "Germany"
        elif target_country == "IT":
            country_name = "Italy"
        elif target_country == "ES":
            country_name = "Spain"
        elif target_country == "JP":
            country_name = "Japan"
        elif target_country == "AU":
            country_name = "Australia"
        elif target_country == "BR":
            country_name = "Brazil"
        elif target_country == "IN":
            country_name = "India"
        elif target_country == "CN":
            country_name = "China"
        elif target_country == "MX":
            country_name = "Mexico"
        
        if country_name:
            location_constraint = f"All customers must be from {country_name}. Use cities and regions within {country_name}. Add the country code '{target_country}' at the end of location values."
    
    # Préparer les contraintes d'âge
    age_constraint = ""
    if age_range:
        age_constraint = f"All customers must have ages within the range: {age_range}."
    
    # Préparer les contraintes de niveau de revenu
    income_constraint = ""
    if income_level:
        income_description = ""
        if income_level == "budget":
            income_description = "budget-conscious, cost-sensitive, value-oriented"
        elif income_level == "middle":
            income_description = "middle income, average spending power"
        elif income_level == "affluent":
            income_description = "affluent, financially comfortable, higher disposable income"
        elif income_level == "luxury":
            income_description = "luxury consumers, high-end, premium buyers"
        
        if income_description:
            income_constraint = f"All customers should be {income_description} shoppers with income_level set to '{income_level}'."
    
    prompt = f"""
    Generate {num_customers} diverse and vibrant customer profiles for a boutique specializing in {niche}.
    Boutique description: {niche_description}
    
    CREATE HIGHLY UNIQUE PROFILES:
    - Ensure an even gender distribution (approximately 50/50)
    - Create a diverse age range (18-75+) with special focus on underrepresented age groups like seniors and young adults
    - Include diversity in education levels (from high school to doctorate)
    - Vary income levels (budget, middle, affluent, and luxury)
    - Create unique occupation combinations that challenge stereotypes
    - Invent distinctive shopping patterns and brand affinities
    - Generate creative interests that surprise but remain relevant to the niche
    
    The customers should have the following attributes:
    - name: str (create culturally diverse names representative of different ethnicities and backgrounds)
    - age: int (distribute across age ranges 18-25, 26-35, 36-45, 46-55, 56-65, 66-75, 76+)
    - location: str (use specific neighborhoods and cultural districts, not just city centers)
    - country_code: str (2-letter ISO code, e.g., 'US', 'FR', 'JP')
    - gender: Gender (MALE, FEMALE - ensure balanced distribution)
    - language: str (include primary language and secondary languages when appropriate)
    - purchase_history: list[Item] (range from first-time buyers to loyal customers with product progression stories)
    - interests: list[str] (include at least 5 specific, nuanced interests directly relevant to {niche})
    - search_history: dict[str, str] (reflect knowledge journey and discovery patterns unique to each customer)
    - preferred_device: str (consider age and lifestyle for realistic device preferences)
    - income_level: str (one of: 'budget', 'middle', 'affluent', 'luxury')
    - education: str (e.g., 'high school', 'bachelor', 'master', 'doctorate', 'self-taught', 'vocational training')
    - occupation: str (be creative and specific with job titles and sectors)
    - social_media: dict[str, str] (platform name and usage frequency - match to age and lifestyle realistically)
    - shopping_frequency: str (one of: 'rarely', 'occasionally', 'frequently', 'very frequently')

    For Item objects in purchase_history:
    - name: str (create distinctive, brand-specific product names that feel like real catalog items)
    - category: str (use specific product categories and subcategories relevant to {niche})
    - price: float (create realistic prices with appropriate variation and precision)
    - purchase_date: str (create purchase patterns over time, in YYYY-MM-DD format, most recent within the last 6 months)

    CRITICAL DIVERSITY REQUIREMENTS:
    - Customers must have deeply varied backstories and motivations 
    - Include surprising customer profiles that challenge traditional market assumptions
    - Create a rich spectrum of lifestyle patterns and value systems
    - Include customers with different levels of expertise in the {niche} area
    - Include unusual combinations of interests that still realistically connect to the {niche}
    - Have 70% of customers be in the target demographic for this niche, and 30% be potential new audiences
    {location_constraint}
    {age_constraint}
    {income_constraint}

    Please set the persona attribute to null for all customers.
    """

    try:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=Customers,
            temperature=1.1,
        )

        if not response.choices[0].message.parsed:
            raise ValueError("No customer profiles generated")

        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error generating boutique customers: {e}")
        raise

# Generate richly detailed persona for a customer profile
async def generate_enhanced_customer_data_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    existing_personas: list = None,
    boutique_info: dict = None,
    model: str = GROK_3
) -> dict:
    """
    Génère un persona client enrichi avec avatar et attributs spécifiques à la niche.
    Cette version améliorée assure une diversité entre les profils générés.
    
    Args:
        client: AsyncOpenAI client
        customer: Dictionnaire contenant les données client
        niche: Niche de marché
        existing_personas: Liste de personas existants pour éviter les répétitions
        model: Modèle Grok à utiliser
        
    Returns:
        Dictionnaire contenant le persona, l'URL de l'avatar et les attributs de niche
    """
    name = customer.get("name", "Unknown")
    age = customer.get("age", 0)
    location = customer.get("location", "Unknown")
    gender = customer.get("gender", "Unknown")
    language = customer.get("language", "English")
    interests = ", ".join(customer.get("interests", []))
    purchase_history = customer.get("purchase_history", [])
    
    # Format purchase history for prompt
    purchases = []
    for item in purchase_history:
        purchases.append(f"{item.get('name')} ({item.get('category')}) - ${item.get('price')}")
    purchase_str = "\n".join(purchases)
    
    # Fournir une liste des personas existants au modèle pour éviter la répétition
    existing_personas_summary = ""
    if existing_personas and len(existing_personas) > 0:
        existing_personas_summary = "ALREADY CREATED PERSONAS TO AVOID DUPLICATING (MAKE SURE TO CREATE SOMETHING COMPLETELY DIFFERENT):\n\n"
        for i, persona in enumerate(existing_personas[:3]):  # Limiter à 3 pour éviter un prompt trop long
            existing_personas_summary += f"Persona {i+1}:\n{persona[:200]}...\n\n"
    
    # Intégrer les informations de la boutique si disponibles
    boutique_context = ""
    if boutique_info and isinstance(boutique_info, dict):
        boutique_name = boutique_info.get("name", "")
        boutique_description = boutique_info.get("description", "")
        boutique_target = boutique_info.get("target_demographic", "")
        
        if boutique_name or boutique_description or boutique_target:
            boutique_context = f"""
            BOUTIQUE INFORMATION:
            Name: {boutique_name}
            Description: {boutique_description}
            Target Demographic: {boutique_target}
            
            SPECIAL REQUIREMENTS:
            - Create a persona that would be an ideal customer for this specific boutique
            - Align their interests and preferences with the boutique's offerings and style
            - Ensure the persona would be part of the target demographic while maintaining diversity
            - Include specific reasons why this person would be drawn to this boutique
            - Consider how the boutique's identity resonates with this customer's values
            """
    
    # Utiliser le système de prompts traduits
    prompt = get_translated_prompt(
        "customer_persona",
        name=name,
        age=age,
        gender=gender,
        location=location,
        niche=niche,
        interests=interests,
        purchases=purchase_str,
        existing_personas_summary=existing_personas_summary,
        boutique_context=boutique_context
    )
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # Augmenter la température pour plus de créativité
            max_tokens=800,
        )
        
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("No persona generated")
            
        persona_text = response.choices[0].message.content
        
        # Génération de l'avatar prompt avec le système de prompts traduits
        avatar_prompt = get_translated_prompt(
            "avatar_generation",
            name=name,
            age=age,
            gender=gender,
            location=location,
            interests=interests,
            niche=niche,
            persona_excerpt=persona_text[:200]
        )
        
        avatar_response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": avatar_prompt}],
            temperature=0.8,
            max_tokens=250,
        )
        
        avatar_text_prompt = avatar_response.choices[0].message.content
        
        # Génération des attributs spécifiques à la niche avec le système de prompts traduits
        niche_attributes_prompt = get_translated_prompt(
            "niche_attributes",
            niche=niche,
            persona_excerpt=persona_text[:300]
        )
        
        niche_attr_response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": niche_attributes_prompt}],
            temperature=0.7,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        niche_attributes = json.loads(niche_attr_response.choices[0].message.content)
        
        # Génération d'exemples de produits achetés avec le système de prompts traduits
        purchase_history_prompt = get_translated_prompt(
            "purchase_history",
            niche=niche,
            persona_excerpt=persona_text[:300]
        )
        
        purchase_response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": purchase_history_prompt}],
            temperature=0.7,
            max_tokens=600,
            response_format={"type": "json_object"}
        )
        
        purchased_products = json.loads(purchase_response.choices[0].message.content)
        
        return {
            "persona": persona_text,
            "avatar_prompt": avatar_text_prompt,
            "niche_attributes": niche_attributes,
            "purchased_products": purchased_products
        }
    except Exception as e:
        logger.error(f"Error generating enhanced customer data: {e}")
        raise

async def generate_customer_persona_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    boutique_id: int = None,
    model: str = GROK_3
) -> str:
    """
    Version simplifiée pour la compatibilité avec le code existant.
    Utilise la fonction enhanced et retourne uniquement le persona.
    
    Args:
        client: AsyncOpenAI client
        customer: Dictionnaire contenant les données client
        niche: Niche de marché
        boutique_id: ID de la boutique associée (optionnel)
        model: Modèle Grok à utiliser
        
    Returns:
        String contenant le persona généré
    """
    try:
        from models import Customer, Boutique
        from app import db
        
        # Récupérer tous les personas existants pour éviter la répétition
        existing_personas = []
        # Une requête SQL serait idéale, mais nous éviterons les dépendances de DB ici
        # et laissons cette partie vide pour l'instant
        
        # Récupérer les informations de la boutique si disponibles
        boutique_info = None
        if boutique_id:
            try:
                boutique = Boutique.query.get(boutique_id)
                if boutique:
                    boutique_info = {
                        "name": boutique.name,
                        "description": boutique.description,
                        "target_demographic": boutique.target_demographic
                    }
            except Exception as boutique_err:
                logger.warning(f"Could not retrieve boutique information: {boutique_err}")
        
        # Si le customer a une boutique_id, récupérer cette boutique
        if not boutique_info and isinstance(customer, dict) and customer.get('boutique_id'):
            try:
                boutique = Boutique.query.get(customer.get('boutique_id'))
                if boutique:
                    boutique_info = {
                        "name": boutique.name,
                        "description": boutique.description,
                        "target_demographic": boutique.target_demographic
                    }
            except Exception as boutique_err:
                logger.warning(f"Could not retrieve boutique information from customer: {boutique_err}")
        
        enhanced_data = await generate_enhanced_customer_data_async(
            client=client,
            customer=customer,
            niche=niche,
            existing_personas=existing_personas,
            boutique_info=boutique_info,
            model=model
        )
        
        # Mise à jour du customer avec les nouvelles données
        if isinstance(customer, dict) and 'id' in customer:
            # Si nous sommes dans un contexte où nous pouvons mettre à jour le modèle Customer
            try:
                # Tentons de mettre à jour les attributs additionnels
                from app import db
                
                customer_id = customer.get('id')
                if customer_id:
                    customer_obj = Customer.query.get(customer_id)
                    if customer_obj:
                        customer_obj.purchased_products = enhanced_data.get('purchased_products')
                        customer_obj.niche_attributes = enhanced_data.get('niche_attributes')
                        # L'avatar_url sera mis à jour séparément après génération de l'image
                        db.session.commit()
            except Exception as update_err:
                logger.warning(f"Could not update additional customer attributes: {update_err}")
        
        return enhanced_data["persona"]
    except Exception as e:
        logger.error(f"Error in generate_customer_persona_async: {e}")
        raise

# Generate boutique-specific marketing content for a customer
async def generate_boutique_marketing_content_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    campaign_type: str,
    boutique_info: dict = None,
    model: str = GROK_3
) -> str:
    """
    Génère du contenu marketing personnalisé pour un client spécifique en tenant compte
    des informations de la boutique.
    
    Args:
        client: AsyncOpenAI client
        customer: Dictionnaire contenant les données client
        niche: Niche de marché
        campaign_type: Type de campagne (email, social, sms, ad, product_description)
        boutique_info: Informations sur la boutique (optionnel)
        model: Modèle Grok à utiliser
        
    Returns:
        String contenant le contenu marketing généré
    """
    # Extract customer data for personalization
    name = customer.get("name", "valued customer")
    language = customer.get("language", "English")
    interests = ", ".join(customer.get("interests", []))
    persona = customer.get("persona", "")
    
    # Récupérer les informations de la boutique si le customer est lié à une boutique
    if not boutique_info and isinstance(customer, dict) and customer.get('boutique_id'):
        try:
            from models import Boutique
            boutique = Boutique.query.get(customer.get('boutique_id'))
            if boutique:
                boutique_info = {
                    "name": boutique.name,
                    "description": boutique.description,
                    "target_demographic": boutique.target_demographic
                }
        except Exception as boutique_err:
            logger.warning(f"Could not retrieve boutique information from customer: {boutique_err}")
    
    # Préparer le contexte de la boutique pour le prompt
    boutique_context = ""
    if boutique_info and isinstance(boutique_info, dict):
        boutique_name = boutique_info.get("name", "")
        boutique_description = boutique_info.get("description", "")
        boutique_target = boutique_info.get("target_demographic", "")
        
        if boutique_name or boutique_description or boutique_target:
            boutique_context = f"""
            BOUTIQUE INFORMATION:
            Name: {boutique_name}
            Description: {boutique_description}
            Target Demographic: {boutique_target}
            
            SPECIAL REQUIREMENTS:
            - Incorporate the boutique's unique identity and values into the content
            - Reference the boutique's specific products, style, or offerings
            - Ensure the tone matches the boutique's brand voice
            - Create a natural connection between the customer's needs and the boutique's offerings
            """
    
    # Determine the appropriate content type based on campaign
    content_type_map = {
        "email": "marketing email",
        "social": "social media post",
        "sms": "SMS message",
        "ad": "online advertisement",
        "product_description": "product description"
    }
    content_type = content_type_map.get(campaign_type, "marketing content")
    
    # Utiliser le système de prompts traduits pour le contenu marketing
    prompt = get_translated_prompt(
        "marketing_content",
        name=name,
        persona=persona,
        campaign_type=campaign_type,
        niche=niche,
        interests=interests,
        language=language,
        boutique_context=boutique_context
    )
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=1000,
        )
        
        if not response.choices or not response.choices[0].message.content:
            raise ValueError(f"No {content_type} generated")
            
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating marketing content: {e}")
        raise

# Generate a prompt for creating boutique-specific marketing images
async def generate_image_prompt_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    base_prompt: str,
    boutique_info: dict = None,
    model: str = GROK_3
) -> dict:
    """
    Génère un prompt optimisé pour la création d'images marketing ciblées et SEO-friendly
    
    Args:
        client: AsyncOpenAI client
        customer: Dictionnaire contenant les données client
        niche: Niche de marché
        base_prompt: Prompt de base fourni par l'utilisateur
        model: Modèle Grok à utiliser
        
    Returns:
        Dictionnaire contenant le prompt optimisé, les mots-clés SEO et d'autres métadonnées
    """
    interests = ", ".join(customer.get("interests", []))
    persona = customer.get("persona", "")
    location = customer.get("location", "")
    age = customer.get("age", "")
    
    # Récupérer les informations de la boutique si le customer est lié à une boutique
    if not boutique_info and isinstance(customer, dict) and customer.get('boutique_id'):
        try:
            from models import Boutique
            boutique = Boutique.query.get(customer.get('boutique_id'))
            if boutique:
                boutique_info = {
                    "name": boutique.name,
                    "description": boutique.description,
                    "target_demographic": boutique.target_demographic
                }
        except Exception as boutique_err:
            logger.warning(f"Could not retrieve boutique information from customer: {boutique_err}")
    
    # Préparer le contexte de la boutique pour le prompt
    boutique_context = ""
    if boutique_info and isinstance(boutique_info, dict):
        boutique_name = boutique_info.get("name", "")
        boutique_description = boutique_info.get("description", "")
        boutique_target = boutique_info.get("target_demographic", "")
        
        if boutique_name or boutique_description or boutique_target:
            boutique_context = f"""
            BOUTIQUE BRANDING:
            Name: {boutique_name}
            Description: {boutique_description}
            Target Demographic: {boutique_target}
            
            BRAND CONSISTENCY REQUIREMENTS:
            - Incorporate the boutique's visual identity and aesthetic into the image
            - Use colors, textures and styles that align with the boutique's brand
            - Ensure the image clearly represents the boutique's market positioning
            - Create visual elements that support the boutique's specific value proposition
            """
    
    # Extraction des mots-clés pertinents pour le SEO
    keywords = [niche]
    if interests:
        keywords.extend([interest.strip() for interest in interests.split(',')[:3]])
    if boutique_info and boutique_info.get("name"):
        keywords.append(boutique_info.get("name"))
    
    # Utiliser le système de prompts traduits pour la génération d'image
    meta_prompt = get_translated_prompt(
        "campaign_image",
        niche=niche,
        customer_name=customer.get("name", ""),
        campaign_description=base_prompt,
        customer_profile=f"Interests: {interests}, Location: {location}, Age: {age}, Persona: {persona[:250]}...",
        boutique_info=boutique_context,
        campaign_type=customer.get("campaign_type", "marketing")
    )
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.8,
            max_tokens=700,
            response_format={"type": "json_object"}
        )
        
        if not response.choices or not response.choices[0].message.content:
            return {"prompt": base_prompt, "keywords": keywords}
        
        try:
            # Tenter de parser le JSON retourné
            import json
            result = json.loads(response.choices[0].message.content)
            
            # S'assurer que toutes les clés nécessaires sont présentes
            if "prompt" not in result:
                result["prompt"] = base_prompt
            if "keywords" not in result:
                result["keywords"] = keywords
            if "alt_text" not in result:
                result["alt_text"] = f"{niche} marketing image for {customer.get('name', 'customer')}"
            if "image_title" not in result:
                result["image_title"] = f"{niche} - {base_prompt[:30]}..."
            if "description" not in result:
                result["description"] = f"Custom {niche} marketing image tailored for {customer.get('name', 'customers')} with interests in {interests}"
                
            return result
        except json.JSONDecodeError:
            # Si le JSON est invalide, extraire le prompt du texte brut
            content = response.choices[0].message.content
            return {
                "prompt": content,
                "keywords": keywords,
                "alt_text": f"{niche} marketing image",
                "image_title": f"{niche} - {base_prompt[:30]}...",
                "description": f"Custom {niche} marketing image"
            }
    except Exception as e:
        logger.error(f"Error generating image prompt: {e}")
        return {
            "prompt": base_prompt,
            "keywords": keywords,
            "alt_text": f"{niche} marketing image",
            "image_title": f"{niche} - {base_prompt[:30]}...",
            "description": f"Custom {niche} marketing image"
        }

# Generate boutique-specific marketing image
async def generate_boutique_image_async(
    client: AsyncOpenAI,
    image_prompt: str,
    model: str = GROK_2_IMAGE,
    image_data=None,
    style=None
) -> str:
    """
    Generate a marketing image with Grok's image generation model.
    
    Args:
        client: AsyncOpenAI client
        image_prompt: Text prompt for image generation
        model: Grok model to use
        image_data: Optional base64 encoded image data to use as a starting point
        style: Optional style to apply to the image (e.g., 'watercolor', 'photorealistic')
    
    Returns:
        URL of the generated image
    """
    try:
        # Nettoyer et limiter le prompt
        max_prompt_length = 900  # Laissons une marge
        if len(image_prompt) > max_prompt_length:
            logger.warning(f"Image prompt too long ({len(image_prompt)} chars). Truncating to {max_prompt_length} chars.")
            image_prompt = image_prompt[:max_prompt_length] + "..."
        
        # Filtrer les contenus potentiellement problématiques
        def sanitize_prompt(prompt):
            # Liste de termes qui pourraient être rejetés par les filtres de contenu
            sensitive_terms = [
                "naked", "nude", "violence", "gore", "blood", "injury", "sexual", 
                "illegal", "weapon", "drug", "controversial", "political"
            ]
            filtered_prompt = prompt
            for term in sensitive_terms:
                if term.lower() in prompt.lower():
                    filtered_prompt = filtered_prompt.replace(term, "suitable")
            return filtered_prompt
            
        # Sanitize the prompt
        image_prompt = sanitize_prompt(image_prompt)
        
        # Ajouter un préfixe de qualité pour l'image
        image_prefix = "Professional, high-quality image of "
        
        # Prepare prompt with style if specified
        final_prompt = f"{image_prefix}{image_prompt}"
        if style:
            if style == "watercolor":
                final_prompt = f"A beautiful watercolor painting of {image_prompt}, artistic style, soft colors, elegant"
            elif style == "oil_painting":
                final_prompt = f"An oil painting of {image_prompt}, classic style, rich textures, detailed"
            elif style == "photorealistic":
                final_prompt = f"Photorealistic image of {image_prompt}, high definition, detailed, professional photography"
            elif style == "sketch":
                final_prompt = f"A detailed sketch drawing of {image_prompt}, pencil lines, artistic, black and white"
            elif style == "anime":
                final_prompt = f"Anime style illustration of {image_prompt}, clean lines, vibrant colors"
            elif style == "3d_render":
                final_prompt = f"3D render of {image_prompt}, clean lighting, professional, detailed textures"
            elif style == "minimalist":
                final_prompt = f"Minimalist design of {image_prompt}, clean lines, simple colors, elegant"
            elif style == "pop_art":
                final_prompt = f"Pop art style illustration of {image_prompt}, bright colors, bold patterns"
            else:
                final_prompt = f"{image_prefix}{image_prompt} in {style} style"
        
        logger.info(f"Final image prompt: {final_prompt[:100]}...")
        
        # Try using Grok model first (preferred)
        try:
            logger.info(f"Attempting to generate image with Grok model: {model}")
            
            # Use Grok client with the correct implementation for image generation
            XAI_API_KEY = os.environ.get("XAI_API_KEY")
            xai_client = OpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)
            
            # Utiliser la nouvelle méthode correcte pour la génération d'images avec xAI
            response = xai_client.images.generate(
                model="grok-2-image-1212",  # Utiliser grok-2-image-1212 qui est le modèle d'image recommandé
                prompt=final_prompt,
                n=1
                # Suppression du paramètre size qui n'est pas supporté par xAI
            )
            
            # Extraire l'URL de l'image de la réponse
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                if image_url:
                    logger.info("Successfully generated image with Grok")
                    return image_url
            
            # Si nous arrivons ici, Grok n'a pas produit d'URL d'image valide
            logger.warning("Grok didn't return a valid image URL, falling back to OpenAI")
        except Exception as grok_error:
            logger.error(f"Grok image generation failed: {grok_error}")
            logger.warning("Falling back to OpenAI for image generation")
            
        # Fallback to OpenAI
        try:
            # Use OpenAI client instead for image generation
            openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Try with DALL-E 2 first (more reliable)
            response = openai_client.images.generate(
                model="dall-e-2",
                prompt=final_prompt,
                n=1,
                size="1024x1024"
            )
            
            # Extract the URL from the response
            if response.data and len(response.data) > 0 and hasattr(response.data[0], 'url'):
                logger.info("Successfully generated image with DALL-E 2")
                return response.data[0].url
                
        except Exception as first_attempt_error:
            logger.warning(f"OpenAI DALL-E 2 image generation failed: {first_attempt_error}")
            # Final fallback to a simpler prompt
            try:
                # Create a very simple prompt as fallback
                simple_prompt = f"A simple professional image of {image_prompt}"
                
                response = openai_client.images.generate(
                    model="dall-e-2",
                    prompt=simple_prompt,
                    n=1,
                    size="1024x1024"
                )
                
                if response.data and len(response.data) > 0 and hasattr(response.data[0], 'url'):
                    logger.info("Successfully generated image with simplified prompt")
                    return response.data[0].url
                else:
                    raise ValueError("No image generated from OpenAI API (final attempt)")
            except Exception as second_attempt_error:
                logger.error(f"Final image generation attempt failed: {second_attempt_error}")
                raise Exception(f"All image generation attempts failed: {second_attempt_error}")
        
        raise ValueError("Failed to generate image with any available method")
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        # Return a placeholder image URL for development
        return "https://placehold.co/600x400/grey/white?text=Image+Generation+Failed"

# Synchronous wrapper functions for async functions

def generate_customers(niche, niche_description, num_customers=5, generation_params=None):
    """
    Generate customer profiles for a specific boutique niche with optional parameters
    
    Args:
        niche: The niche market name
        niche_description: Description of the niche market
        num_customers: Number of customer profiles to generate
        generation_params: Optional dictionary of parameters including:
            - target_country: ISO country code to focus customers on (e.g., 'US', 'FR')
            - age_range: Age range for customers (e.g., '18-25', '26-35')
            - income_level: Income level bracket (e.g., 'budget', 'affluent')
    
    Returns:
        List of customer profile dictionaries
    """
    if generation_params is None:
        generation_params = {}
    
    # Créer une nouvelle boucle d'événements pour éviter les conflits avec d'autres boucles
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Exécuter la fonction asynchrone avec un timeout de 30 secondes pour éviter les blocages
        customers_obj = loop.run_until_complete(asyncio.wait_for(
            generate_boutique_customers(
                grok_client, 
                niche, 
                niche_description, 
                num_customers,
                target_country=generation_params.get('target_country', ''),
                age_range=generation_params.get('age_range', ''),
                income_level=generation_params.get('income_level', '')
            ), 
            timeout=30.0
        ))
        
        # Convert to a list of dictionaries for JSON serialization
        return [customer.dict() for customer in customers_obj.customers]
    except asyncio.TimeoutError:
        # En cas de timeout, retourner un message d'erreur lisible
        logging.error(f"Timeout lors de la génération des profils clients pour {niche}")
        # Retourner un tableau vide pour éviter les erreurs
        return []
    except Exception as e:
        # Gérer les autres exceptions
        logging.error(f"Erreur lors de la génération des profils clients: {str(e)}")
        return []
    finally:
        # Toujours fermer la boucle pour éviter les fuites de ressources
        loop.close()

def generate_customer_persona(customer, boutique_id=None):
    """
    Generate a detailed persona for a customer profile
    
    Args:
        customer: Customer data dict
        boutique_id: Optional ID of the boutique to use for context
    
    Returns:
        String containing the generated persona
    """
    import logging
    
    niche = ""  # Extract from interests or other attributes
    if customer.get("interests"):
        niche = customer["interests"][0]  # Use first interest as niche if not specified
    
    # Créer une nouvelle boucle d'événements
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Exécuter la fonction asynchrone avec un timeout
        return loop.run_until_complete(asyncio.wait_for(
            generate_customer_persona_async(grok_client, customer, niche, boutique_id),
            timeout=20.0
        ))
    except asyncio.TimeoutError:
        logging.error(f"Timeout lors de la génération du persona pour {customer.get('name', 'client inconnu')}")
        return "Impossible de générer un persona en raison d'un délai d'attente dépassé. Veuillez réessayer."
    except Exception as e:
        logging.error(f"Erreur lors de la génération du persona: {str(e)}")
        return f"Erreur lors de la génération du persona: {str(e)}"
    finally:
        loop.close()

def generate_marketing_content(customer, campaign_type, boutique_id=None):
    """
    Generate personalized marketing content for a customer
    
    Args:
        customer: Customer data dict
        campaign_type: Type of marketing campaign (email, social, sms, etc.)
        boutique_id: Optional ID of the boutique to use for context
        
    Returns:
        String containing the generated marketing content
    """
    import logging
    
    niche = ""
    if customer.get("interests"):
        niche = customer["interests"][0]
    
    # Récupérer les informations de la boutique si un ID est fourni
    boutique_info = None
    if boutique_id:
        try:
            from models import Boutique
            boutique = Boutique.query.get(boutique_id)
            if boutique:
                boutique_info = {
                    "name": boutique.name,
                    "description": boutique.description,
                    "target_demographic": boutique.target_demographic
                }
                logging.info(f"Using boutique information from boutique_id: {boutique.name}")
        except Exception as boutique_err:
            logging.warning(f"Could not retrieve boutique information: {boutique_err}")
    
    # Si le client est associé à une boutique, utiliser cette information
    if not boutique_info and customer.get("boutique_id"):
        try:
            from models import Boutique
            boutique = Boutique.query.get(customer.get("boutique_id"))
            if boutique:
                boutique_info = {
                    "name": boutique.name,
                    "description": boutique.description,
                    "target_demographic": boutique.target_demographic
                }
                logging.info(f"Using boutique information from customer association: {boutique.name}")
        except Exception as boutique_err:
            logging.warning(f"Could not retrieve boutique information from customer: {boutique_err}")
    
    # Créer une nouvelle boucle d'événements
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Exécuter la fonction asynchrone avec un timeout
        return loop.run_until_complete(asyncio.wait_for(
            generate_boutique_marketing_content_async(
                grok_client,
                customer,
                niche,
                campaign_type,
                boutique_info=boutique_info
            ),
            timeout=25.0
        ))
    except asyncio.TimeoutError:
        logging.error(f"Timeout lors de la génération du contenu marketing pour {customer.get('name', 'client inconnu')}")
        return "Impossible de générer du contenu marketing en raison d'un délai d'attente dépassé. Veuillez réessayer."
    except Exception as e:
        logging.error(f"Erreur lors de la génération du contenu marketing: {str(e)}")
        return f"Erreur lors de la génération du contenu marketing: {str(e)}"
    finally:
        loop.close()

def generate_image_prompt_from_content(campaign_content, campaign_type, customer_profile=None):
    """
    Generate an optimized image prompt based on campaign content and customer profile
    
    Args:
        campaign_content: Text content of the campaign
        campaign_type: Type of campaign (email, social, sms, ad)
        customer_profile: Optional customer profile data
    
    Returns:
        Optimized image prompt string
    """
    # Extraire des éléments clés du contenu
    content_sample = campaign_content[:500]  # Limiter pour éviter les prompts trop longs
    
    # Définir un style visuel basé sur le type de campagne
    style_map = {
        "email": "professional, clean layout, subtle colors",
        "social": "vibrant, eye-catching, social media optimized",
        "sms": "simple, direct, clear messaging",
        "ad": "polished, conversion-focused, professional",
        "product": "product-centered, detailed, e-commerce ready"
    }
    
    style = style_map.get(campaign_type, "marketing optimized")
    
    # Construire le prompt de base
    base_prompt = f"Create a high-quality {campaign_type} marketing image that conveys: {content_sample[:100]}... "
    base_prompt += f"Style: {style}. "
    
    # Ajouter des détails du profil client si disponible
    if customer_profile:
        # Ajouter des éléments démographiques si disponibles
        if customer_profile.get('age'):
            age_group = "young" if customer_profile.get('age', 30) < 30 else "mature" if customer_profile.get('age', 30) < 50 else "senior"
            base_prompt += f"Target audience: {age_group} "
            
        if customer_profile.get('gender'):
            base_prompt += f"{customer_profile.get('gender')} "
            
        # Ajouter des intérêts si disponibles
        if customer_profile.get('interests') and len(customer_profile.get('interests', [])) > 0:
            interests = ", ".join(customer_profile.get('interests', [])[:3])
            base_prompt += f"interested in {interests}. "
    
    # Optimisation pour les moteurs de recherche
    base_prompt += "The image should be optimized for marketing effectiveness with good composition and professional appearance."
    
    return base_prompt

def generate_marketing_image(customer, base_prompt, image_data=None, style=None, boutique_id=None):
    """
    Generate a personalized marketing image for a customer with SEO optimization
    
    Args:
        customer: Customer data dict
        base_prompt: Base text prompt for image generation
        image_data: Optional base64 encoded image data
        style: Optional style to apply (watercolor, oil painting, photorealistic, etc)
        boutique_id: Optional ID of the boutique for branding consistency
        
    Returns:
        Dictionary with image URL and SEO metadata (or just URL string for backward compatibility)
    """
    import os
    import logging
    import time
    from openai import OpenAI
    
    try:
        # Extraire le créneau de marché à partir des intérêts du client, si disponible
        niche = ""
        if customer.get("interests") and len(customer["interests"]) > 0:
            niche = customer["interests"][0]
        
        # Récupérer les informations de la boutique si un ID est fourni
        boutique_info = None
        if boutique_id:
            try:
                from models import Boutique
                boutique = Boutique.query.get(boutique_id)
                if boutique:
                    boutique_info = {
                        "name": boutique.name,
                        "description": boutique.description,
                        "target_demographic": boutique.target_demographic
                    }
                    logging.info(f"Using boutique information from boutique_id: {boutique.name}")
            except Exception as boutique_err:
                logging.warning(f"Could not retrieve boutique information: {boutique_err}")
        
        # Si le client est associé à une boutique, utiliser cette information
        if not boutique_info and customer.get("boutique_id"):
            try:
                from models import Boutique
                boutique = Boutique.query.get(customer.get("boutique_id"))
                if boutique:
                    boutique_info = {
                        "name": boutique.name,
                        "description": boutique.description,
                        "target_demographic": boutique.target_demographic
                    }
                    logging.info(f"Using boutique information from customer association: {boutique.name}")
            except Exception as boutique_err:
                logging.warning(f"Could not retrieve boutique information from customer: {boutique_err}")
        
        # Générer un prompt optimisé et des métadonnées SEO
        try:
            # Créer une nouvelle boucle d'événements pour la génération du prompt
            prompt_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(prompt_loop)
            
            try:
                # Exécuter avec un timeout pour éviter les blocages
                prompt_data = prompt_loop.run_until_complete(asyncio.wait_for(
                    generate_image_prompt_async(
                        grok_client, 
                        customer, 
                        niche, 
                        base_prompt,
                        boutique_info=boutique_info
                    ),
                    timeout=15.0
                ))
                
                # Extraire le prompt et les métadonnées
                if isinstance(prompt_data, dict) and "prompt" in prompt_data:
                    enhanced_prompt = prompt_data["prompt"]
                    seo_metadata = {
                        "keywords": prompt_data.get("keywords", [niche]),
                        "alt_text": prompt_data.get("alt_text", f"{niche} marketing image"),
                        "image_title": prompt_data.get("image_title", f"{niche} - {base_prompt[:30]}..."),
                        "description": prompt_data.get("description", f"Custom {niche} marketing image")
                    }
                else:
                    enhanced_prompt = prompt_data if isinstance(prompt_data, str) else base_prompt
                    seo_metadata = {
                        "keywords": [niche],
                        "alt_text": f"{niche} marketing image",
                        "image_title": f"{niche} - {base_prompt[:30]}...",
                        "description": f"Custom {niche} marketing image"
                    }
            except asyncio.TimeoutError:
                logging.warning("Timeout lors de l'amélioration du prompt, utilisation du prompt de base")
                enhanced_prompt = base_prompt
                seo_metadata = {
                    "keywords": [niche],
                    "alt_text": f"{niche} marketing image",
                    "image_title": f"{niche} - {base_prompt[:30]}...",
                    "description": f"Custom {niche} marketing image"
                }
            except Exception as e:
                logging.warning(f"Could not enhance prompt: {e}, using base prompt instead")
                enhanced_prompt = base_prompt
                seo_metadata = {
                    "keywords": [niche],
                    "alt_text": f"{niche} marketing image",
                    "image_title": f"{niche} - {base_prompt[:30]}...",
                    "description": f"Custom {niche} marketing image"
                }
            finally:
                prompt_loop.close()
        except Exception as e:
            logging.warning(f"Erreur lors de la configuration de la boucle asyncio: {e}, utilisation du prompt de base")
            enhanced_prompt = base_prompt
            seo_metadata = {
                "keywords": [niche],
                "alt_text": f"{niche} marketing image",
                "image_title": f"{niche} - {base_prompt[:30]}...",
                "description": f"Custom {niche} marketing image"
            }
        
        # Ajouter le style au prompt si spécifié
        final_prompt = enhanced_prompt
        if style:
            final_prompt = f"{enhanced_prompt} Style: {style}."
            
        # Si des données d'image sont fournies, mentionner cela dans le prompt
        if image_data:
            final_prompt = f"{final_prompt} Based on the provided reference image."
            
        # Utiliser xAI (Grok) pour la génération d'images
        # Créer un client OpenAI configuré pour xAI
        xai_client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=os.environ.get("XAI_API_KEY")
        )
        
        # Ajouter des éléments SEO supplémentaires au prompt final
        seo_enhanced_prompt = f"{final_prompt} The image should be clear and distinct with good product visibility optimized for online marketing."
        
        # Génération de l'image avec des tentatives de récupération en cas d'échec
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Utiliser xAI pour la génération d'images via l'interface de chat completions
                response = xai_client.chat.completions.create(
                    model="grok-2-vision-1212",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Generate an image based on this prompt: {seo_enhanced_prompt}"
                                }
                            ]
                        }
                    ]
                )
                
                # Extraire l'URL de l'image de la réponse
                # Le modèle Grok ne retourne pas directement une URL d'image, mais un message texte
                # Pour obtenir des images, on doit utiliser un service tiers pour convertir le texte en image
                # Pour le moment, utilisons un placeholder pour la démonstration
                
                # On vérifie si la réponse contient un message
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    # Pour les besoins de la démonstration, nous utiliserons un service placeholder
                    # Dans une implémentation réelle, vous devriez soit:
                    # 1. Utiliser un service tiers qui convertit des prompts en images
                    # 2. Utiliser directement DALL-E via OpenAI
                    
                    # Créer une URL d'image placeholder avec un texte court et très visible
                    import urllib.parse
                    
                    # Extraire juste quelques mots-clés pour une meilleure lisibilité
                    keywords = " ".join(seo_enhanced_prompt.split()[:5]) + "..."
                    encoded_prompt = urllib.parse.quote(keywords.replace(" ", "+"))
                    
                    # Utiliser un fond noir avec du texte jaune pour un contraste maximal et une taille plus grande
                    image_url = f"https://placehold.co/1024x1024/000000/FFEB3B?text={encoded_prompt}"
                    
                    # Dans une version production, vous pourriez vouloir utiliser DALL-E comme fallback
                    # si le modèle Grok ne génère pas correctement d'images
                    
                    # Construction du nom de fichier SEO-friendly
                    timestamp = int(time.time())
                    name_part = customer.get("name", "customer").lower().replace(" ", "-")
                    niche_part = niche.lower().replace(" ", "-")
                    image_filename = f"{niche_part}-{name_part}-{timestamp}.png"
                    
                    # Ajouter toutes les métadonnées dans un dictionnaire
                    result = {
                        "url": image_url,
                        "filename": image_filename,
                        "alt_text": seo_metadata["alt_text"],
                        "title": seo_metadata["image_title"],
                        "description": seo_metadata["description"],
                        "keywords": seo_metadata["keywords"],
                        "prompt": enhanced_prompt
                    }
                    
                    # Pour la compatibilité avec le code existant, retourner uniquement l'URL
                    # Cette ligne peut être modifiée si le code appelant est mis à jour pour utiliser les métadonnées
                    return image_url
                else:
                    logging.error("No image URL in OpenAI response")
                    retry_count += 1
                    if retry_count <= max_retries:
                        logging.info(f"Retrying image generation (attempt {retry_count}/{max_retries})...")
                        time.sleep(2)  # Attendre avant de réessayer
                    else:
                        return "https://placehold.co/800x800/FF0000/FFFFFF?text=Echec+de+génération+d'image"
            except Exception as e:
                logging.error(f"Error generating image on attempt {retry_count+1}: {e}")
                retry_count += 1
                if retry_count <= max_retries:
                    logging.info(f"Retrying image generation (attempt {retry_count}/{max_retries})...")
                    time.sleep(2)  # Attendre avant de réessayer
                else:
                    return "https://placehold.co/800x800/FF0000/FFFFFF?text=Echec+de+génération+d'image"
    except Exception as e:
        logging.error(f"Error in overall image generation process: {e}")
        return "https://placehold.co/800x800/FF0000/FFFFFF?text=Echec+de+génération+d'image"
