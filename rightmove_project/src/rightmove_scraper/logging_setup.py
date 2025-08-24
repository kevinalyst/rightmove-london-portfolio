from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> logging.Logger:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    console = Console(force_terminal=True)
    handler = RichHandler(console=console, show_time=True, show_level=True, show_path=False)
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
    )
    logger = logging.getLogger("rightmove_scraper")
    logger.setLevel(numeric_level)
    return logger


