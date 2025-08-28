# London Property Market Portfolio — Sub‑Project 1: Data Mining (Rightmove Scraper)

Important: This project is for personal, non‑commercial research only. Respect the Rightmove Terms of Use and robots, and scrape gently.

## Portfolio Overview
- 1) Data mining (this repo): robust Rightmove scraper that plans and discovers at scale, then scrapes listing details.
- 2) Data processing & database: clean/validate and load to Cloud SQL (curated schema for analytics).
- 3) BI dashboard: connect SQL to Power BI and build an interactive market insight product.

---

## Project Overview

#### Key challenge: Rightmove’s hard pagination cap
- Rightmove caps browseable results at ~1,050 per query (~42 pages, ~25/listings per page). A single broad query cannot enumerate all listings.

#### Solution: Adaptive slicer (plan → discover → scrape)
- Plan slices that bypass the cap by splitting the search into non‑overlapping parts:
  - Start with London region (REGION^87490)
  - Split into postcode districts (OUTCODE^… like E14, SW1, W11)
  - If a district still exceeds the cap, split its price range into non‑overlapping bands until each slice ≤ ~1,000
- Each slice is discovered (URLs collected) and then scraped for full details.

#### Scale-out execution (100 shards → Cloud Run)
- Discovered ~27k unique property URLs, then split into 100 shards.
- Deployed the scraper as a Cloud Run Job with 100 parallel tasks to maximize throughput with reliability guardrails (randomized delays, low concurrency per task, retries, batch saves every 100 records, and automatic upload to GCS).

#### Example output (head 10 rows from one task)
File: `out/rightmove-job/task_01/listings.csv`

```csv
url,rightmove_id,price_text,price_value,price_currency,property_type,property_title,bedrooms,bathrooms,sizes,tenure,estate_agent,key_features,description,council_tax,parking,garden,accessibility
https://www.rightmove.co.uk/properties/162236315,162236315,"£8,750,000",8750000,GBP,Detached,"Barnsbury Park, London, N1",6.0,4.0,"6,060 sq ft 563 sq m",Freehold,"Knight Frank, Islington 321-322 Upper Street,
London,
N1 2XQ More properties from this agent","['6 bedrooms', '4 reception rooms', '4 bathrooms', 'Period', 'Detached', 'Garden', 'Gym', 'Town/City']","Located in the heart of the Barnsbury Conservation Area, this remarkable Grade II listed home stands out as one of the few fully detached, double-fronted properties in the area—a truly rare find. Spanning approximately 6,077 sq ft, the house is set across just three principal floors, offering a seamless balance of grandeur, elegance, and practical family living. Upon entry, a beautifully landscaped front garden creates an inviting approach, leading to a stunning raised ground floor filled with natural light and character. This level features a formal drawing room, an elegant dining room, a spacious sitting room with balcony, a library, and a dedicated study, all with impressive proportions and period detailing. The lower ground floor has been cleverly designed for both entertaining and everyday use. It includes a large kitchen with an adjacent pantry, a charming garden room with direct access to the rear terrace, a gym with an en suite shower room, and practical additions such as a utility room, wine storage, and boiler room. Both the rear and front gardens are beautifully maintained, with mature planting offering year-round greenery and privacy—ideal for outdoor entertaining or quiet relaxation. Upstairs, the first floor hosts six generously sized bedrooms, including a luxurious principal suite with en suite bathroom and dressing area, and multiple further bathrooms. The second floor is home to an additional, secluded seventh bedroom/storage room tucked beneath the eaves. A roof terrace adds an unexpected bonus space, offering a quiet retreat with elevated views over the garden. Barnsbury Park is in the heart of the Barnsbury Conservation area and is well placed for the fantastic transport links at Highbury Corner. The London Overground, Victoria Line, National Rail and many bus routes all provide access in all directions. Barnsbury is well placed for access to Farringdon, the new transport hub that serves south Islington. The Elizabeth Line is the new addition to London transport providing speedy access to East and West London to include Canary Wharf and Heathrow. Brochures More Details Barnsbury Park - Bro

Show less",H,Ask agent,Yes,Ask agent
https://www.rightmove.co.uk/properties/163596818,163596818,"£6,500,000",6500000,GBP,Detached,"Canonbury Park South, Islington, London, N1",4.0,3.0,"3,171 sq ft 295 sq m",Freehold,"Savills, Islington 94 Upper Street,
London,
N1 0NP More properties from this agent","['80’ x 75’ south facing garden adjacent to New river Walk', 'Front garden with off street parking', 'Exceptional , iconic Grade II listed Canonbury House', 'Triple fronted, detached two storey house', 'Large plot with south facing garden and off street parking at the front.', 'Amazing 60’ living space overlooking rear garden.', 'Quiet residential road with restricted traffic access', 'EPC Rating = D']","The most iconic house in Canonbury – the magnificent Myddelton Cottage 
 Description The exceptional Myddelton Cottage on the south side of Canonbury Park South is unquestionably one of the most iconic houses in the Islington area. The wisteria clad frontage is most attractive and only adds to the appeal of the accommodation that is laid out over just two floors, is triple fronted and detached. Almost unique in the area. The rooms are full of period features with attractive windows, fireplaces, shutters, ceiling mouldings and the like. The room at the rear of the house includes a sitting room, breakfast room and a conservatory, all enjoying access and views of the south facing rear garden. The additional living space on the ground floor can be utilised as further living space, home office use or dining rooms. Bedrooms and bathrooms occupy the first floor.  The cellarage is just over 1000 sq ft and provides excellent storage space for all manner of uses. The rear garden is almost square; another exception for typical Islington gardens. It faces south and backs onto the New River. The front area  has off street parking for a number of vehicles and provides access to the garage. Location Canonbury Park South is in the heart of the Canonbury Conservation Area and has restricted access to traffic. The south side backs onto The New River and consequently is a quiet residential location in this most favoured street. Access to Upper Street is easy with it’s many shops, restaurants, and bars whilst the excellent transport links including buses, underground, overground and national rail links are equally accessible at Highbury Corner and Canonbury. Square Footage: 3,171 sq ft 
 Brochures Web Details Particulars
```

