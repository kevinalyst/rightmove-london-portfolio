Active Context

Current focus
- Initialize the Memory Bank and document project context for reliable continuity across sessions.

Repo state (at initialization)
- Branch behind `origin/main` by 2 commits.
- Modified files: `src/rightmove_scraper/extractors.py`, `src/rightmove_scraper/models.py`, `src/rightmove_scraper/scrape_listing.py`.
- Untracked: `tests/` directory present.

Recent changes
- Memory Bank created with core files and initial content derived from README, `pyproject.toml`, and Dockerfile.

Next steps
- Keep Memory Bank up‑to‑date after significant code or process changes.
- Stabilize extractors and models as needed; expand tests under `tests/`.
- Maintain compliance defaults (low concurrency, delays, consent gate).

Active decisions
- Default outputs under `out/`; final merged scraped data at `out/listings.csv`.
- CLI entrypoint `rightmove-scraper` (Typer) with supporting shell scripts for common flows.
- Cloud Run Job pattern supported via `jobs/entrypoint.py` and shards directory.
