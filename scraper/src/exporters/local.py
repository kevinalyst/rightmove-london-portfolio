from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping
import pandas as pd


def write_local(rows: Iterable[Mapping], *, output_path: str, format: str = "csv") -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(rows))
    if format == "csv":
        df.to_csv(output_path, index=False)
    elif format == "parquet":
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")
    return output_path


