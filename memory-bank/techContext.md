Tech Context

Languages & runtime
- **Python 3.11+** (scraper, pipelines)
- **JavaScript ES6+** (Cloudflare Worker, frontend)

Core dependencies
**Python**:
- Playwright (browser automation)
- Pydantic (models/validation)
- Typer (CLI)
- Pandas, PyArrow (I/O)
- Tenacity (retries)
- Rich (logging/UI)
- geopy (reverse geocoding)
- python-dotenv, lxml

**JavaScript/Frontend**:
- Vega v5 (visualization runtime)
- Vega-Lite v5 (grammar of graphics)
- Vega-Embed v6 (embedder for web)
- Browser-native: EventSource (SSE), fetch, DOM

Dev dependencies
- Pytest, pytest-cov, ruff, black, mypy, pre-commit, mkdocs-material

CLI & packaging
- Package name: `rightmove-scraper` (entry: `rightmove_scraper.cli:app`).
- Installed via `pip install -e '.[dev]'`; CLI command `rightmove-scraper`.

Environment variables
**Scraper**:
- `USER_AGENT`, `HEADLESS`, `MAX_CONCURRENCY`, `REQUEST_TIMEOUT`, `MIN_DELAY_SEC`, `MAX_DELAY_SEC`, `ALLOW_DISCOVERY`, `OUTPUT_DIR`, `OUTPUT_FORMAT`, `LOG_LEVEL`.

**Worker** (Cloudflare Secrets + wrangler.toml vars):
- `SNOWFLAKE_PAT_TOKEN` (secret)
- `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_AGENT_DATABASE`, `SNOWFLAKE_AGENT_SCHEMA`, `SNOWFLAKE_AGENT_NAME`
- `SNOWFLAKE_SEARCH_DATABASE`, `SNOWFLAKE_SEARCH_SCHEMA`, `SNOWFLAKE_SEARCH_SERVICE`
- `ALLOW_ORIGIN` (CORS whitelist)

Filesystem conventions
- Raw sample: `data/raw/listings_10.{csv,ndjson}`
- Processed: `data/processed/listings_10_transformed.{csv,parquet}`

Cloudflare Worker stack
- Runtime: Cloudflare Workers (V8 isolates, serverless)
- Deployment: `wrangler deploy` (auto from GitHub push)
- Observability: `wrangler tail` for logs, correlation IDs
- Endpoints:
  - `GET /api/health` → Config check
  - `GET /api/chat/stream` → SSE streaming (analyst mode)
  - `POST /api/chat` → JSON batch (search mode)
  - `OPTIONS /api/*` → CORS preflight

Frontend architecture
- SPA: Vanilla JavaScript, no framework
- Styling: Custom CSS with dark theme
- Charts: Vega-Lite (declarative specs from Cortex)
- Streaming: EventSource API for real-time updates
- State management: Simple state machine (idle/querying/error)

Containerization
- Dockerfile based on `python:3.11-slim-bookworm`; installs package, Playwright with deps, optional GCS client.
- Default envs in image: `OUTPUT_DIR=/workspace/out`, `SHARDS_DIR=/app/shards`, `MAX_CONCURRENCY=1`, `HEADLESS=true`, `REQUEST_TIMEOUT=45`.
- Entry: `python jobs/entrypoint.py` (Cloud Run Job friendly).

Local setup quickstart
1) `make setup` (venv deps, Playwright, pre-commit).
2) Create `.env` and `consent.txt`.
3) `make scrape10`, `make transform10` (portfolio demo flows).
