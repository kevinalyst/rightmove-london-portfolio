Product Context

Why this exists
- Create a high‑quality dataset of London property listings for pricing and market insights, suitable for downstream analytics and BI.

Problems it solves
- Rightmove’s hard pagination cap (~1,050 listings) blocks naively enumerating search results.
- Fragile scraping due to dynamic content and anti‑bot mitigations.

Core approach (how it should work)
- Plan: Build an adaptive plan that partitions the search space (REGION → OUTCODE → price bands) so each slice stays under the cap.
- Discover: Visit slice result pages, read counts, and collect unique listing URLs; merge and de‑dup to a single seeds file.
- Scrape: Visit each listing and extract normalized fields into structured CSV. Support resume from a given `rightmove_id`.

Primary user workflows
- Run slicer → discover → scrape via provided shell scripts with prompt‑driven parameters.
- Monitor progress logs and incremental batch outputs; final merged CSV at `out/listings.csv`.

User experience goals
- Simple, repeatable CLI with sensible defaults and prompts.
- Polite by default: low concurrency, randomized delays, retries.
- Clear failure modes with actionable logs and resumability.
