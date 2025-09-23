from __future__ import annotations

import argparse
import csv
import os
from typing import List, Dict

from .gcs import write_gcs


def main() -> int:
    p = argparse.ArgumentParser(description="Export listings CSV to GCS")
    p.add_argument("--input", required=True, help="Path to CSV file with listings")
    p.add_argument("--bucket", default=os.getenv("GCS_BUCKET"), help="gs://BUCKET or gs://BUCKET/path")
    p.add_argument("--prefix", default=os.getenv("GCS_PREFIX", "rightmove/listings/"), help="prefix within bucket")
    args = p.parse_args()

    rows: List[Dict] = []
    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    dest = write_gcs(rows, bucket_uri=args.bucket, prefix=args.prefix, filename=os.path.basename(args.input), format="csv")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


