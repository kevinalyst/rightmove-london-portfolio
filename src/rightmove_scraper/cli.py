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
from .discovery import build_london_search_url, build_search_url, extract_listing_urls_from_search, extract_total_results_from_search
from .slicer import Slice, borough_slices, partition, make_outcode_identifier


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
    start_page: int = typer.Option(1, "--start-page", min=1, help="First page number (1-indexed)"),
    pages: int = typer.Option(1, "--pages", min=1, help="How many pages to fetch from start-page"),
    all: bool = typer.Option(False, "--all", help="Ignore --pages and paginate until no more results"),
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
            p = start_page
            fetched_any = False
            while True:
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
                fetched_any = True
                if all:
                    if not page_urls:
                        break
                    p += 1
                    continue
                # not --all: stop after start_page + pages - 1
                if p >= start_page + pages - 1:
                    break
                p += 1

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
    start_page: int = typer.Option(1, "--start-page", min=1),
    pages: int = typer.Option(1, "--pages", min=1),
    all: bool = typer.Option(False, "--all"),
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
            p = start_page
            while True:
                url = build_london_search_url(query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=p)
                await page.goto(url)
                content = await page.content()
                page_urls = extract_listing_urls_from_search(content)
                discovered.extend(page_urls)
                polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)
                if all:
                    if not page_urls:
                        break
                    p += 1
                    continue
                if p >= start_page + pages - 1:
                    break
                p += 1

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


@app.command("discover-adaptive")
def discover_adaptive(
    min_price: Optional[int] = typer.Option(300000, "--min-price"),
    max_price: Optional[int] = typer.Option(450000, "--max-price"),
    property_type: Optional[str] = typer.Option(None, "--type", help="detached|semi-detached|flat|terraced|bungalow"),
    query: Optional[str] = typer.Option("", "--query", help="Optional keyword filter"),
    slices: Optional[str] = typer.Option(None, "--slices", help="Comma-separated slice names to run; 'null' or empty means all"),
    start_page: Optional[int] = typer.Option(None, "--start-page", min=1, help="First page number (1-indexed)"),
    pages: Optional[int] = typer.Option(None, "--pages", min=1, help="How many pages to fetch from start-page; omit for all"),
    list_only: bool = typer.Option(False, "--list-only", help="Only list available slice names and exit"),
    out: str = typer.Option("./out", "--out"),
):
    """Discover URLs across London using adaptive slicing (borough → district → price)."""
    cfg = load_config()
    logger = setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    from rich.console import Console
    console = Console()

    async def _count(page, location_identifier: str, *, min_price: Optional[int], max_price: Optional[int], query: str = "", property_type: Optional[str] = None) -> int:
        url = build_search_url(location_identifier=location_identifier, query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=1)
        await page.goto(url)
        # Try to accept cookies/banner if present
        try:
            await page.get_by_role("button", name="Accept all").click(timeout=1500)
        except Exception:
            pass
        content = await page.content()
        n = extract_total_results_from_search(content) or 0
        return n

    class _Counter:
        def __init__(self, page):
            self.page = page

        async def count(self, location_identifier: str, *, min_price: Optional[int], max_price: Optional[int], query: str, property_type: Optional[str]) -> int:
            return await _count(self.page, location_identifier, min_price=min_price, max_price=max_price, query=query, property_type=property_type)

    urls: list[str] = []

    async def _run():
        async with browser_context(cfg) as (_, __, page):
            counter = _Counter(page)
            # If user requested specific slices, short-circuit partitioning and build directly
            final_slices: list[Slice] = []
            if slices is not None and slices.strip() and slices.strip().lower() != "null":
                for name in {x.strip() for x in slices.split(",") if x.strip()}:
                    final_slices.append(
                        Slice(level="district", name=name, location_identifier=f"OUTCODE^{name}", price_min=min_price, price_max=max_price)
                    )
            else:
                # Otherwise, run the full partitioning flow once
                initial_slices: list[Slice] = []
                for b in borough_slices():
                    s = Slice(level="borough", name=b, location_identifier="REGION^87490", price_min=min_price, price_max=max_price)
                    initial_slices.append(s)
                for s in initial_slices:
                    parts = await partition(initial_slice=s, result_counter=counter, district_provider=None)
                    final_slices.extend(parts)

            # De-duplicate slices by (location_identifier, price_min, price_max)
            deduped: list[Slice] = []
            seen_keys: set[tuple[str, Optional[int], Optional[int]]] = set()
            for s in final_slices:
                key = (s.location_identifier, s.price_min, s.price_max)
                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped.append(s)
            final_slices = deduped

            # List-only: print slice names and exit
            if list_only:
                seen: set[str] = set()
                for s in final_slices:
                    if s.name not in seen:
                        seen.add(s.name)
                        typer.echo(s.name)
                return

            console.log(f"Generated {len(final_slices)} slices")

            # Collect URLs for each slice with optional pagination limits
            for idx, s in enumerate(final_slices, 1):
                p = start_page or 1
                console.log(f"[{idx}/{len(final_slices)}] Collecting {s.level}={s.name} price=[{s.price_min},{s.price_max})")
                while True:
                    # For OUTCODE searches, Rightmove sometimes expects the search page with primaryLocation/value/andId
                    if s.location_identifier.startswith("OUTCODE^"):
                        outcode = s.location_identifier.split("^", 1)[1]
                        url = f"https://www.rightmove.co.uk/property-for-sale/{outcode}.html?minPrice={(s.price_min or '')}&maxPrice={(s.price_max or '')}&index={(p-1)*24}&searchType=SALE"
                    else:
                        url = build_search_url(location_identifier=s.location_identifier, query=query or "", min_price=s.price_min, max_price=s.price_max, property_type=property_type, page=p)
                    await page.goto(url, wait_until="networkidle")
                    # Try to accept cookies/banner if present
                    try:
                        await page.get_by_role("button", name="Accept all").click(timeout=1500)
                    except Exception:
                        pass
                    # Wait for property cards to render
                    try:
                        await page.locator('[data-testid="propertyCard-link"]').first.wait_for(timeout=5000)
                    except Exception:
                        pass
                    content = await page.content()
                    page_urls = extract_listing_urls_from_search(content)
                    console.log(f"Slice {s.name} page {p}: found {len(page_urls)} URLs")
                    if not page_urls:
                        # Debug snapshot to help troubleshoot 0 URLs on a page
                        try:
                            from pathlib import Path as _Path
                            _dbg_dir = _Path(cfg.output_dir)
                            _dbg_dir.mkdir(parents=True, exist_ok=True)
                            (_dbg_dir / f"debug_search_{s.name}_p{p}.html").write_text(content, encoding="utf-8")
                        except Exception:
                            pass
                        break
                    urls.extend(page_urls)
                    # If pages limit set, stop after desired number
                    if pages is not None and p >= (start_page or 1) + pages - 1:
                        break
                    p += 1
                    polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

    import asyncio
    asyncio.run(_run())

    # De-duplicate by URL, which encodes property id
    from .utils import dedupe_preserve_order
    deduped = dedupe_preserve_order(urls)

    from pathlib import Path
    import csv as _csv
    Path(out).mkdir(parents=True, exist_ok=True)
    out_csv = Path(out) / "discovered_adaptive_seeds.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["url"])
        for u in deduped:
            w.writerow([u])
    typer.echo(f"Wrote {len(deduped)} URLs to {out_csv}")


if __name__ == "__main__":
    app()



