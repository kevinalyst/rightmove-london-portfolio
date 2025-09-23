from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Geocoder:
    provider: str = "mock"
    api_key: Optional[str] = None

    def reverse(self, lat: float, lon: float) -> Tuple[str, str]:
        """Return (address, postal_district). Mock returns synthetic values.
        Replace with real geocoding by switching provider and wiring SDK.
        """
        if self.provider == "mock":
            return (f"{lat:.5f},{lon:.5f} Mock Address", "E14")
        raise NotImplementedError("Configure a real provider (nominatim/google) as needed.")


def assign_zone(district: str) -> Optional[str]:
    # Minimal example mapping; extend as needed or read from CSV
    mapping = {
        "E14": "Zone 2",
        "SW1": "Zone 1",
        "W11": "Zone 2",
    }
    return mapping.get(district)


def run(input_csv: str, output_csv: str) -> None:
    geocoder = Geocoder(provider=os.getenv("GEOCODER_PROVIDER", "mock"), api_key=os.getenv("GEOCODER_API_KEY"))
    with open(input_csv, newline="", encoding="utf-8") as f_in, open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or []) + ["address", "postal_district", "zone"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            try:
                lat = float(row.get("latitude", "0") or 0)
                lon = float(row.get("longitude", "0") or 0)
            except Exception:
                lat, lon = 0.0, 0.0
            address, district = geocoder.reverse(lat, lon)
            zone = assign_zone(district) or "Unknown"
            row.update({"address": address, "postal_district": district, "zone": zone})
            writer.writerow(row)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    run(args.input, args.output)


