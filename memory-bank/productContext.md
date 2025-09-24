Product Context

Why this exists
- Create a high‑quality dataset of London property listings for pricing and market insights, suitable for downstream analytics and BI.

Problems it solves
- Rightmove’s hard pagination cap (~1,050 listings) blocks naively enumerating search results.
- Fragile scraping due to dynamic content and anti‑bot mitigations.

Core approach (how it should work)
- Plan: Adaptive partitioning (REGION → OUTCODE → price bands) sized under the pagination cap.
- Discover: Collect canonical URLs per slice; merge and de‑dup to seeds.
- Scrape: Extract normalized fields → CSV/Parquet; batch/resume semantics.
- Transform: Load to Snowflake (staging → CTE transforms → semantic view `RIGHTMOVE_ANALYSIS`).
- Agents: Query with Cortex Analyst/Search over transformed data.

Primary user workflows
- Run via Makefile: `make setup`, `make scrape`, `make geocode`, `make load`, `make docs`.
- Monitor outputs under `out/`; run SQL in Snowflake; try agents examples.

User experience goals
- Simple, repeatable CLI with sensible defaults and prompts.
- Polite by default: low concurrency, randomized delays, retries.
- Clear failure modes with actionable logs and resumability.
