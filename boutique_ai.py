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
    Generate {num_customers} sample customers for a boutique focused on {niche}.
    Boutique description: {niche_description}
    
    The customers should have the following attributes:
    - name: str
    - age: int
    - location: str
    - country_code: str (2-letter ISO code, e.g., 'US', 'FR', 'JP')
    - gender: Gender
    - language: str
    - purchase_history: list[Item]
    - interests: list[str]
    - search_history: dict[str, str]
    - preferred_device: str
    - income_level: str (one of: 'budget', 'middle', 'affluent', 'luxury')
    - education: str (e.g., 'high school', 'bachelor', 'master', 'doctorate')
    - occupation: str
    - social_media: dict[str, str] (platform name and usage frequency)
    - shopping_frequency: str (one of: 'rarely', 'occasionally', 'frequently', 'very frequently')

    Here are the attributes of an Item:
    - name: str (make this relevant to the {niche} niche)
    - category: str (make this relevant to the {niche} niche)
    - price: float (make this realistic for {niche} products)
    - purchase_date: str (in YYYY-MM-DD format)

    Each customer should be varied and distinct from the others: 
    - Ensure the customers are realistic for the {niche} market
    - Include appropriate languages based on the customer's location
    - Make sure purchase history, interests, and search history are highly relevant to the {niche} niche
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
    
    # Craft a boutique-specific persona generation prompt
    prompt = f"""
    Create a detailed, compelling persona for a customer of a {niche} boutique with the following information:
    
    Name: {name}
    Age: {age}
    Location: {location}
    Gender: {gender}
    Language: {language}
    Interests: {interests}
    
    Purchase History:
    {purchase_str}
    
    This persona should tell a rich story about this customer that helps understand:
    1. Their relationship with the {niche} market
    2. Their shopping habits and preferences
    3. Their lifestyle and values
    4. What motivates their purchasing decisions
    5. What kind of personalized marketing would resonate with them
    
    Write in second person as if you're directly describing the customer to the boutique owner.
    The persona should be 3-4 paragraphs long, vivid and specific.
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
) -> str:
    interests = ", ".join(customer.get("interests", []))
    persona = customer.get("persona", "")
    
    meta_prompt = f"""
    Create a detailed image generation prompt for a {niche} boutique marketing image.
    
    Base idea: {base_prompt}
    
    Customer interests: {interests}
    
    Customer persona summary: {persona[:200]}...
    
    Your task is to enhance this base prompt to:
    1. Appeal specifically to this customer's aesthetic preferences
    2. Incorporate visual elements from the {niche} niche
    3. Suggest specific colors, styles, and composition that would resonate with this customer
    4. Create a visually striking image that will catch this customer's attention
    5. Make it feel personalized to their tastes
    
    Write a detailed, specific image generation prompt that would create an image perfect for this customer.
    The prompt should be 3-5 sentences long and extremely detailed.
    """
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.8,
            max_tokens=400,
        )
        
        if not response.choices or not response.choices[0].message.content:
            return base_prompt
            
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating image prompt: {e}")
        return base_prompt

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
        
    customers_obj = asyncio.run(generate_boutique_customers(
        grok_client, 
        niche, 
        niche_description, 
        num_customers,
        target_country=generation_params.get('target_country', ''),
        age_range=generation_params.get('age_range', ''),
        income_level=generation_params.get('income_level', '')
    ))
    
    # Convert to a list of dictionaries for JSON serialization
    return [customer.dict() for customer in customers_obj.customers]

def generate_customer_persona(customer):
    """Generate a detailed persona for a customer profile"""
    niche = ""  # Extract from interests or other attributes
    if customer.get("interests"):
        niche = customer["interests"][0]  # Use first interest as niche if not specified
    return asyncio.run(generate_customer_persona_async(grok_client, customer, niche))

def generate_marketing_content(customer, campaign_type):
    """Generate personalized marketing content for a customer"""
    niche = ""
    if customer.get("interests"):
        niche = customer["interests"][0]
    return asyncio.run(generate_boutique_marketing_content_async(grok_client, customer, niche, campaign_type))

def generate_marketing_image(customer, base_prompt, image_data=None, style=None):
    """
    Generate a personalized marketing image for a customer
    
    Args:
        customer: Customer data dict
        base_prompt: Base text prompt for image generation
        image_data: Optional base64 encoded image data
        style: Optional style to apply (watercolor, oil painting, photorealistic, etc)
        
    Returns:
        URL of the generated image
    """
    niche = ""
    if customer.get("interests"):
        niche = customer["interests"][0]
        
    # First, enhance the prompt for this specific customer and niche
    enhanced_prompt = asyncio.run(generate_image_prompt_async(grok_client, customer, niche, base_prompt))
    
    # Then, generate the image using the enhanced prompt and optional parameters
    return asyncio.run(generate_boutique_image_async(
        grok_client, 
        enhanced_prompt, 
        image_data=image_data,
        style=style
    ))
