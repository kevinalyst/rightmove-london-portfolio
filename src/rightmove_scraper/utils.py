from __future__ import annotations

import random
import re
import time
from collections.abc import Iterable

RIGHTMOVE_URL_RE = re.compile(r"https?://(www\.)?rightmove\.co\.uk/properties/(\d+)")


def polite_sleep(min_seconds: float, max_seconds: float) -> None:
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def extract_rightmove_id(url: str) -> str:
    match = RIGHTMOVE_URL_RE.match(url)
    if not match:
        raise ValueError(f"Invalid Rightmove property URL: {url}")
    return match.group(2)


def dedupe_preserve_order(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


