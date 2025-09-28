from __future__ import annotations

import os

from rich.console import Console


def assert_personal_use_banner() -> None:
    console = Console(force_terminal=True)
    console.print("[bold yellow]\nThis scraper is for personal, non-commercial research only.\nRespect Rightmove ToS and robots; scrape gently.\n[/bold yellow]")


def discovery_enabled() -> bool:
    allow = os.getenv("ALLOW_DISCOVERY", "false").lower() in {"1", "true", "yes", "on"}
    if not allow:
        return False
    return os.path.exists(os.path.join(os.getcwd(), "consent.txt"))


