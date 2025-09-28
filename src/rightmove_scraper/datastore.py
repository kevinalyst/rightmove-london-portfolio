from __future__ import annotations

import os

import pandas as pd

from .models import Listing


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_records(records: list[Listing], output_dir: str, output_format: str = "csv") -> str:
    _ensure_dir(output_dir)
    df = pd.DataFrame([r.model_dump() for r in records])
    # Deduplicate by rightmove_id
    if not df.empty:
        df = df.drop_duplicates(subset=["rightmove_id"], keep="last")

    out_path = os.path.join(output_dir, f"listings.{output_format}")
    if output_format == "csv":
        df.to_csv(out_path, index=False)
    elif output_format == "parquet":
        df.to_parquet(out_path, index=False)
    elif output_format == "sqlite":
        import sqlite3

        con = sqlite3.connect(os.path.join(output_dir, "listings.db"))
        df.to_sql("listings", con, if_exists="replace", index=False)
        con.close()
        out_path = os.path.join(output_dir, "listings.db")
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    return out_path


