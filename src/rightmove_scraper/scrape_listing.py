from __future__ import annotations

import asyncio
from typing import Optional

from lxml import html
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .browser import open_page, wait_for_text, maybe_click, wait_for_any_text
from .extractors import (
    get_title,
    get_price_text,
    get_summary_panel_value,
    get_key_features,
    get_description,
    get_fact_value,
    get_agent,
    find_label_value_fuzzy,
    derive_from_key_features,
    get_fact_after_description,
    get_fact_grid_value,
    get_photo_urls,
    get_floorplan_url,
    get_agent_address,
    get_agent_phone,
    get_lat_lng,
    get_listing_history,
)
from .models import Listing
from .normalize import coerce_int, normalize_tenure, normalize_council_tax, parse_price
from .utils import extract_rightmove_id
from datetime import datetime
from zoneinfo import ZoneInfo


@retry(wait=wait_exponential_jitter(initial=1, max=5), stop=stop_after_attempt(3))
async def scrape(page, url: str) -> Optional[Listing]:
    await open_page(page, url)
    # Wait for any reliable marker to reduce timeouts across page variants
    await wait_for_any_text(page, [
        "Key features",
        "Description",
        "PROPERTY TYPE",
        "TENURE",
        "Guide Price",
        "Price",
    ], timeout_ms=15000)

    # Expand collapsible description and feature area to reveal the 'Show less' anchored facts
    await maybe_click(page, "Read full description")
    await maybe_click(page, "Show more")

    content = await page.content()
    doc = html.fromstring(content)

    price_text = get_price_text(doc)
    price_value, price_currency = parse_price(price_text)
    listing_history = get_listing_history(doc)

    property_type = get_summary_panel_value(doc, "PROPERTY TYPE")
    property_title = get_title(doc)
    bedrooms = coerce_int(get_summary_panel_value(doc, "BEDROOMS"))
    bathrooms = coerce_int(get_summary_panel_value(doc, "BATHROOMS"))
    sizes = get_summary_panel_value(doc, "SIZE")
    tenure = normalize_tenure(
        get_summary_panel_value(doc, "TENURE") or find_label_value_fuzzy(doc, ["Tenure"])
    )

    key_features = get_key_features(doc)
    description = get_description(doc)

    # Strictly prefer values located under the Description section (after Show less)
    council_tax = normalize_council_tax(
        get_fact_grid_value(doc, "COUNCIL TAX")
        or get_fact_after_description(doc, "COUNCIL TAX")
        or get_fact_value(doc, "COUNCIL TAX")
        or find_label_value_fuzzy(doc, ["Council tax", "Council Tax Band", "Council tax band"])
    )
    parking = (
        get_fact_grid_value(doc, "PARKING")
        or get_fact_after_description(doc, "PARKING")
        or get_fact_value(doc, "PARKING")
        or find_label_value_fuzzy(doc, ["Parking", "Parking type", "Off street parking"]) 
        or derive_from_key_features(key_features, ["parking", "driveway", "garage"]) 
    )
    garden = (
        get_fact_grid_value(doc, "GARDEN")
        or get_fact_after_description(doc, "GARDEN")
        or get_fact_value(doc, "GARDEN")
        or find_label_value_fuzzy(doc, ["Garden", "Gardens", "Private garden"]) 
        or derive_from_key_features(key_features, ["garden", "rear garden", "front garden"]) 
    )
    accessibility = (
        get_fact_grid_value(doc, "ACCESSIBILITY")
        or get_fact_after_description(doc, "ACCESSIBILITY")
        or get_fact_value(doc, "ACCESSIBILITY")
        or find_label_value_fuzzy(doc, ["Accessibility", "Lift", "Step free"]) 
    )
    estate_agent = get_agent(doc)
    agent_address = get_agent_address(doc)
    localnumber = get_agent_phone(doc)

    rightmove_id = extract_rightmove_id(url)

    # Removed by agent handling
    removed_banner = doc.xpath('//*[contains(., "removed by the agent")]')
    if removed_banner:
        if not description:
            description = "Removed by agent"

    # Photos up to 10
    photos = get_photo_urls(doc, limit=10)
    # Normalize to exactly 10 entries by padding with None
    photos = (photos + [None] * 10)[:10]

    # Floorplan and coordinates
    floorplan_url = get_floorplan_url(doc)
    lat, lng = get_lat_lng(doc)

    return Listing(
        url=url,
        rightmove_id=rightmove_id,
        price_text=price_text,
        price_value=price_value,
        price_currency=price_currency,
        listing_history=listing_history,
        property_type=property_type,
        property_title=property_title,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        sizes=sizes,
        tenure=tenure,
        estate_agent=estate_agent,
        agent_address=agent_address,
        localnumber=localnumber,
        key_features=key_features,
        description=description,
        council_tax=council_tax,
        parking=parking,
        garden=garden,
        accessibility=accessibility,
        photo_1=photos[0],
        photo_2=photos[1],
        photo_3=photos[2],
        photo_4=photos[3],
        photo_5=photos[4],
        photo_6=photos[5],
        photo_7=photos[6],
        photo_8=photos[7],
        photo_9=photos[8],
        photo_10=photos[9],
        floorplan=floorplan_url,
        latitude=lat,
        longitude=lng,
        timestamp=datetime.now(ZoneInfo("Europe/London")).isoformat(),
    )