---

## Setup & Usage

### Environment setup and package install
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

### Generate an adaptive slice plan (`scripts/adaptive_slicer.sh`)
  - Prompts: keywords query (null for none), min/max price (null for none), property type (null for all).
  - Produces a plan file at `out/<query-or-n>/<min-or-n>/<max-or-n>/<type-or-n>.txt`.
  - The plan file includes your filters (header) and an ordered list of slices, one per line:
    `slicer_name|location_identifier|min_price|max_price`.
```bash
./scripts/adaptive_slicer.sh
# Example output: out/n/300000/450000/n.txt or out/n/n/n/n.txt
```

### Discover URLs from the plan (`scripts/discover_urls.sh`)
  - Prompts for the plan path and optional pagination start/page limits.
  - Discovers each slice in order, writing per‑slice CSVs to `out/per_slice/` with columns:
    `rightmove_id,url,slicer_name`.
  - After all slices, merges and de‑duplicates URLs into `out/discovered_adaptive_seeds.csv`.
```bash
./scripts/discover_urls.sh
# Per-slice outputs: out/per_slice/slice_001_<NAME>.csv (rightmove_id,url,slicer_name)
# Merged:            out/discovered_adaptive_seeds.csv (header: url)
```

### Scrape listings (`scripts/run_scrape.sh`)
  - Prompts for “Start from Rightmove ID (null for first)” to resume mid‑run.
  - Scrapes URLs from `out/discovered_adaptive_seeds.csv`, prints live progress, and batch‑saves every 100 records to `out/batches/`. The final merged output is written to `out/listings.csv`.
```bash
./scripts/run_scrape.sh
# Progress prints as it scrapes; batches land in out/batches/, final in out/listings.csv
```

## Rightmove pagination cap and how the adaptive slicer bypasses it
- Rightmove limits browseable results for a single search to ~1,050 items (25 per page → ~42 pages). Beyond that, listings aren’t accessible by pagination alone.
- The adaptive slicer avoids this by partitioning the search space into non‑overlapping “slices” that each fall under the cap:
  - Start with London region (REGION^87490).
  - Split into postcode districts (OUTCODE^… like E14, SW1, W11, etc.).
  - If a district still exceeds the cap, split its price range into non‑overlapping bands (e.g., [300k,375k) and [375k,450k)), repeating until each slice ≤ 1,000.
- Sizing is done by loading real search pages headlessly and parsing result counts from the DOM/scripts. We navigate with `domcontentloaded` and then wait for property cards to render for robustness.
- Finally, per‑slice discovery collects listing URLs, and the app merges and de‑duplicates them by canonical URL (and later by `rightmove_id` when writing scraped records).

## Compliance & troubleshooting
-- Set `ALLOW_DISCOVERY=true` in `.env` and create `consent.txt`.
-- Install browsers: `python -m playwright install --with-deps`.
-- If network sluggish, use `REQUEST_TIMEOUT=60–90` and keep concurrency modest.
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
