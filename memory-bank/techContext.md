Tech Context

Languages & runtime
- Python 3.11+

Core dependencies
- Playwright (browser automation)
- Pydantic (models/validation)
- Typer[all] (CLI)
- Pandas, PyArrow (I/O)
- Tenacity (retries)
- Rich (logging/UI)
- python-dotenv, lxml

Dev dependencies
- Pytest, pytest-cov, ruff

CLI & packaging
- Package name: `rightmove-scraper` (entry: `rightmove_scraper.cli:app`).
- Installed via `pip install -e '.[dev]'`; CLI command `rightmove-scraper`.

Environment variables (see README for example `.env`)
- `USER_AGENT`, `HEADLESS`, `MAX_CONCURRENCY`, `REQUEST_TIMEOUT`, delays (`MIN_DELAY_SEC`, `MAX_DELAY_SEC`), `ALLOW_DISCOVERY`, `OUTPUT_DIR`, `OUTPUT_FORMAT`, `LOG_LEVEL`.

Filesystem conventions
- Plans: `out/<q>/<min>/<max>/<type>.txt`
- Per-slice CSVs: `out/per_slice/`
- Merged discovery: `out/discovered_adaptive_seeds.csv`
- Final scraped listings: `out/listings.csv` (+ batches in `out/batches/`)

Containerization
- Dockerfile based on `python:3.11-slim-bookworm`; installs package, Playwright with deps, optional GCS client.
- Default envs in image: `OUTPUT_DIR=/workspace/out`, `SHARDS_DIR=/app/shards`, `MAX_CONCURRENCY=1`, `HEADLESS=true`, `REQUEST_TIMEOUT=45`.
- Entry: `python jobs/entrypoint.py` (Cloud Run Job friendly).

Local setup quickstart
1) Create venv; install package and Playwright browsers.
2) Create `.env` and `consent.txt`.
3) Run scripts: slicer → discover → scrape.
