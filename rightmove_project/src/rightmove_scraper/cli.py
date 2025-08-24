from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console

from .config import load_config
from .logging_setup import setup_logging
from .compliance import assert_personal_use_banner, discovery_enabled
from .browser import browser_context
from .scrape_listing import scrape
from .datastore import write_records
from .seeds import load_seeds
from .utils import polite_sleep
from .discovery import build_london_search_url, extract_listing_urls_from_search


app = typer.Typer(add_completion=False, help="Rightmove personal research scraper")


@app.command("scrape-seeds")
def scrape_seeds(
    input: str = typer.Option(..., "--input", help="CSV/TXT with header 'url' column or lines"),
    out: str = typer.Option("./out", "--out", help="Output directory"),
    format: str = typer.Option("csv", "--format", help="csv|parquet|sqlite"),
    max: int = typer.Option(25, "--max", min=1, help="Max URLs to scrape"),
    headless: Optional[bool] = typer.Option(None, help="Override headless"),
    concurrency: int = typer.Option(1, "--concurrency", min=1, max=5, help="Parallel pages"),
    timeout: int = typer.Option(20, "--timeout", min=5, help="Per-page timeout seconds"),
):
    """Scrape property detail pages from a list of seed URLs."""
    cfg_overrides = {}
    if headless is not None:
        cfg_overrides["headless"] = headless
    cfg_overrides["output_dir"] = out
    cfg_overrides["output_format"] = format
    cfg_overrides["request_timeout_sec"] = timeout
    cfg = load_config(cfg_overrides)

    logger = setup_logging(cfg.log_level)
    assert_personal_use_banner()

    urls = load_seeds(input)[:max]
    if not urls:
        typer.echo("No valid seed URLs found.")
        raise typer.Exit(code=1)

    console = Console()
    records = []
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)

    async def _run():
        from .models import Listing
        sem = asyncio.Semaphore(concurrency)

        async with browser_context(cfg) as (_, context, _):
            async def worker(idx: int, url: str):
                async with sem:
                    try:
                        page = await context.new_page()
                        try:
                            listing: Listing | None = await scrape(page, url)
                        finally:
                            await page.close()
                        if listing is not None:
                            records.append(listing)
                            console.log(f"[{idx}/{len(urls)}] scraped: {url}")
                    except Exception as e:
                        console.log(f"Error scraping {url}: {e}")
                    finally:
                        polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

            await asyncio.gather(*(worker(idx, url) for idx, url in enumerate(urls, 1)))

    asyncio.run(_run())

    out_path = write_records(records, cfg.output_dir, cfg.output_format)
    console.log(f"Wrote {len(records)} records to {out_path}")


@app.command("dump-snapshots")
def dump_snapshots(
    input: str = typer.Option(..., "--input", help="Seeds CSV/TXT"),
    limit: int = typer.Option(5, "--limit", min=1),
):
    cfg = load_config()
    console = Console()
    urls = load_seeds(input)[:limit]

    async def _run():
        async with browser_context(cfg) as (_, __, page):
            for idx, url in enumerate(urls, 1):
                await page.goto(url)
                content = await page.content()
                out_dir = Path("tests/fixtures/html")
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"sample_listing_{idx}.html").write_text(content, encoding="utf-8")
                console.log(f"Saved snapshot for {url}")

    asyncio.run(_run())


@app.command("validate")
def validate(file: str = typer.Option(..., "--file")):
    import pandas as pd
    from .models import Listing

    df = pd.read_csv(file)
    required_columns = [
        "url",
        "rightmove_id",
        "property_type",
        "property_title",
        "bedrooms",
        "bathrooms",
        "sizes",
        "tenure",
        "estate_agent",
        "key_features",
        "description",
        "council_tax",
        "parking",
        "garden",
        "accessibility",
    ]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        typer.echo(f"Missing columns: {missing}")
        raise typer.Exit(code=1)
    typer.echo("OK")


@app.command("discover-search")
def discover_search(
    query: str = typer.Option("", "--query", help="Optional keyword filter"),
    min_price: Optional[int] = typer.Option(None, "--min-price"),
    max_price: Optional[int] = typer.Option(None, "--max-price"),
    property_type: Optional[str] = typer.Option(None, "--type", help="detached|semi-detached|flat|terraced|bungalow"),
    pages: int = typer.Option(1, "--pages", min=1, max=10),
    out: str = typer.Option("./out", "--out"),
):
    cfg = load_config()
    logger = setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    from rich.console import Console
    console = Console()
    urls: list[str] = []

    async def _run():
        async with browser_context(cfg) as (_, __, page):
            for p in range(1, pages + 1):
                url = build_london_search_url(query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=p)
                await page.goto(url)
                # Try to accept cookies/banner if present
                try:
                    await page.get_by_role("button", name="Accept all").click(timeout=2000)
                except Exception:
                    pass
                # Wait for property cards to render
                try:
                    await page.locator('[data-testid="propertyCard-link"]').first.wait_for(timeout=5000)
                except Exception:
                    pass
                content = await page.content()
                page_urls = extract_listing_urls_from_search(content)
                console.log(f"Page {p}: found {len(page_urls)} property URLs")
                urls.extend(page_urls)
                polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

    asyncio.run(_run())

    # Write URLs to seeds.csv compatible file
    from pathlib import Path
    import csv as _csv
    Path(out).mkdir(parents=True, exist_ok=True)
    out_csv = Path(out) / "discovered_seeds.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["url"])
        for u in dict.fromkeys(urls):
            w.writerow([u])
    typer.echo(f"Wrote {len(dict.fromkeys(urls))} URLs to {out_csv}")


@app.command("scrape-search")
def scrape_search(
    query: str = typer.Option("", "--query"),
    min_price: Optional[int] = typer.Option(None, "--min-price"),
    max_price: Optional[int] = typer.Option(None, "--max-price"),
    property_type: Optional[str] = typer.Option(None, "--type"),
    pages: int = typer.Option(1, "--pages", min=1, max=10),
    out: str = typer.Option("./out", "--out"),
    format: str = typer.Option("csv", "--format"),
    max: int = typer.Option(50, "--max", min=1),
):
    cfg = load_config({"output_dir": out, "output_format": format})
    logger = setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    from rich.console import Console
    console = Console()
    discovered: list[str] = []

    async def _discover():
        async with browser_context(cfg) as (_, __, page):
            for p in range(1, pages + 1):
                url = build_london_search_url(query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=p)
                await page.goto(url)
                content = await page.content()
                page_urls = extract_listing_urls_from_search(content)
                discovered.extend(page_urls)
                polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

    asyncio.run(_discover())
    if not discovered:
        typer.echo("No listings found.")
        raise typer.Exit(code=1)

    seeds = list(dict.fromkeys(discovered))[:max]
    console.log(f"Scraping {len(seeds)} discovered listings…")

    records = []

    async def _scrape():
        from .models import Listing
        sem = asyncio.Semaphore(2)
        async with browser_context(cfg) as (_, context, _):
            async def worker(idx: int, url: str):
                async with sem:
                    try:
                        page = await context.new_page()
                        try:
                            listing: Listing | None = await scrape(page, url)
                        finally:
                            await page.close()
                        if listing is not None:
                            records.append(listing)
                            console.log(f"[{idx}/{len(seeds)}] scraped: {url}")
                    except Exception as e:
                        console.log(f"Error scraping {url}: {e}")
                    finally:
                        polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

            await asyncio.gather(*(worker(idx, url) for idx, url in enumerate(seeds, 1)))

    asyncio.run(_scrape())
    out_path = write_records(records, cfg.output_dir, cfg.output_format)
    console.log(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    app()



