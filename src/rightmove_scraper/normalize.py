from __future__ import annotations

import re
from typing import Optional


def coerce_int(value: str | None) -> Optional[int]:
    if value is None:
        return None
    m = re.search(r"\d+", value.replace(",", ""))
    return int(m.group()) if m else None


def normalize_tenure(value: str | None) -> Optional[str]:
    if value is None:
        return None
    v = value.strip().lower()
    if "freehold" in v:
        return "Freehold"
    if "leasehold" in v:
        return "Leasehold"
    return value.strip()


def normalize_council_tax(value: str | None) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    # Preserve explicit "Ask agent"
    if "ask agent" in v.lower():
        return "Ask agent"
    # Extract band letter A..H in variants like "Band: B" or "Council tax band C"
    m = re.search(r"band[:\s]*([a-h])", v, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Fallback: any standalone A..H letter
    m2 = re.search(r"\b([A-Ha-h])\b", v)
    if m2:
        return m2.group(1).upper()
    return v


def parse_price(text: str | None) -> tuple[Optional[int], Optional[str]]:
    if not text:
        return None, None
    t = text.strip()
    currency: Optional[str] = None
    if "£" in t:
        currency = "GBP"
    elif "USD" in t or "$" in t:
        currency = "USD"
    elif "EUR" in t or "€" in t:
        currency = "EUR"
    # Extract integer number (allow commas)
    m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)", t)
    if not m:
        return None, currency
    value = int(m.group(1).replace(",", ""))
    return value, currency


