Scraper — Playwright + Adaptive Slicer

This folder contains a focused, composable scraping system:
- slicer: plan non-overlapping search slices to bypass pagination caps
- pipelines: crawl → parse → validate → emit
- exporters: write CSV/Parquet locally and to GCS

Quickstart (local)
```bash
make setup
make scrape
```

Adaptive slicer (pseudo-code)
```text
function partition(initial_slice):
  if count(initial_slice) <= CAP: return [initial_slice]
  if level == borough: split into districts
  if level == district: split price range into bands and recurse
```

Anti‑ban hygiene
- Low concurrency, randomized delays, realistic desktop USER_AGENT
- domcontentloaded + wait for property cards
- Retries with backoff; debug HTML on empty pages
- Respect robots/terms; personal/educational use only

Emitted fields (core)
- url, rightmove_id, price_text/value/currency, property_type, property_title,
  bedrooms, bathrooms, sizes, tenure, estate_agent, key_features, description,
  council_tax, parking, garden, accessibility

Examples
```bash
rightmove-scraper plan-adaptive --min-price 300000 --max-price 450000
rightmove-scraper discover-from-plan --plan-file out/n/300000/450000/n.txt --per-slice-dir out/per_slice
rightmove-scraper scrape-seeds --input out/discovered_adaptive_seeds.csv --max 25
```

Placeholder
- Demo: https://youtu.be/PLACEHOLDER

