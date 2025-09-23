System Patterns

Architecture overview
- Modules
  - `slicer.py`: Creates adaptive slice plans (REGION → OUTCODE → price bands) sized to fit under pagination caps.
  - `discovery.py`: Iterates slice pages, reads result counts, collects canonical listing URLs.
  - `scrape_listing.py`: Orchestrates listing fetch + parse using Playwright and extractors.
  - `extractors.py`: DOM/HTML parsing and normalization of listing fields.
  - `normalize.py`: Value cleaning (e.g., price parsing, text normalization).
  - `browser.py`: Playwright context/page creation with timeouts and headless config.
  - `config.py`/`compliance.py`: Env var loading, guardrails (consent gate, delays, concurrency).
  - `datastore.py`: Batch writes and final merges to CSV/Arrow.
  - `logging_setup.py`: Rich logging configuration.
  - `cli.py`: Typer CLI entry mapping to plan/discover/scrape commands.
  - `jobs/entrypoint.py`: Sharded execution for Cloud Run Job.

Control flow (plan → discover → scrape)
1) Plan: write plan file under `out/<q>/<min>/<max>/<type>.txt`.
2) Discover: write per‑slice CSVs to `out/per_slice/` and merged `out/discovered_adaptive_seeds.csv`.
3) Scrape: read seeds, optionally resume from `rightmove_id`, batch‑save every N, final merge to `out/listings.csv`.

Reliability & compliance
- Navigation waits for `domcontentloaded`, then for property cards to render.
- Retries with exponential backoff (`tenacity`), randomized delays between actions.
- Low default concurrency; HEADLESS true by default; configurable timeouts.
- Debug artifacts for empty pages (e.g., `out/debug_search_<SLICE>_p<PAGE>.html`).

Data model themes (non‑exhaustive)
- Identification: `url`, `rightmove_id`.
- Pricing: `price_text`, `price_value`, `price_currency`.
- Property meta: `property_type`, `property_title`, `bedrooms`, `bathrooms`, `sizes`, `tenure`.
- Agent & listing: `estate_agent`, `key_features`, `description`.
- Amenities/flags: `council_tax`, `parking`, `garden`, `accessibility` (fields may be sparse).

Operational patterns
- Batch writes during scrape, final merge at end; resumable by ID threshold.
- Shard input seeds to parallelize across Cloud Run Job tasks with guarded per‑task concurrency.
