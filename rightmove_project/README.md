# Rightmove Personal Research Scraper (Python)

Important: This tool is for personal, non-commercial research only. Respect the Rightmove Terms of Use and robots, and scrape gently.

Compliance banner
- Strict politeness defaults: random delays, retries; resource blocking for speed
- The recommended/default workflow uses discovery (search → scrape). Manual seeds are optional.
- To run discovery, set ALLOW_DISCOVERY=true and create a local file consent.txt in the project root.

Quickstart (discovery-first, London)
1) Create and activate Python 3.11+ environment
   - macOS zsh example
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -U pip

2) Install package and browsers
   - quote extras in zsh
     pip install -e '.[dev]'
     python -m playwright install --with-deps

3) Configure .env and consent (enables discovery)
   cp .env.example .env
   # edit .env: set ALLOW_DISCOVERY=true, adjust HEADLESS, delays, etc.
   touch consent.txt

4) Discover London listings (writes out/discovered_seeds.csv)
   - London region is pre-set. Filter examples:
     PYTHONPATH=$PWD/src python -m rightmove_scraper.cli discover-search \
       --query "" \
       --min-price 300000 --max-price 1200000 \
       --type flat \
       --pages 1 \
       --out ./out

5) Scrape discovered URLs (writes out/listings.csv)
   - Use modest concurrency for reliability; increase timeout if needed
     PYTHONPATH=$PWD/src python -m rightmove_scraper.cli scrape-search \
       --query "" \
       --min-price 300000 --max-price 1200000 \
       --type flat \
       --pages 1 \
       --out ./out --format csv --max 25

Quickstart (optional manual seeds)
1) Create seeds.csv with a header `url` and property URLs
   url\nhttps://www.rightmove.co.uk/properties/119387291
2) Scrape the seeds
   PYTHONPATH=$PWD/src python -m rightmove_scraper.cli scrape-seeds \
     --input ./seeds.csv \
     --out ./out \
     --format csv \
     --max 5

Environment (.env)
- USER_AGENT: Optional override
- HEADLESS=true
- MAX_CONCURRENCY=1
- REQUEST_TIMEOUT=30
- MIN_DELAY_SEC=2.0
- MAX_DELAY_SEC=5.0
- ALLOW_DISCOVERY=false
- OUTPUT_DIR=./out
- OUTPUT_FORMAT=csv (csv|parquet|sqlite)
- LOG_LEVEL=INFO

CLI
- discover-search (default flow) — find London listing URLs with filters
- scrape-search (default flow) — scrape discovered listing URLs
- scrape-seeds (optional) — scrape explicit URLs from a file
- dump-snapshots — save raw HTML pages for debugging/fixtures
- validate — basic column check for generated CSV

Discovery notes
- Region: London (locationIdentifier REGION^87490) is built-in.
- Filters: use --min-price/--max-price, --type (flat|detached|semi-detached|terraced|bungalow), and --query.
- Output: discovery writes `out/discovered_seeds.csv` with a header `url`.

Testing
- pytest
- Unit tests run against HTML snapshots in tests/fixtures/html/

ComplianceGuard
- On startup, a visible warning prints.
- Programmatic discovery remains disabled unless you have both env ALLOW_DISCOVERY=true and a local consent.txt.

Notes
- If a listing is removed by the agent, we return a partial record with description="Removed by agent".
- “Ask agent” values are preserved as-is.

Performance tips
- Keep concurrency modest (e.g., 2) and timeouts around 20–30s for reliability.
- We block images/media/fonts to speed up page loads and auto-accept cookies when present.
- If you hit intermittent timeouts, re-run failed URLs with lower concurrency or a higher timeout.


