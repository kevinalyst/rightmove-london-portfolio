London Property Market Portfolio — Data Mining → Transformation → AI Agents

Purpose
- Build a robust, polite Rightmove listing scraper for personal, non‑commercial research.
- Overcome Rightmove’s pagination cap by planning adaptive search slices, discovering listing URLs, and scraping full listing details at scale.

Scope (in this repo)
- Adaptive slicer to plan non‑overlapping search slices.
- URL discovery per slice, merging and de‑duping results.
- Headless scraping of listing details with resilient extractors and normalization.
- SQL modeling: staging clean, CTE transforms, semantic view for analysis.
- Cortex Analyst/Search examples over transformed data.
- CLI + Makefile targets for repeatable runs; CI workflows and docs site.
- Outputs to `out/` and loading path to Snowflake.

Out of Scope (handled elsewhere)
- External BI dashboards.

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
- Python package `rightmove-scraper` with Typer CLI and Makefile targets.
- Scraper module + exporters; pipeline loaders and geocoding; SQL CTEs and view.
- Agents examples for Snowflake Cortex.
- CI (lint/test/build) and MkDocs site.
