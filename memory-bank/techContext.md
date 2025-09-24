Tech Context

Languages & runtime
- Python 3.11+

Core dependencies
- Playwright (browser automation)
- Pydantic (models/validation)
- Typer (CLI)
- Pandas, PyArrow (I/O)
- Tenacity (retries)
- Rich (logging/UI)
- geopy (reverse geocoding)
- python-dotenv, lxml

Dev dependencies
- Pytest, pytest-cov, ruff, black, mypy, pre-commit, mkdocs-material

CLI & packaging
- Package name: `rightmove-scraper` (entry: `rightmove_scraper.cli:app`).
- Installed via `pip install -e '.[dev]'`; CLI command `rightmove-scraper`.

Environment variables
- `USER_AGENT`, `HEADLESS`, `MAX_CONCURRENCY`, `REQUEST_TIMEOUT`, `MIN_DELAY_SEC`, `MAX_DELAY_SEC`, `ALLOW_DISCOVERY`, `OUTPUT_DIR`, `OUTPUT_FORMAT`, `LOG_LEVEL`.

Filesystem conventions
- Raw sample: `data/raw/listings_10.{csv,ndjson}`
- Processed: `data/processed/listings_10_transformed.{csv,parquet}`

Containerization
- Dockerfile based on `python:3.11-slim-bookworm`; installs package, Playwright with deps, optional GCS client.
- Default envs in image: `OUTPUT_DIR=/workspace/out`, `SHARDS_DIR=/app/shards`, `MAX_CONCURRENCY=1`, `HEADLESS=true`, `REQUEST_TIMEOUT=45`.
- Entry: `python jobs/entrypoint.py` (Cloud Run Job friendly).

Local setup quickstart
1) `make setup` (venv deps, Playwright, pre-commit).
2) Create `.env` and `consent.txt`.
3) `make scrape`, optionally `make geocode`, `make load`, `make docs`.
