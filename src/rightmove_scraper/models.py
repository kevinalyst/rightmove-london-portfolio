from __future__ import annotations

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class Listing(BaseModel):
    url: HttpUrl
    rightmove_id: str
    price_text: Optional[str] = None
    price_value: Optional[int] = None
    price_currency: Optional[str] = None
    property_type: Optional[str] = None
    property_title: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    sizes: Optional[str] = None
    tenure: Optional[str] = None
    estate_agent: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    council_tax: Optional[str] = None
    parking: Optional[str] = None
    garden: Optional[str] = None
    accessibility: Optional[str] = None


