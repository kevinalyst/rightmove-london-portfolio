import argparse
from pathlib import Path
import json
import sys
import time
import pandas as pd
from typing import Optional

# Ensure local src/ is importable for data_transformer
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_transformer.convert_coordinate_tozone import TfLZoneConverter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Local Rightmove transform (no Snowflake)")
    p.add_argument("--input-csv", required=True, help="Path to scraped listings.csv")
    p.add_argument("--output-prefix", required=True, help="Prefix for outputs (without extension)")
    return p.parse_args()


def format_location(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    if pd.isna(lat) or pd.isna(lon):
        return None
    try:
        return f"{float(lat):.6f},{float(lon):.6f}"
    except Exception:
        return None


def reverse_geocode_locations(df: pd.DataFrame, location_col: str = "LOCATION") -> pd.Series:
    geolocator = Nominatim(user_agent="rightmove_transformer", timeout=10)
    addresses: list[Optional[str]] = []
    for loc in df[location_col].tolist():
        if not isinstance(loc, str) or not loc.strip():
            addresses.append(None)
            continue
        try:
            time.sleep(1.1)  # be polite (Nominatim ~1 req/sec)
            result = geolocator.reverse(loc)
            addresses.append(result.address if result and result.address else None)
        except (GeocoderTimedOut, GeocoderServiceError):
            addresses.append(None)
        except Exception:
            addresses.append(None)
    return pd.Series(addresses, index=df.index)


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    out_prefix = Path(args.output_prefix)

    df = pd.read_csv(input_csv)

    # Harmonize to uppercase columns used here
    if "RIGHTMOVE_ID" not in df.columns and "rightmove_id" in df.columns:
        df.rename(columns={"rightmove_id": "RIGHTMOVE_ID"}, inplace=True)
    if "LATITUDE" not in df.columns and "latitude" in df.columns:
        df.rename(columns={"latitude": "LATITUDE"}, inplace=True)
    if "LONGITUDE" not in df.columns and "longitude" in df.columns:
        df.rename(columns={"longitude": "LONGITUDE"}, inplace=True)

    # Build LOCATION string
    df["LOCATION"] = df.apply(lambda r: format_location(r.get("LATITUDE"), r.get("LONGITUDE")), axis=1)

    # Zone enrichment using local converter
    converter = TfLZoneConverter()
    df["ZONE"] = df.apply(
        lambda r: converter.get_zone_from_coordinates(r.get("LATITUDE"), r.get("LONGITUDE")), axis=1
    )

    # Reverse geocode ADDRESS from LOCATION
    df["ADDRESS"] = reverse_geocode_locations(df, location_col="LOCATION")

    # Keep only requested columns
    cols = ["RIGHTMOVE_ID", "LOCATION", "ADDRESS", "ZONE"]
    out_df = df[cols]

    # Save outputs
    out_csv = out_prefix.with_suffix(".csv")
    out_parquet = out_prefix.with_suffix(".parquet")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv, index=False)
    try:
        out_df.to_parquet(out_parquet, index=False)
    except Exception:
        out_df.to_parquet(out_parquet, index=False)

    # Validation summary
    summary = {
        "rows": int(len(out_df)),
        "columns": cols,
        "nulls": {k: int(out_df[k].isna().sum()) for k in cols},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


