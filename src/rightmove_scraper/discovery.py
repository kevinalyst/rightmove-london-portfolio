from __future__ import annotations

import urllib.parse
from typing import Iterable, List

from lxml import html


RIGHTMOVE_HOST = "https://www.rightmove.co.uk"


def build_london_search_url(query: str = "", min_price: int | None = None, max_price: int | None = None, property_type: str | None = None, page: int = 1) -> str:
    # Use a canonical London search path; Rightmove uses query params in encoded form
    # We keep it minimal and stable.
    base = f"{RIGHTMOVE_HOST}/property-for-sale/find.html"
    params = {
        # IMPORTANT: pass raw caret so urlencode produces %5E (avoid double-encoding)
        "locationIdentifier": "REGION^87490",  # London region id
        "searchType": "SALE",
        "index": str((page - 1) * 24),
    }
    if min_price is not None:
        params["minPrice"] = str(min_price)
    if max_price is not None:
        params["maxPrice"] = str(max_price)
    if property_type:
        params["propertyTypes"] = property_type
    if query:
        params["keywords"] = query
    return base + "?" + urllib.parse.urlencode(params)


def extract_listing_urls_from_search(html_text: str) -> List[str]:
    doc = html.fromstring(html_text)
    urls: List[str] = []
    anchors = doc.xpath(
        '//*[@data-testid="propertyCard-link" or contains(@class, "propertyCard")]//a[contains(@href, "/properties/")][@href]'
        ' | //a[contains(@href, "/properties/")][@href]'
    )
    for a in anchors:
        href = a.get("href") or ""
        if "/properties/" in href:
            if href.startswith("/"):
                href = RIGHTMOVE_HOST + href
            # normalize to canonical detail page without query/hash tracking
            href = href.split("?")[0].split("#")[0]
            urls.append(href)
    # de-duplicate preserving order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


