import os
import json
import asyncio
import logging
from openai import AsyncOpenAI
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Grok model constants
GROK_3 = "grok-3-fast"
GROK_2_IMAGE = "grok-2-image"

# Initialize Grok client
grok_client = AsyncOpenAI(
    base_url="https://api.x.ai/v1", 
    api_key=os.environ.get("XAI_API_KEY")
)

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
async def generate_customer_persona_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    model: str = GROK_3
) -> str:
    # Extract customer data for prompt
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
    
    # Craft a creative and vibrant boutique-specific persona generation prompt
    prompt = f"""
    Create an extraordinarily vivid and multi-dimensional persona for a {niche} boutique customer with these specific characteristics:
    
    Name: {name}
    Age: {age}
    Location: {location}
    Gender: {gender}
    Language: {language}
    Interests: {interests}
    
    Purchase History:
    {purchase_str}
    
    PERSONA GENERATION REQUIREMENTS:
    
    1. PSYCHOLOGICAL DIMENSION
       - Craft a unique psychological profile with distinctive personality traits
       - Create specific emotional triggers and sensitivities related to {niche}
       - Develop nuanced motivational drives beyond obvious ones
       - Include surprising psychological insights that defy stereotypical assumptions
    
    2. LIFESTYLE PORTRAIT
       - Paint a detailed picture of their daily rituals and routines
       - Describe their home environment and personal aesthetic in vivid detail
       - Illustrate their social circles and relationships as they relate to {niche}
       - Include specific challenges or pain points in their lifestyle
    
    3. SHOPPING PSYCHOLOGY
       - Explain their discovery process for new products
       - Detail how they evaluate quality and value in the {niche} space
       - Describe their emotional relationship with purchasing decisions
       - Illustrate their post-purchase behavior and satisfaction patterns
    
    4. CONTENT & MARKETING PREFERENCES  
       - Identify specific media channels where they spend time
       - Note their sensitivity to different marketing approaches (humor, emotion, data)
       - Detail the aesthetic styles and visual language that attracts them
       - Explain how they prefer to receive communication (tone, format, frequency)
    
    5. RELATIONSHIP WITH THE NICHE
       - Create a compelling backstory for how they discovered this niche
       - Describe their level of expertise and confidence in the {niche} market
       - Detail their aspirational goals related to the {niche}
       - Include specific frustrations or unmet needs within the {niche} space
    
    Write in second person as if you're directly describing the customer to the boutique owner.
    The persona should be 3-4 paragraphs long, vibrant and specific, with memorable details.
    Avoid generic descriptions - make this person feel utterly unique and immediately recognizable.
    """
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=800,
        )
        
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("No persona generated")
            
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating customer persona: {e}")
        raise

# Generate boutique-specific marketing content for a customer
async def generate_boutique_marketing_content_async(
    client: AsyncOpenAI,
    customer: dict,
    niche: str,
    campaign_type: str,
    model: str = GROK_3
) -> str:
    # Extract customer data for personalization
    name = customer.get("name", "valued customer")
    language = customer.get("language", "English")
    interests = ", ".join(customer.get("interests", []))
    persona = customer.get("persona", "")
    
    # Determine the appropriate content type based on campaign
    content_type_map = {
        "email": "marketing email",
        "social": "social media post",
        "sms": "SMS message",
        "ad": "online advertisement",
        "product_description": "product description"
    }
    content_type = content_type_map.get(campaign_type, "marketing content")
    
    # Create a boutique-specific marketing prompt
    prompt = f"""
    Create a highly personalized {content_type} for a {niche} boutique targeted at this specific customer:
    
    Customer Name: {name}
    Language: {language}
    Interests: {interests}
    
    Customer Persona:
    {persona}
    
    Your task:
    1. Write the {content_type} in {language} language
    2. Make it feel personally crafted for this specific customer
    3. Reference their interests and shopping preferences
    4. Incorporate elements specific to the {niche} niche
    5. Use language, tone, and references that would resonate with this customer
    6. Include a compelling call-to-action relevant to this customer
    
    The content should be authentic, emotionally resonant, and make the customer feel understood.
    """
    
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
    
    # Extraction des mots-clés pertinents pour le SEO
    keywords = [niche]
    if interests:
        keywords.extend([interest.strip() for interest in interests.split(',')[:3]])
    
    meta_prompt = f"""
    Create an extraordinarily rich and vivid image generation prompt for a {niche} boutique marketing visual optimized for SEO and targeted marketing.
    
    STARTING CONCEPT: {base_prompt}
    
    CUSTOMER PROFILE:
    - Interests: {interests}
    - Location: {location}
    - Age: {age}
    - Persona Insights: {persona[:250]}...
    
    VISUAL STORYTELLING REQUIREMENTS:
    
    1. AESTHETIC ALIGNMENT
       - Identify a specific visual style that would deeply resonate with this customer's taste profile
       - Consider cultural references from their background and interests
       - Suggest a distinctive color palette that captures their emotional associations with {niche}
       - Define lighting approaches that evoke the right mood for this customer
    
    2. SYMBOLIC ELEMENTS
       - Include powerful visual symbols that connect to the customer's values
       - Create unexpected juxtapositions or elements that surprise while remaining relevant
       - Incorporate subtle details that only someone passionate about {niche} would notice
       - Balance aspirational elements with authentic, relatable touches
    
    3. COMPOSITIONAL STRATEGY  
       - Design a focal point that immediately grabs this specific customer's attention
       - Suggest composition techniques that align with their aesthetic sensibilities
       - Define perspective approaches that create the right emotional distance
       - Balance white space and visual density based on their cognitive preferences
    
    4. EMOTIONAL RESONANCE
       - Target specific emotional triggers that motivate this customer
       - Create visual contrast that reflects their decision-making patterns
       - Include elements that address their specific pain points related to {niche}
       - Develop a visual hierarchy that guides them toward conversion
    
    5. SEO & MARKET TARGETING OPTIMIZATION
       - Incorporate searchable industry-standard elements that shoppers look for
       - Include clear product visualization that matches search intent
       - Consider elements that are trending in {niche} market searches
       - Ensure the image has a clear focal point that reads well in thumbnails
    
    DELIVERABLE FORMAT:
    Provide your response in JSON format with these fields:
    1. "prompt": a detailed, evocative image prompt (5-7 sentences) that would generate an image perfectly tailored to this customer
    2. "alt_text": a concise, SEO-rich alternative text description (max 125 chars)
    3. "keywords": 3-5 most relevant SEO keywords for this image
    4. "image_title": SEO-optimized title for the image (max 60 chars)
    5. "description": longer SEO-rich description for marketing copy (1-2 sentences)
    """
    
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
    # Fallback to OpenAI for image generation since xAI doesn't support it fully yet
    try:
        # Use OpenAI client instead for image generation
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Prepare prompt with style if specified
        final_prompt = image_prompt
        if style:
            final_prompt = f"{image_prompt} Style: {style}."
        
        # If image_data is provided, include it in the prompt
        if image_data:
            final_prompt = f"{final_prompt} Use the provided reference image as inspiration."
            
        # Generate image with OpenAI
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=final_prompt,
            n=1,
            size="1024x1024",
        )
        
        # Extract the URL from the response
        if response.data and len(response.data) > 0 and hasattr(response.data[0], 'url'):
            return response.data[0].url
        else:
            raise ValueError("No image generated from OpenAI API")
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

