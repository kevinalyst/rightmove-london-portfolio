from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from .utils import RIGHTMOVE_URL_RE, dedupe_preserve_order


def _read_lines(path: Path) -> Iterable[str]:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        yield line.strip()


def load_seeds(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    urls: List[str] = []
    if p.suffix.lower() in {".csv"}:
        with p.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "url" not in reader.fieldnames:
                raise ValueError("CSV must contain a 'url' header")
            for row in reader:
                u = (row.get("url") or "").strip()
                if u:
                    urls.append(u)
    else:
        # treat as plain text, one URL per line (skip header-like line)
        for line in _read_lines(p):
            if line.lower() == "url":
                continue
            if line:
                urls.append(line)

    valid = [u for u in urls if RIGHTMOVE_URL_RE.match(u)]
    return dedupe_preserve_order(valid)


