# Rightmove London Property Scraper

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
   - Create .env
     nano .env
   - edit .env: set ALLOW_DISCOVERY=true, adjust HEADLESS, delays, etc.
     USER_AGENT: Optional override
     HEADLESS=true
     MAX_CONCURRENCY=1
     REQUEST_TIMEOUT=30
     MIN_DELAY_SEC=2.0
     MAX_DELAY_SEC=5.0
     ALLOW_DISCOVERY=true
     OUTPUT_DIR=./out
     OUTPUT_FORMAT=csv (csv|parquet|sqlite)
     LOG_LEVEL=INFO
4) Go to Rightmove.com and search for the property the way you used to be, and on the search results page:
<img width="1401" height="264" alt="Screenshot 2025-08-25 at 22 11 24" src="https://github.com/user-attachments/assets/2f356e13-df32-4d44-a00a-8c28be0aa142" />
   - The results on the left, if that number > 1000, then you should turn on the adaptive slicer later in the interactive script; otherwise, you should leave that off for better performance
   - 'Add keyword' corresponding to the query in the interactive script
   - min/max price and property type are the same as the filter above
5) Run interactive script
   - One step to run discovery (adaptive or simple) and then scrape
     ./scripts/run_discover_and_scrape.sh
   - Prompts: use adaptive slicer(see explanation below, recommend on)
              query (null for none),
              min/max price(null for none),
              property type(null for all)
      
     Output: discovered CSVs in ./out and scraped listings file in ./out

   Background run on a VM and check progress:
   - Start (example: adaptive slicer for N1, page 1 only). Edit inputs as needed:
     ALLOW_DISCOVERY=true nohup bash -lc 'printf "y\n\n300000\n450000\n\nN1\n1\n1\n" | ./scripts/run_discover_and_scrape.sh' > ./out/run.log 2>&1 & echo $! > ./out/run.pid
   - Check progress (tail the log):
     tail -f ./out/run.log


CLI
- discover-search (default flow) — find London listing URLs with filters
- discover-adaptive — adaptive slicing discovery (borough → district → price)
- scrape-search (default flow) — scrape discovered listing URLs
- scrape-seeds (optional) — scrape explicit URLs from a file
- dump-snapshots — save raw HTML pages for debugging/fixtures
- validate — basic column check for generated CSV

Discovery notes
- Region: London (locationIdentifier REGION^87490) is built-in.
- Filters: use --min-price/--max-price, --type (flat|detached|semi-detached|terraced|bungalow), and --query.
- Output: discovery writes `out/discovered_seeds.csv` with a header `url`.

Adaptive discovery (slicer)
- Goal: bypass Rightmove's ~1,050 browsable results cap per query by splitting into non-overlapping slices and merging + de-duping at the end.
- Keep filters identical across slices (except the dimension being split). CAP is 1,000 results per slice.
- Steps:
  1) Start at London region. If total results ≤ 1,000, paginate and collect.
  2) If > 1,000, split by postcode districts (OUTCODE^ codes) from a practical cheat sheet (e.g., E14, SW1, W11…). Districts are narrower and reduce volume.
  3) If a district still exceeds 1,000, split the price range into non-overlapping sub-bands (e.g., [300k, 375k) and [375k, 450k)). Repeat until ≤ 1,000.
- Counting: we read the total results from the page DOM/scripts to decide when to split.
- Merge + de-dupe: after collecting all slices, we merge and de-duplicate by Rightmove property ID (from the URL). Output is `out/discovered_adaptive_seeds.csv`.

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


