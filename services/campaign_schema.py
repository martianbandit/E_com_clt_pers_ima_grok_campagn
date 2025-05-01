from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class CampaignSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    content: str = Field(..., min_length=10)
    campaign_type: str = Field(...)
    profile_data: Optional[Dict[str, Any]] = None
    customer_id: Optional[int] = None
    persona_id: Optional[int] = None
    boutique_id: Optional[int] = None
    prompt_used: Optional[str] = None
    ai_model_used: Optional[str] = None
    status: str = Field(default='draft')
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    platforms: Optional[List[str]] = None
    scheduled_at: Optional[str] = None
    target_audience: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None
