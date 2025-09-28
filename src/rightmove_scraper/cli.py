from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from .browser import browser_context
from .compliance import assert_personal_use_banner, discovery_enabled
from .config import load_config
from .datastore import write_records
from .discovery import (
    build_london_search_url,
    build_search_url,
    extract_listing_urls_from_search,
    extract_total_results_from_search,
)
from .logging_setup import setup_logging
from .scrape_listing import scrape
from .seeds import load_seeds
from .slicer import BOROUGH_TO_DISTRICTS, Slice, borough_slices, partition
from .utils import dedupe_preserve_order, extract_rightmove_id, polite_sleep

app = typer.Typer(add_completion=False, help="Rightmove personal research scraper")


@app.command("scrape-seeds")
def scrape_seeds(
    input: str = typer.Option(..., "--input", help="CSV/TXT with header 'url' column or lines"),
    out: str = typer.Option("./out", "--out", help="Output directory"),
    format: str = typer.Option("csv", "--format", help="csv|parquet|sqlite"),
    max: int = typer.Option(25, "--max", min=1, help="Max URLs to scrape"),
    headless: bool | None = typer.Option(None, help="Override headless"),
    concurrency: int = typer.Option(1, "--concurrency", min=1, max=5, help="Parallel pages"),
    timeout: int = typer.Option(20, "--timeout", min=5, help="Per-page timeout seconds"),
    batch_size: int | None = typer.Option(None, "--batch-size", min=1, help="If set, write batch outputs after every N scraped records"),
    batch_dir: str | None = typer.Option(None, "--batch-dir", help="Directory for batch outputs; defaults to <out>/batches"),
):
    """Scrape property detail pages from a list of seed URLs."""
    cfg_overrides = {}
    if headless is not None:
        cfg_overrides["headless"] = headless
    cfg_overrides["output_dir"] = out
    cfg_overrides["output_format"] = format
    cfg_overrides["request_timeout_sec"] = timeout
    cfg = load_config(cfg_overrides)

    setup_logging(cfg.log_level)
    assert_personal_use_banner()

    urls = load_seeds(input)[:max]
    if not urls:
        typer.echo("No valid seed URLs found.")
        raise typer.Exit(code=1)

    console = Console()
    records: list = []
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)

    async def _run():
        from .models import Listing
        sem = asyncio.Semaphore(concurrency)
        batch_records: list = []
        batches_written: int = 0

        def _flush_batch():
            nonlocal batch_records, batches_written
            if not batch_size or not batch_records:
                return
            target_dir = batch_dir or os.path.join(cfg.output_dir, "batches")
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            out_path = os.path.join(target_dir, f"listings_batch_{batches_written + 1:03d}.{cfg.output_format}")
            import pandas as _pd
            df = _pd.DataFrame([r.model_dump() for r in batch_records])
            if not df.empty:
                df = df.drop_duplicates(subset=["rightmove_id"], keep="last")
            if cfg.output_format == "csv":
                df.to_csv(out_path, index=False)
            elif cfg.output_format == "parquet":
                df.to_parquet(out_path, index=False)
            elif cfg.output_format == "sqlite":
                import sqlite3 as _sqlite3
                db_path = os.path.join(target_dir, f"listings_batch_{batches_written + 1:03d}.db")
                con = _sqlite3.connect(db_path)
                df.to_sql("listings", con, if_exists="replace", index=False)
                con.close()
                out_path = db_path
            console.log(f"Wrote batch of {len(batch_records)} to {out_path}")
            batches_written += 1
            batch_records.clear()

        async with browser_context(cfg) as (_, context, _):
            async def worker(idx: int, url: str):
                nonlocal batch_records, batches_written
                async with sem:
                    try:
                        page = await context.new_page()
                        try:
                            listing: Listing | None = await scrape(page, url)
                        finally:
                            await page.close()
                        if listing is not None:
                            records.append(listing)
                            if batch_size:
                                batch_records.append(listing)
                                if len(batch_records) >= batch_size:
                                    _flush_batch()
                            console.log(f"[{idx}/{len(urls)}] scraped: {url}")
                    except Exception as e:
                        console.log(f"Error scraping {url}: {e}")
                    finally:
                        polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

            await asyncio.gather(*(worker(idx, url) for idx, url in enumerate(urls, 1)))
            # Final flush
            _flush_batch()

    asyncio.run(_run())

    out_path = write_records(records, cfg.output_dir, cfg.output_format)
    console.log(f"Wrote {len(records)} records to {out_path}")


