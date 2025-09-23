from __future__ import annotations

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class Listing(BaseModel):
    url: HttpUrl
    rightmove_id: str
    price_text: Optional[str] = None
    price_value: Optional[int] = None
    price_currency: Optional[str] = None
    listing_history: Optional[str] = None
    property_type: Optional[str] = None
    property_title: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    sizes: Optional[str] = None
    tenure: Optional[str] = None
    estate_agent: Optional[str] = None
    agent_address: Optional[str] = None
    localnumber: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    council_tax: Optional[str] = None
    parking: Optional[str] = None
    garden: Optional[str] = None
    accessibility: Optional[str] = None
    # Photos (top 10 if available)
    photo_1: Optional[str] = None
    photo_2: Optional[str] = None
    photo_3: Optional[str] = None
    photo_4: Optional[str] = None
    photo_5: Optional[str] = None
    photo_6: Optional[str] = None
    photo_7: Optional[str] = None
    photo_8: Optional[str] = None
    photo_9: Optional[str] = None
    photo_10: Optional[str] = None
    floorplan: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[str] = None


