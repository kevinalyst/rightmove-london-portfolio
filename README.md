# Rightmove Personal Research Scraper (Python)

Important: This tool is for personal, non-commercial research only. Respect the Rightmove Terms of Use and robots, and scrape gently.

### 1) Compliance banner
- Personal, non‑commercial use only.
- Be polite: the app inserts random delays, runs low concurrency, and auto‑accepts the cookie banner when present.
- Discovery is disabled by default. To enable, set `ALLOW_DISCOVERY=true` in `.env` and create a `consent.txt` file in the project root.

### 2) Quickstart

- 2.1 Environment setup and package install
  - Create and activate a Python 3.11+ venv (macOS zsh example):
```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install -e '.[dev]'
     python -m playwright install --with-deps
```
  - Create `.env` and `consent.txt`:
```bash
cat > .env << 'EOF'
USER_AGENT=
     HEADLESS=true
     MAX_CONCURRENCY=1
REQUEST_TIMEOUT=45
     MIN_DELAY_SEC=2.0
     MAX_DELAY_SEC=5.0
     ALLOW_DISCOVERY=true
     OUTPUT_DIR=./out
OUTPUT_FORMAT=csv
     LOG_LEVEL=INFO
EOF
   touch consent.txt
```

- 2.2 Generate an adaptive slice plan (`scripts/adaptive_slicer.sh`)
  - Prompts: keywords query (null for none), min/max price (null for none), property type (null for all).
  - Produces a plan file at `out/<query-or-n>/<min-or-n>/<max-or-n>/<type-or-n>.txt`.
  - The plan file includes your filters (header) and an ordered list of slices, one per line:
    `slicer_name|location_identifier|min_price|max_price`.
```bash
./scripts/adaptive_slicer.sh
# Example output: out/n/300000/450000/n.txt or out/n/n/n/n.txt
```

- 2.3 Discover URLs from the plan (`scripts/discover_urls.sh`)
  - Prompts for the plan path and optional pagination start/page limits.
  - Discovers each slice in order, writing per‑slice CSVs to `out/per_slice/` with columns:
    `rightmove_id,url,slicer_name`.
  - After all slices, merges and de‑duplicates URLs into `out/discovered_adaptive_seeds.csv`.
```bash
./scripts/discover_urls.sh
# Per-slice outputs: out/per_slice/slice_001_<NAME>.csv (rightmove_id,url,slicer_name)
# Merged:            out/discovered_adaptive_seeds.csv (header: url)
```

- 2.4 Scrape listings (`scripts/run_scrape.sh`)
  - Prompts for “Start from Rightmove ID (null for first)” to resume mid‑run.
  - Scrapes URLs from `out/discovered_adaptive_seeds.csv`, prints live progress, and batch‑saves every 100 records to `out/batches/`. The final merged output is written to `out/listings.csv`.
```bash
./scripts/run_scrape.sh
# Progress prints as it scrapes; batches land in out/batches/, final in out/listings.csv
```

### 3) Rightmove pagination cap and how the adaptive slicer bypasses it
- Rightmove limits browseable results for a single search to ~1,050 items (24 per page → ~44 pages). Beyond that, listings aren’t accessible by pagination alone.
- The adaptive slicer avoids this by partitioning the search space into non‑overlapping “slices” that each fall under the cap:
  - Start with London region (REGION^87490).
  - Split into postcode districts (OUTCODE^… like E14, SW1, W11, etc.).
  - If a district still exceeds the cap, split its price range into non‑overlapping bands (e.g., [300k,375k) and [375k,450k)), repeating until each slice ≤ 1,000.
- Sizing is done by loading real search pages headlessly and parsing result counts from the DOM/scripts. We navigate with `domcontentloaded` and then wait for property cards to render for robustness.
- Finally, per‑slice discovery collects listing URLs, and the app merges and de‑duplicates them by canonical URL (and later by `rightmove_id` when writing scraped records).

### 4) Common troubleshooting
- “Warning: ALLOW_DISCOVERY is not 'true'”
  - Ensure `.env` has `ALLOW_DISCOVERY=true` and there is a `consent.txt` file in the project root.

- Playwright not installed / browsers missing
  - Run: `python -m playwright install --with-deps` (once per environment).

- Timeouts while discovering
  - We navigate using `domcontentloaded` and then wait for property cards, which is more reliable than waiting for “network idle”. If your network is slow, increase `REQUEST_TIMEOUT` in `.env` (e.g., 60–90) and consider bumping delays (e.g., `MIN_DELAY_SEC=3.0`, `MAX_DELAY_SEC=7.0`).
  - A debug HTML is written on empty pages: `out/debug_search_<SLICE>_p<PAGE>.html`.

- Very few or empty per‑slice results
  - Some OUTCODE slices (or sub‑districts) legitimately contain few listings for the chosen filters. Verify your plan file filters and consider setting min/max price to narrow sub‑slices.

- Anti‑bot mitigations (intermittent blocks)
  - Set a desktop `USER_AGENT` in `.env`, keep concurrency low (`MAX_CONCURRENCY=1–2`), and allow generous delays.
  - You can set `HEADLESS=false` temporarily for local debugging.

- Resume scraping from a specific listing
  - Use `./scripts/run_scrape.sh` and enter the starting Rightmove ID when prompted. The script filters the seeds to IDs ≥ the value you provide.

- Where are outputs?
  - Plans: `out/<q>/<min>/<max>/<type>.txt`
  - Per‑slice discovery CSVs: `out/per_slice/`
  - Merged discovery: `out/discovered_adaptive_seeds.csv`
  - Scraped listings: `out/listings.csv` (+ batches in `out/batches/`)
