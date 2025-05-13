from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class PersonaSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    primary_goal: Optional[str] = None
    pain_points: Optional[str] = None
    buying_triggers: Optional[str] = None
    age_range: Optional[str] = None
    gender_affinity: Optional[str] = None
    location_type: Optional[str] = None
    income_bracket: Optional[str] = None
    education_level: Optional[str] = None
    values: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    lifestyle: Optional[str] = None
    personality_traits: Optional[List[str]] = None
    buying_habits: Optional[str] = None
    brand_affinities: Optional[List[str]] = None
    price_sensitivity: Optional[str] = None
    decision_factors: Optional[List[str]] = None
    preferred_channels: Optional[List[str]] = None
    content_preferences: Optional[str] = None
    social_media_behavior: Optional[Dict[str, Any]] = None
    niche_specific_attributes: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None
    avatar_prompt: Optional[str] = None
    niche_market_id: Optional[int] = None
    boutique_id: Optional[int] = None