def generate_customer_persona(customer):
    """Generate a detailed persona for a customer profile"""
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
            generate_customer_persona_async(grok_client, customer, niche),
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

def generate_marketing_content(customer, campaign_type):
    """Generate personalized marketing content for a customer"""
    import logging
    
    niche = ""
    if customer.get("interests"):
        niche = customer["interests"][0]
    
    # Créer une nouvelle boucle d'événements
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Exécuter la fonction asynchrone avec un timeout
        return loop.run_until_complete(asyncio.wait_for(
            generate_boutique_marketing_content_async(grok_client, customer, niche, campaign_type),
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

def generate_marketing_image(customer, base_prompt, image_data=None, style=None):
    """
    Generate a personalized marketing image for a customer with SEO optimization
    
    Args:
        customer: Customer data dict
        base_prompt: Base text prompt for image generation
        image_data: Optional base64 encoded image data
        style: Optional style to apply (watercolor, oil painting, photorealistic, etc)
        
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
        
        # Générer un prompt optimisé et des métadonnées SEO
        try:
            # Créer une nouvelle boucle d'événements pour la génération du prompt
            prompt_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(prompt_loop)
            
            try:
                # Exécuter avec un timeout pour éviter les blocages
                prompt_data = prompt_loop.run_until_complete(asyncio.wait_for(
                    generate_image_prompt_async(grok_client, customer, niche, base_prompt),
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
            
        # Utiliser OpenAI directement pour la génération d'images
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Ajouter des éléments SEO supplémentaires au prompt final
        seo_enhanced_prompt = f"{final_prompt} The image should be clear and distinct with good product visibility optimized for online marketing."
        
        # Génération de l'image avec des tentatives de récupération en cas d'échec
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                response = openai_client.images.generate(
                    model="dall-e-3",
                    prompt=seo_enhanced_prompt,
                    n=1,
                    size="1024x1024",
                )
                
                # Extraire l'URL de l'image de la réponse
                if hasattr(response, 'data') and len(response.data) > 0 and hasattr(response.data[0], 'url'):
                    image_url = response.data[0].url
                    
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
                        return "https://placehold.co/600x400/grey/white?text=Image+Generation+Failed"
            except Exception as e:
                logging.error(f"Error generating image on attempt {retry_count+1}: {e}")
                retry_count += 1
                if retry_count <= max_retries:
                    logging.info(f"Retrying image generation (attempt {retry_count}/{max_retries})...")
                    time.sleep(2)  # Attendre avant de réessayer
                else:
                    return "https://placehold.co/600x400/grey/white?text=Image+Generation+Failed"
    except Exception as e:
        logging.error(f"Error in overall image generation process: {e}")
        return "https://placehold.co/600x400/grey/white?text=Image+Generation+Failed"
