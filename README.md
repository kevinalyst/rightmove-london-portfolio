### Compliance banner

- **Personal use only**: This scraper is for personal, non-commercial research.
- **Respect the site**: Follow Rightmove Terms of Use and robots. Scrape gently.
- **Guardrails**: Discovery is disabled unless both `ALLOW_DISCOVERY=true` in `.env` and a `consent.txt` file exist in the project root.

### Quickstart

- **1) Environment setup and install**
  - Create and activate a Python 3.11+ virtualenv (macOS zsh example):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```
  - Install package and Playwright browsers:
```bash
pip install -e '.[dev]'
python -m playwright install --with-deps
```
  - Configure `.env` and consent:
```bash
nano .env
# Required to enable discovery
ALLOW_DISCOVERY=true
# Optional tuning
HEADLESS=true
REQUEST_TIMEOUT=45
MIN_DELAY_SEC=2.0
MAX_DELAY_SEC=5.0
OUTPUT_DIR=./out
OUTPUT_FORMAT=csv
LOG_LEVEL=INFO
# USER_AGENT=Your desktop UA string (optional)

touch consent.txt
```

- **2) Use `scripts/adaptive_slicer.sh` (plan generator)**
  - This prompts for filters (query, min/max price, property type) and generates a slice plan that partitions London into non-overlapping slices.
  - Plan is saved under `out/<query-or-n>/<min-or-n>/<max-or-n>/<type-or-n>.txt`, for example: `out/n/300000/450000/n.txt` or `out/n/n/n/n.txt` when filters are null.
  - Output: prints the plan filepath; keep it for the next step.
```bash
./scripts/adaptive_slicer.sh
```

- **3) Use `scripts/discover_urls.sh` (discover per slice + merge)**
  - Prompts:
    - **Path to adaptive plan txt**: the plan produced above
    - **Start slice index**: 1-based integer (e.g., 1). Not a name.
    - **Start page / Pages per slice**: leave blank to discover until the true end per slice
  - Behavior:
    - Uses canonical Rightmove search URLs with your filters.
    - Bounds pagination by the live `resultCount` from page 1 to avoid “ghost pages”.
    - Writes per-slice CSVs to `out/per_slice/…` with columns: `rightmove_id,url,slicer_name`.
    - Merges de-duplicated URLs across slices into `out/discovered_adaptive_seeds.csv`.
```bash
./scripts/discover_urls.sh
```

- **4) Use `scripts/run_scrape.sh` (scrape listings with resume + batches)**
  - Prompts:
    - **Start from Rightmove ID**: enter a numeric ID to resume from, or leave blank to start from the first URL.
  - Behavior:
    - Reads `out/discovered_adaptive_seeds.csv` and scrapes listing pages.
    - Shows progress and saves a batch output every 100 listings to `out/batches/`.
    - Writes aggregated `out/listings.csv` when done.
```bash
./scripts/run_scrape.sh
```

### Rightmove pagination cap and how we bypass it

- **The cap**: Rightmove only exposes ~1,050 browsable results per query. Practically, this manifests as a limited number of paginated pages even if more listings exist.
- **Our approach (adaptive slicer)**:
  - **CAP per slice**: We target ≤1,000 results per slice (`CAP=1000`).
  - **Partitioning strategy**:
    1) Start from London borough coverage; count results for each.
    2) If a borough slice exceeds CAP, partition by postcode districts (`OUTCODE^…`).
    3) If a district still exceeds CAP, split the price range into non-overlapping bands (5k granularity) and recurse until ≤ CAP.
  - **Counting**: We drive a headless browser to the canonical Rightmove search URL with your filters, wait for `domcontentloaded`, and extract `resultCount` from the DOM/scripts.
  - **Discovery**: For each final slice, we paginate using the canonical search URL and stop at `ceil(resultCount/24)` pages, de-duplicating URLs by property ID.

### Common troubleshooting

- **Discovery disabled**: Ensure `.env` has `ALLOW_DISCOVERY=true` and `consent.txt` exists.
- **“.env parse” error**: The file must contain `KEY=VALUE` lines only. Remove stray text or use `#` for comments. Do not paste prose into `.env`.
- **Playwright not installed**: Run `python -m playwright install --with-deps`.
- **Timeouts on discovery**: We use `domcontentloaded` plus an explicit wait for cards. If your network is slow, raise `REQUEST_TIMEOUT` in `.env` (e.g., 60–90).
- **Deep pages return few/zero URLs**: The tool now uses canonical URLs and bounds pagination by the live `resultCount`, avoiding ghost pages. If you still see issues, re-run with a fresh plan or allow min/max to be null so the slicer can price-split more aggressively.
- **Start slice input**: It must be a 1-based integer index, not a slice name like `WC2`.
- **Resuming scrape**: In `run_scrape.sh`, provide a `rightmove_id` present in your seeds file. The scraper will filter seeds `>=` that ID and continue.
- **Batch outputs**: Scrape batches are written every 100 records into `out/batches/` for resilience.
