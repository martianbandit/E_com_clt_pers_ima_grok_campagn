from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ProductSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: Optional[str] = None
    base_description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    generated_title: Optional[str] = None
    generated_description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    alt_text: Optional[str] = None
    keywords: Optional[List[str]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    comparative_analysis: Optional[Dict[str, Any]] = None
    target_audience_id: Optional[int] = None
    boutique_id: Optional[int] = None
    html_description: Optional[str] = None
    html_specifications: Optional[str] = None
    html_faq: Optional[str] = None
