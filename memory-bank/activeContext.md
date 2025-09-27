Active Context

Current focus
- Portfolio-ready guided flows A/B/C with zero external creds; minimal repo footprint.
- Keep Pages chatbot reliably wired to Worker after demo-only backend change.

Repo state
- New repo created and pushed: `rightmove-london-portfolio` (remote `portfolio`).
- CI workflows added, docs site configured, Makefile targets available.

Recent changes
- Makefile trimmed to two targets: `scrape10` (uses `rightmove_scraper.cli`) and `transform10` (local, no Snowflake).
- Added `pipeline/local_rightmove_transform.py`: builds LOCATION, computes ZONE, reverse-geocodes ADDRESS via geopy.
- Built `/docs` static mini chatbot (dark UI) and wiring guide; backend stubs under `/backend` (Cloudflare Worker).
- Removed dummy `scraper/` CLI/stubs; added .gitignore to exclude secrets, outputs, and unneeded code.
- Deployed Cloudflare Worker: `london-portfolio-backend` with KV `USAGE_TOKENS`, CORS wildcard support for Pages preview subdomains and production `london-property-analysis.uk` domain.
- Pages project serves `/docs` and points frontend to Worker `backend_base_url`.
- Worker now supports `ALLOW_DEMO_FREE` mode (5 free queries) and accepts `{question|query}` payloads; inline backend URL injected in `index.html` to avoid missing `config.json`.
- Snowflake Cortex wired via `RIGHTMOVE_ANALYSIS`; SQL API call now sets Accept/User-Agent/Bearer headers and binds resource/prompt explicitly (requires valid `SNOWFLAKE_OAUTH_TOKEN`).

Next steps
- Optional: enable GitHub Pages for `/docs`; add social preview link in README.
- Record demo video snippet of the three flows.
- Consider restoring paid Stripe flow later or document free demo limitations.

Active decisions
- Outputs live under `data/raw` and `data/processed`; these are gitignored.
- Use `rightmove_scraper.cli` directly for scraping 10 listings; geopy used for ADDRESS locally.
- Secrets and Snowflake-only scripts are untracked and ignored in this portfolio repo.
- Backend Worker simplified: Stripe endpoints removed; remaining chat endpoint is open-access (no KV throttling) and still depends on Snowflake OAuth token for real answers.
