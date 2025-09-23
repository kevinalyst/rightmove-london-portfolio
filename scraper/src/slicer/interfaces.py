from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, List


@dataclass(frozen=True)
class Slice:
    level: str  # "borough" | "district" | "price"
    name: str
    location_identifier: str
    price_min: Optional[int] = None
    price_max: Optional[int] = None


class ResultCounter(Protocol):
    async def count(
        self,
        location_identifier: str,
        *,
        min_price: Optional[int],
        max_price: Optional[int],
        query: str,
        property_type: Optional[str],
    ) -> int: ...


CAP = 1000

async def partition(
    initial_slice: Slice,
    *,
    result_counter: ResultCounter,
    district_provider: Optional[object],
    query: str,
    property_type: Optional[str],
) -> List[Slice]:
    """Minimal stub that returns the input if under CAP, else price-splits.

    This is a clean, testable interface; the real implementation already exists in src/rightmove_scraper/slicer.py.
    """
    n = await result_counter.count(
        initial_slice.location_identifier,
        min_price=initial_slice.price_min,
        max_price=initial_slice.price_max,
        query=query,
        property_type=property_type,
    )
    if n <= CAP:
        return [initial_slice]
    # Split price range into two bands if not provided
    lo = initial_slice.price_min or 0
    hi = initial_slice.price_max or 1_000_000_000
    mid = (lo + hi) // 2
    return [
        Slice(level="price", name=f"{initial_slice.name}_lo", location_identifier=initial_slice.location_identifier, price_min=lo, price_max=mid),
        Slice(level="price", name=f"{initial_slice.name}_hi", location_identifier=initial_slice.location_identifier, price_min=mid, price_max=hi),
    ]