@app.command("shard-seeds")
def shard_seeds(
    input: str = typer.Option(..., "--input", help="Path to seeds CSV/TXT with 'url' header or one URL per line"),
    shards: int = typer.Option(20, "--shards", min=1, help="Number of output shards"),
    out: str = typer.Option("./out/shards", "--out", help="Directory to write shard_XX.csv files"),
):
    """Split a seeds file into N ordered shards with roughly equal sizes.

    Each shard is written as CSV with a single 'url' header, preserving original order.
    """
    import csv as _csv
    from pathlib import Path as _Path

    urls = load_seeds(input)
    n = len(urls)
    _Path(out).mkdir(parents=True, exist_ok=True)
    if n == 0:
        # Still emit empty shards with only headers for consistency
        for i in range(shards):
            shard_path = _Path(out) / f"shard_{i:02d}.csv"
            with shard_path.open("w", newline="", encoding="utf-8") as f:
                w = _csv.writer(f)
                w.writerow(["url"])
        typer.echo(f"No URLs found. Wrote {shards} empty shard files to {out}")
        return

    base = n // shards
    rem = n % shards
    start = 0
    for i in range(shards):
        count = base + (1 if i < rem else 0)
        part = urls[start : start + count] if count > 0 else []
        shard_path = _Path(out) / f"shard_{i:02d}.csv"
        with shard_path.open("w", newline="", encoding="utf-8") as f:
            w = _csv.writer(f)
            w.writerow(["url"])
            for u in part:
                w.writerow([u])
        start += count
    typer.echo(f"Wrote {shards} shards to {out} (total URLs: {n})")


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
    min_price: int | None = typer.Option(None, "--min-price"),
    max_price: int | None = typer.Option(None, "--max-price"),
    property_type: str | None = typer.Option(None, "--type", help="detached|semi-detached|flat|terraced|bungalow"),
    start_page: int = typer.Option(1, "--start-page", min=1, help="First page number (1-indexed)"),
    pages: int = typer.Option(1, "--pages", min=1, help="How many pages to fetch from start-page"),
    all: bool = typer.Option(False, "--all", help="Ignore --pages and paginate until no more results"),
    out: str = typer.Option("./out", "--out"),
):
    cfg = load_config()
    setup_logging(cfg.log_level)
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
    import csv as _csv
    from pathlib import Path
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
    min_price: int | None = typer.Option(None, "--min-price"),
    max_price: int | None = typer.Option(None, "--max-price"),
    property_type: str | None = typer.Option(None, "--type"),
    start_page: int = typer.Option(1, "--start-page", min=1),
    pages: int = typer.Option(1, "--pages", min=1),
    all: bool = typer.Option(False, "--all"),
    out: str = typer.Option("./out", "--out"),
    format: str = typer.Option("csv", "--format"),
    max: int = typer.Option(50, "--max", min=1),
):
    cfg = load_config({"output_dir": out, "output_format": format})
    setup_logging(cfg.log_level)
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
    min_price: int | None = typer.Option(300000, "--min-price"),
    max_price: int | None = typer.Option(450000, "--max-price"),
    property_type: str | None = typer.Option(None, "--type", help="detached|semi-detached|flat|terraced|bungalow"),
    query: str | None = typer.Option("", "--query", help="Optional keyword filter"),
    slices: str | None = typer.Option(None, "--slices", help="Comma-separated slice names to run; 'null' or empty means all"),
    start_page: int | None = typer.Option(None, "--start-page", min=1, help="First page number (1-indexed)"),
    pages: int | None = typer.Option(None, "--pages", min=1, help="How many pages to fetch from start-page; omit for all"),
    list_only: bool = typer.Option(False, "--list-only", help="Only list available slice names and exit"),
    timeout: int = typer.Option(45, "--timeout", min=10, help="Per-page timeout seconds"),
    out: str = typer.Option("./out", "--out"),
):
    """Discover URLs across London using adaptive slicing (borough → district → price)."""
    cfg = load_config({"request_timeout_sec": timeout})
    setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    from rich.console import Console
    console = Console()

    async def _count(page, location_identifier: str, *, min_price: int | None, max_price: int | None, query: str = "", property_type: str | None = None) -> int:
        url = build_search_url(location_identifier=location_identifier, query=query, min_price=min_price, max_price=max_price, property_type=property_type, page=1)
        await page.goto(url, wait_until="domcontentloaded")
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

        async def count(self, location_identifier: str, *, min_price: int | None, max_price: int | None, query: str, property_type: str | None) -> int:
            return await _count(self.page, location_identifier, min_price=min_price, max_price=max_price, query=query, property_type=property_type)

    urls: list[str] = []

    async def _run():
        # If only listing slice names, avoid any network calls: print a static list from the cheat sheet
        if list_only:
            seen: set[str] = set()
            # Districts first
            for districts in BOROUGH_TO_DISTRICTS.values():
                for d in districts:
                    if d not in seen:
                        seen.add(d)
                        typer.echo(d)
            # Then borough names
            for b in borough_slices():
                if b not in seen:
                    seen.add(b)
                    typer.echo(b)
            return

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
                    parts = await partition(
                        initial_slice=s,
                        result_counter=counter,
                        district_provider=None,
                        query=query or "",
                        property_type=property_type,
                    )
                    final_slices.extend(parts)

            # De-duplicate slices by (location_identifier, price_min, price_max)
            deduped: list[Slice] = []
            seen_keys: set[tuple[str, int | None, int | None]] = set()
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
                    await page.goto(url, wait_until="domcontentloaded")
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

    import csv as _csv
    from pathlib import Path
    Path(out).mkdir(parents=True, exist_ok=True)
    out_csv = Path(out) / "discovered_adaptive_seeds.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["url"])
        for u in deduped:
            w.writerow([u])
    typer.echo(f"Wrote {len(deduped)} URLs to {out_csv}")


