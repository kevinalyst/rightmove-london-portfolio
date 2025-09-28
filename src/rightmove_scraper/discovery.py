from __future__ import annotations

import re
import urllib.parse

from lxml import html

RIGHTMOVE_HOST = "https://www.rightmove.co.uk"


def build_search_url(*, location_identifier: str, query: str = "", min_price: int | None = None, max_price: int | None = None, property_type: str | None = None, page: int = 1) -> str:
    # Build a Rightmove search URL for a given locationIdentifier
    base = f"{RIGHTMOVE_HOST}/property-for-sale/find.html"
    params = {
        "locationIdentifier": location_identifier,
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


def build_london_search_url(query: str = "", min_price: int | None = None, max_price: int | None = None, property_type: str | None = None, page: int = 1) -> str:
    # Backwards-compatible helper: London region id by default
    return build_search_url(location_identifier="REGION^87490", query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=page)


def extract_listing_urls_from_search(html_text: str) -> list[str]:
    doc = html.fromstring(html_text)
    urls: list[str] = []
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
    if out:
        return out
    # Fallback: extract property IDs from raw HTML (handles cases where links render via JSON)
    try:
        ids = re.findall(r"/properties/(\d+)", html_text)
        out = []
        seen = set()
        for pid in ids:
            u = f"{RIGHTMOVE_HOST}/properties/{pid}"
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out
    except Exception:
        return []


def extract_total_results_from_search(html_text: str) -> int | None:
    doc = html.fromstring(html_text)
    # Heuristic: look for text like "12,345 results" or "X properties found"
    full_text = " ".join(doc.xpath("//body//text()"))
    patterns = [
        r"(\d{1,3}(?:,\d{3})+|\d+)\s+results",
        r"(\d{1,3}(?:,\d{3})+|\d+)\s+properties",
        r'"resultCount"\s*:\s*"?(\d{1,3}(?:,\d{3})+|\d+)"?',
    ]
    for pat in patterns:
        m = re.search(pat, full_text, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except Exception:
                pass
    # Fallback: search scripts only
    scripts_text = "\n".join(doc.xpath("//script/text()"))
    m = re.search(r'"resultCount"\s*:\s*"?(\d{1,3}(?:,\d{3})+|\d+)"?', scripts_text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None


