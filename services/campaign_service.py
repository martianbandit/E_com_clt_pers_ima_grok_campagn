from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError, Field
from app.models import Campaign
from app import db

class CampaignSchema(BaseModel):
    title: str
    content: str
    campaign_type: str
    profile_data: Optional[Dict[str, Any]] = None
    customer_id: Optional[int] = None
    persona_id: Optional[int] = None
    boutique_id: Optional[int] = None
    prompt_used: Optional[str] = None
    ai_model_used: Optional[str] = None
    status: str = 'draft'
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    platforms: Optional[list] = None
    scheduled_at: Optional[str] = None
    target_audience: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None


def validate_campaign_data(data: Dict[str, Any]) -> CampaignSchema:
    """
    Valide et nettoie les données d'une campagne (ex: issues de l'IA).
    Lève ValidationError si incohérent.
    """
    return CampaignSchema(**data)


def create_campaign(data: Dict[str, Any]) -> Campaign:
    """
    Crée une campagne après validation stricte.
    """
    validated = validate_campaign_data(data)
    campaign = Campaign(**validated.dict())
    db.session.add(campaign)
    db.session.commit()
    return campaign


def publish_campaign(campaign_id: int) -> Campaign:
    """
    Change le statut d'une campagne en 'published' de façon centralisée.
    """
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.status == 'published':
        return campaign
    campaign.status = 'published'
    db.session.commit()
    return campaign