@app.command("plan-adaptive")
def plan_adaptive(
    query: str | None = typer.Option("", "--query", help="Optional keyword filter (for sizing)"),
    min_price: int | None = typer.Option(None, "--min-price"),
    max_price: int | None = typer.Option(None, "--max-price"),
    property_type: str | None = typer.Option(None, "--type", help="detached|semi-detached|flat|terraced|bungalow (for sizing)"),
    timeout: int = typer.Option(45, "--timeout", min=10, help="Per-page timeout seconds"),
    plan_dir: str = typer.Option("./out", "--plan-dir", help="Base directory where the plan txt will be saved"),
):
    """Compute the adaptive slice plan and save the ordered slices plus filters to a txt file.

    Output path format: <plan_dir>/<query-or-n>/<min-or-n>/<max-or-n>/<type-or-n>.txt
    """
    cfg = load_config({"request_timeout_sec": timeout})
    setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    def _slugify(value: str | None) -> str:
        v = (value or "").strip().lower()
        if not v:
            return "n"
        v = re.sub(r"\s+", "+", v)
        v = re.sub(r"[^a-z0-9+_-]", "-", v)
        v = re.sub(r"-+", "-", v).strip("-")
        return v or "n"

    async def _run():
        async with browser_context(cfg) as (_, __, page):
            async def _count(location_identifier: str, *, min_price: int | None, max_price: int | None) -> int:
                url = build_search_url(location_identifier=location_identifier, query=query or "", min_price=min_price, max_price=max_price, property_type=property_type, page=1)
                await page.goto(url, wait_until="domcontentloaded")
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

                async def count(self, location_identifier: str, *, min_price: int | None, max_price: int | None, query: str, property_type: str | None) -> int:
                    return await _count(location_identifier, min_price=min_price, max_price=max_price)

            final_slices: list[Slice] = []
            initial_slices: list[Slice] = []
            for b in borough_slices():
                s = Slice(level="borough", name=b, location_identifier="REGION^87490", price_min=min_price, price_max=max_price)
                initial_slices.append(s)
            counter = _Counter(page)
            for s in initial_slices:
                parts = await partition(initial_slice=s, result_counter=counter, district_provider=None, query=query or "", property_type=property_type)
                final_slices.extend(parts)

            # De-duplicate slices by (location_identifier, price_min, price_max)
            deduped: list[Slice] = []
            seen_keys: set[tuple[str, int | None, int | None]] = set()
            for s in final_slices:
                key = (s.location_identifier, s.price_min, s.price_max)
                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped.append(s)
            final_slices = deduped

            q_part = _slugify(query)
            min_part = str(min_price) if min_price is not None else "n"
            max_part = str(max_price) if max_price is not None else "n"
            t_part = _slugify(property_type)

            plan_path = Path(plan_dir) / q_part / min_part / max_part / f"{t_part}.txt"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            with plan_path.open("w", encoding="utf-8") as f:
                f.write("# adaptive slicer plan\n")
                f.write(f"# query: {query or ''}\n")
                f.write(f"# min_price: {min_price if min_price is not None else ''}\n")
                f.write(f"# max_price: {max_price if max_price is not None else ''}\n")
                f.write(f"# property_type: {property_type or ''}\n")
                f.write(f"# generated_at: {datetime.now(UTC).isoformat()}\n")
                for s in final_slices:
                    f.write(f"{s.name}|{s.location_identifier}|{s.price_min if s.price_min is not None else ''}|{s.price_max if s.price_max is not None else ''}\n")

            typer.echo(str(plan_path))

    asyncio.run(_run())


