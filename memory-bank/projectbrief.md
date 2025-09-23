London Property Market Portfolio — Data Mining (Rightmove Scraper)

Purpose
- Build a robust, polite Rightmove listing scraper for personal, non‑commercial research.
- Overcome Rightmove’s pagination cap by planning adaptive search slices, discovering listing URLs, and scraping full listing details at scale.

Scope (in this repo)
- Adaptive slicer to plan non‑overlapping search slices.
- URL discovery per slice, merging and de‑duping results.
- Headless scraping of listing details with resilient extractors and normalization.
- CLI and shell scripts to run the plan → discover → scrape workflow locally or in containers / Cloud Run Jobs.
- Write structured outputs to `out/` (CSV, batch files).

Out of Scope (handled by other portfolio components)
- Data warehousing and SQL modeling.
- BI dashboarding and distribution.

Success Criteria
- Coverage: high proportion of London listings discovered (unique canonical URLs / `rightmove_id`).
- Completeness: key fields populated (price, property meta, features, description, agent, tenure, etc.).
- Reliability: low error rate via retries, polite delays, and batch writes; resumability by ID.
- Compliance: scrapes are gentle (low concurrency, randomized delays) and respect opt‑in gates.

Constraints
- Personal research only; respect Rightmove Terms and robots.
- Hard pagination cap (~1,050 items) requires search space partitioning.
- Cloud Run Job execution uses parallel shards with guarded concurrency per task.

Primary Deliverables
- Python package `rightmove-scraper` with Typer CLI.
- Shell scripts: `scripts/adaptive_slicer.sh`, `scripts/discover_urls.sh`, `scripts/run_scrape.sh`.
- Container/Docker setup for reproducible runs and Cloud Run Jobs.
- Outputs: `out/per_slice/`, `out/discovered_adaptive_seeds.csv`, `out/listings.csv`.
