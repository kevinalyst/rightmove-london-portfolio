# Rightmove Personal Research Scraper (Python)

Important: This tool is for personal, non-commercial research only. Respect the Rightmove Terms of Use and robots, and scrape gently.

Compliance banner
- Strict politeness defaults: single worker, random delays, retries, no parallel fetches
- Manual seed URLs only by default. Programmatic discovery is disabled unless you explicitly allow it and add local consent.
- To enable discovery, you must: set ALLOW_DISCOVERY=true and create a local file consent.txt in the project root.

Quickstart
1) Create and activate Python 3.11+ environment
2) Install:
   pip install -e '.[dev]'
   python -m playwright install --with-deps
3) Prepare seeds.csv:
   url\nhttps://www.rightmove.co.uk/properties/119387291
4) Run scraper:
   python -m rightmove_scraper.cli scrape-seeds --input ./seeds.csv --out ./out --format csv --max 5

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
- scrape-seeds --input seeds.csv --out ./out --format csv --max 25
- dump-snapshots --input seeds.csv --limit 5
- validate --file out/listings.csv

London discovery (gated)
- Discovery is OFF by default. To enable:
  - Set ALLOW_DISCOVERY=true in .env
  - Ensure a file named consent.txt exists in this folder
- Discover London listing URLs without scraping them:
  PYTHONPATH=$PWD/src python -m rightmove_scraper.cli discover-search \
    --query "" \
    --min-price 300000 --max-price 800000 \
    --type flat \
    --pages 1 \
    --out ./out
  This writes ./out/discovered_seeds.csv with a header `url`.
- Scrape discovered listings directly (London-only search):
  PYTHONPATH=$PWD/src python -m rightmove_scraper.cli scrape-search \
    --query "" \
    --min-price 300000 --max-price 800000 \
    --type flat \
    --pages 1 \
    --out ./out --format csv --max 25

Testing
- pytest
- Unit tests run against HTML snapshots in tests/fixtures/html/

ComplianceGuard
- On startup, a visible warning prints.
- Programmatic discovery remains disabled unless you have both env ALLOW_DISCOVERY=true and a local consent.txt.

Notes
- If a listing is removed by the agent, we return a partial record with description="Removed by agent".
- “Ask agent” values are preserved as-is.