@app.command("discover-from-plan")
def discover_from_plan(
    plan_file: str = typer.Option(..., "--plan-file", help="Path to plan txt generated by plan-adaptive"),
    start_slice: int | None = typer.Option(None, "--start-slice", min=1, help="1-based slice index to start from; omit for first"),
    start_page: int | None = typer.Option(None, "--start-page", min=1, help="1-based page index per slice; omit for 1"),
    pages: int | None = typer.Option(None, "--pages", min=1, help="How many pages per slice from start; omit for all until empty"),
    timeout: int = typer.Option(45, "--timeout", min=10, help="Per-page timeout seconds"),
    out: str = typer.Option("./out", "--out"),
    per_slice_dir: str | None = typer.Option(None, "--per-slice-dir", help="If set, write CSV per slice: rightmove_id,url,slicer_name"),
    slice_count: int | None = typer.Option(None, "--slice-count", min=1, help="Process N slices starting from start-slice"),
    skip_merged: bool = typer.Option(False, "--skip-merged", help="If true, do not write merged discovered_adaptive_seeds.csv"),
):
    """Read a slice plan and collect listing URLs for the selected range of slices in order."""
    cfg = load_config({"request_timeout_sec": timeout})
    setup_logging(cfg.log_level)
    assert_personal_use_banner()

    if not discovery_enabled():
        typer.echo("Discovery is disabled. Set ALLOW_DISCOVERY=true and create consent.txt in project root to enable.")
        raise typer.Exit(code=2)

    path = Path(plan_file)
    if not path.exists():
        typer.echo(f"Plan file not found: {plan_file}")
        raise typer.Exit(code=1)

    # Parse header and slices
    q: str = ""
    t: str | None = None
    lo: int | None = None
    hi: int | None = None
    slices_data: list[tuple[str, str, int | None, int | None]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# query:"):
                q = line.split(":", 1)[1].strip()
            elif line.lower().startswith("# min_price:"):
                v = line.split(":", 1)[1].strip()
                lo = int(v) if v else None
            elif line.lower().startswith("# max_price:"):
                v = line.split(":", 1)[1].strip()
                hi = int(v) if v else None
            elif line.lower().startswith("# property_type:"):
                v = line.split(":", 1)[1].strip()
                t = v or None
            continue
        parts = re.split(r"[|\t]", line)
        if len(parts) >= 4:
            name = parts[0].strip()
            loc = parts[1].strip()
            pmin = int(parts[2]) if parts[2].strip() else None
            pmax = int(parts[3]) if parts[3].strip() else None
            slices_data.append((name, loc, pmin, pmax))

    if not slices_data:
        typer.echo("No slices found in plan file.")
        raise typer.Exit(code=1)

    start_idx = (start_slice or 1) - 1
    if start_idx < 0 or start_idx >= len(slices_data):
        typer.echo(f"start-slice out of range. Plan has {len(slices_data)} slices.")
        raise typer.Exit(code=1)

    urls: list[str] = []

    async def _run():
        console = Console()
        async with browser_context(cfg) as (_, __, page):
            end_idx = len(slices_data)
            if slice_count is not None:
                end_idx = min(len(slices_data), start_idx + slice_count)
            for i in range(start_idx, end_idx):
                name, loc, pmin, pmax = slices_data[i]
                p = start_page or 1
                console.log(f"[{i+1}/{len(slices_data)}] Collecting {name} price=[{pmin},{pmax})")
                slice_urls: list[str] = []
                while True:
                    if loc.startswith("OUTCODE^"):
                        outcode = loc.split("^", 1)[1]
                        url = f"https://www.rightmove.co.uk/property-for-sale/{outcode}.html?searchType=SALE&index={(p-1)*24}"
                        if pmin is not None:
                            url += f"&minPrice={pmin}"
                        if pmax is not None:
                            url += f"&maxPrice={pmax}"
                    else:
                        url = build_search_url(location_identifier=loc, query=q or "", min_price=pmin, max_price=pmax, property_type=t, page=p)
                    await page.goto(url, wait_until="domcontentloaded")
                    try:
                        await page.get_by_role("button", name="Accept all").click(timeout=1500)
                    except Exception:
                        pass
                    try:
                        await page.locator('[data-testid="propertyCard-link"]').first.wait_for(timeout=5000)
                    except Exception:
                        pass
                    content = await page.content()
                    page_urls = extract_listing_urls_from_search(content)
                    console.log(f"Slice {name} page {p}: found {len(page_urls)} URLs")
                    if not page_urls:
                        # Save debug HTML
                        try:
                            path_out = Path(out)
                            path_out.mkdir(parents=True, exist_ok=True)
                            (path_out / f"debug_search_{name}_p{p}.html").write_text(content, encoding="utf-8")
                        except Exception:
                            pass
                        break
                    slice_urls.extend(page_urls)
                    if pages is not None and p >= (start_page or 1) + pages - 1:
                        break
                    p += 1
                    polite_sleep(cfg.min_delay_sec, cfg.max_delay_sec)

                # De-duplicate per-slice and optionally write CSV with id and slicer name
                slice_urls = dedupe_preserve_order(slice_urls)
                if per_slice_dir:
                    Path(per_slice_dir).mkdir(parents=True, exist_ok=True)
                    safe_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", name)
                    slice_csv = Path(per_slice_dir) / f"slice_{i+1:03d}_{safe_name}.csv"
                    import csv as _csv
                    with slice_csv.open("w", newline="", encoding="utf-8") as f:
                        w = _csv.writer(f)
                        w.writerow(["rightmove_id", "url", "slicer_name"])
                        for u in slice_urls:
                            try:
                                rid = extract_rightmove_id(u)
                            except Exception:
                                continue
                            w.writerow([rid, u, name])
                    console.log(f"Wrote slice CSV: {slice_csv}")
                urls.extend(slice_urls)

    asyncio.run(_run())

    if not skip_merged:
        deduped = dedupe_preserve_order(urls)
        Path(out).mkdir(parents=True, exist_ok=True)
        out_csv = Path(out) / "discovered_adaptive_seeds.csv"
        import csv as _csv
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = _csv.writer(f)
            w.writerow(["url"])
            for u in deduped:
                w.writerow([u])
        typer.echo(f"Wrote {len(deduped)} URLs to {out_csv}")


if __name__ == "__main__":
    app()



