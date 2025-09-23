Progress

What works
- Adaptive slicer planning, per README.
- URL discovery with per‑slice outputs and merged de‑duped seeds.
- Scraper with batch saves and final merged CSV example given in README.
- Docker/Cloud Run Job pattern with shard inputs and guarded concurrency.

What’s left / enhancements
- Expand automated tests under `tests/` (HTML fixtures, extractor assertions).
- Harden extractors for edge cases; improve normalization consistency.
- Optional: integrate GCS uploads and CI hooks.

Current status
- Memory Bank initialized and populated with project context.
- Local branch behind `origin/main` by 2 commits; modified extractor/model/scraper files present.

Known issues / risks
- Rightmove anti‑bot mitigations require conservative defaults (low concurrency, delays, real UA).
- Dynamic site changes can break selectors; keep extractor logic modular and well‑tested.
