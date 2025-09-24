Active Context

Current focus
- Portfolio-ready guided flows A/B/C with zero external creds; minimal repo footprint.

Repo state
- New repo created and pushed: `rightmove-london-portfolio` (remote `portfolio`).
- CI workflows added, docs site configured, Makefile targets available.

Recent changes
- Makefile trimmed to two targets: `scrape10` (uses `rightmove_scraper.cli`) and `transform10` (local, no Snowflake).
- Added `pipeline/local_rightmove_transform.py`: builds LOCATION, computes ZONE, reverse-geocodes ADDRESS via geopy.
- Built `/docs` static mini chatbot (dark UI) and wiring guide; backend stubs under `/backend` (Cloudflare Worker).
- Removed dummy `scraper/` CLI/stubs; added .gitignore to exclude secrets, outputs, and unneeded code.

Next steps
- Optional: enable GitHub Pages for `/docs`; add social preview link in README.
- Record demo video snippet of the three flows.

Active decisions
- Outputs live under `data/raw` and `data/processed`; these are gitignored.
- Use `rightmove_scraper.cli` directly for scraping 10 listings; geopy used for ADDRESS locally.
- Secrets and Snowflake-only scripts are untracked and ignored in this portfolio repo.
