from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


CAP = 1000
DEFAULT_MIN_PRICE = 0
DEFAULT_MAX_PRICE = 10_000_000  # 10M upper bound for adaptive price partitioning


@dataclass(frozen=True)
class Slice:
    level: str  # "region" | "borough" | "district"
    name: str  # borough or district code
    location_identifier: str  # REGION^... or OUTCODE^...
    price_min: Optional[int]
    price_max: Optional[int]

    def with_price(self, lo: Optional[int], hi: Optional[int]) -> "Slice":
        return Slice(
            level=self.level,
            name=self.name,
            location_identifier=self.location_identifier,
            price_min=lo,
            price_max=hi,
        )


# Minimal practical borough → districts starter map
BOROUGH_TO_DISTRICTS: dict[str, list[str]] = {
    "Westminster": ["W1", "SW1", "NW1", "WC2"],
    "Kensington and Chelsea": ["W8", "W10", "W11", "SW3", "SW5", "SW7"],
    "Camden": ["NW1", "NW3", "WC1", "WC2", "N1"],
    "Islington": ["N1", "N5", "N7"],
    "Tower Hamlets": ["E1", "E2", "E3", "E14"],
    "Hackney": ["E2", "E5", "E8", "E9"],
    "Southwark": ["SE1", "SE5", "SE16", "SE15"],
    "Lambeth": ["SW2", "SW4", "SW8", "SW9", "SE1"],
    "Wandsworth": ["SW11", "SW12", "SW15", "SW18"],
    "Hammersmith and Fulham": ["W6", "W12", "W14", "SW6"],
    "Ealing": ["W3", "W5", "W7", "W13", "UB1", "UB2"],
    "Barnet": ["NW4", "NW7", "EN4", "EN5", "N2", "N3"],
    "Brent": ["NW2", "NW6", "NW9", "HA0", "HA9"],
    "Croydon": ["CR0", "CR2", "CR7"],
    "Richmond upon Thames": ["TW1", "TW9", "TW10"],
    "Newham": ["E6", "E7", "E13", "E15", "E16"],
    "Waltham Forest": ["E10", "E11", "E17"],
}


def borough_slices() -> list[str]:
    return [
        # Inner (13) + City of London
        "Camden",
        "City of London",
        "Greenwich",
        "Hackney",
        "Hammersmith and Fulham",
        "Islington",
        "Kensington and Chelsea",
        "Lambeth",
        "Southwark",
        "Tower Hamlets",
        "Wandsworth",
        "Westminster",
        "Newham",
        # Outer (20)
        "Barking and Dagenham",
        "Barnet",
        "Bexley",
        "Brent",
        "Bromley",
        "Croydon",
        "Ealing",
        "Enfield",
        "Haringey",
        "Harrow",
        "Havering",
        "Hillingdon",
        "Hounslow",
        "Kingston upon Thames",
        "Merton",
        "Redbridge",
        "Richmond upon Thames",
        "Sutton",
        "Waltham Forest",
    ]


def split_price(range_min: int, range_max: int) -> tuple[tuple[int, int], tuple[int, int]]:
    # Choose a midpoint at 5k granularity, ensuring strictly increasing bounds
    mid_raw = (range_min + range_max) // 2
    mid = int((mid_raw // 5000) * 5000)
    if mid <= range_min:
        mid = range_min + 5000
    if mid >= range_max:
        mid = range_max - 5000
    return (range_min, mid), (mid, range_max)


def make_region_identifier(name: str) -> str:
    # Placeholder: caller must resolve to REGION^ id; keep name for logging
    # The default London region is REGION^87490; per-borough REGION^ ids should be resolved by caller.
    return "REGION^87490"


def make_outcode_identifier(outcode: str) -> str:
    return f"OUTCODE^{outcode.upper()}"


class ResultCounter:
    async def count(self, location_identifier: str, *, min_price: Optional[int], max_price: Optional[int], query: str, property_type: Optional[str]) -> int:
        raise NotImplementedError


async def partition(
    *,
    initial_slice: Slice,
    result_counter: ResultCounter,
    district_provider: callable | None,
    query: str,
    property_type: Optional[str],
) -> Iterable[Slice]:
    # DFS partitioning adhering to CAP
    stack: list[Slice] = [initial_slice]
    out: list[Slice] = []

    while stack:
        current = stack.pop()
        n = await result_counter.count(
            current.location_identifier,
            min_price=current.price_min,
            max_price=current.price_max,
            query=query,
            property_type=property_type,
        )
        if n <= CAP:
            out.append(current)
            continue

        if current.level == "region":
            # Split region into distinct outcodes from our borough→districts cheat-sheet
            seen_outcodes: set[str] = set()
            for districts in BOROUGH_TO_DISTRICTS.values():
                for d in districts:
                    if d not in seen_outcodes:
                        seen_outcodes.add(d)
                        stack.append(
                            Slice(
                                level="district",
                                name=d,
                                location_identifier=make_outcode_identifier(d),
                                price_min=current.price_min,
                                price_max=current.price_max,
                            )
                        )
            continue

        if current.level == "borough":
            districts = (district_provider(current.name) if district_provider else BOROUGH_TO_DISTRICTS.get(current.name, []))
            if districts:
                for d in districts:
                    stack.append(
                        Slice(
                            level="district",
                            name=d,
                            location_identifier=make_outcode_identifier(d),
                            price_min=current.price_min,
                            price_max=current.price_max,
                        )
                    )
                continue

        if current.level == "district":
            # Allow price splitting even when initial bounds are None by using default bounds
            eff_min = current.price_min if current.price_min is not None else DEFAULT_MIN_PRICE
            eff_max = current.price_max if current.price_max is not None else DEFAULT_MAX_PRICE
            # Only split if we have meaningful width to avoid zero-width segments
            if eff_max - eff_min > 10_000:  # ensure both halves at least 5k wide
                (a_lo, a_hi), (b_lo, b_hi) = split_price(eff_min, eff_max)
                stack.append(current.with_price(a_lo, a_hi))
                stack.append(current.with_price(b_lo, b_hi))
                continue

        # If we cannot split further, accept as-is to avoid infinite loop
        out.append(current)

    return out


