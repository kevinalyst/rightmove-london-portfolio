from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

try:
    from dotenv import load_dotenv

    load_dotenv()  # best-effort
except Exception:
    pass


@dataclass(slots=True)
class AppConfig:
    user_agent: str | None = None
    headless: bool = True
    max_concurrency: int = 1
    request_timeout_sec: int = 30
    min_delay_sec: float = 2.0
    max_delay_sec: float = 5.0
    allow_discovery: bool = False
    output_dir: str = "./out"
    output_format: str = "csv"  # csv|parquet|sqlite
    log_level: str = "INFO"

    # runtime
    extra: Dict[str, Any] = field(default_factory=dict)


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config(overrides: Dict[str, Any] | None = None) -> AppConfig:
    overrides = overrides or {}
    cfg = AppConfig(
        user_agent=os.getenv("USER_AGENT") or None,
        headless=_get_bool(os.getenv("HEADLESS"), True),
        max_concurrency=int(os.getenv("MAX_CONCURRENCY") or 1),
        request_timeout_sec=int(os.getenv("REQUEST_TIMEOUT") or 30),
        min_delay_sec=float(os.getenv("MIN_DELAY_SEC") or 2.0),
        max_delay_sec=float(os.getenv("MAX_DELAY_SEC") or 5.0),
        allow_discovery=_get_bool(os.getenv("ALLOW_DISCOVERY"), False),
        output_dir=os.getenv("OUTPUT_DIR") or "./out",
        output_format=os.getenv("OUTPUT_FORMAT") or "csv",
        log_level=os.getenv("LOG_LEVEL") or "INFO",
    )

    for key, value in overrides.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
        else:
            cfg.extra[key] = value
    return cfg


