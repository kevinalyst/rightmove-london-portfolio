from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class Listing(BaseModel):
    url: HttpUrl
    rightmove_id: str
    price_text: str | None = None
    price_value: int | None = None
    price_currency: str | None = None
    listing_history: str | None = None
    property_type: str | None = None
    property_title: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    sizes: str | None = None
    tenure: str | None = None
    estate_agent: str | None = None
    agent_address: str | None = None
    localnumber: str | None = None
    key_features: list[str] = Field(default_factory=list)
    description: str | None = None
    council_tax: str | None = None
    parking: str | None = None
    garden: str | None = None
    accessibility: str | None = None
    # Photos (top 10 if available)
    photo_1: str | None = None
    photo_2: str | None = None
    photo_3: str | None = None
    photo_4: str | None = None
    photo_5: str | None = None
    photo_6: str | None = None
    photo_7: str | None = None
    photo_8: str | None = None
    photo_9: str | None = None
    photo_10: str | None = None
    floorplan: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timestamp: str | None = None


