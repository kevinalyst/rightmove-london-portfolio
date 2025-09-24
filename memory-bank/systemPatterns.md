System Patterns

Architecture overview
- Modules (portfolio scope)
  - `src/rightmove_scraper/*`: discovery + scrape CLI used by `make scrape10`.
  - `pipeline/local_rightmove_transform.py`: local transform, builds LOCATION, computes ZONE, reverse‑geocodes ADDRESS.
  - `docs/*`: static mini chatbot (dark UI), wiring guide, assets.
  - `backend/*`: serverless‑first stubs (Cloudflare Worker) for payment + chat token + chat proxy.

Control flow (A/B/C)
1) A: `make scrape10` → discover/search + scrape 10 listings → `data/raw/listings_10.{csv,ndjson}`.
2) B: `make transform10` → local enrich (LOCATION, ZONE, ADDRESS) → `data/processed/listings_10_transformed.{csv,parquet}`.
3) C: `/docs` mini chatbot → optional backend wiring (no secrets on frontend).

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
- Conservative scraping defaults; `ALLOW_DISCOVERY=true` and `consent.txt` gate discovery.
- Local transform only; no Snowflake required for A/B demos.
- Secrets live only in backend; frontend uses `docs/config.json` placeholders.
