Progress

What works
- `make scrape10` → scrapes 10 listings with `rightmove_scraper.cli`, saves to `data/raw/listings_10.{csv,ndjson}`.
- `make transform10` → local transform builds `LOCATION`, `ZONE`, reverse-geocodes `ADDRESS`, writes `data/processed/...` and prints summary.
- `/docs` Pages chatbot renders with inline backend URL fallback, resilient config load, and documents wiring.
- Cloudflare Worker live with KV + CORS (including preview subdomains and production domain); demo mode (`ALLOW_DEMO_FREE=true`) returns stubbed answer w/out token while still supporting Stripe tokens when configured; Snowflake Cortex call now hits `RIGHTMOVE_ANALYSIS` via SQL API once a valid `SNOWFLAKE_OAUTH_TOKEN` secret is supplied.

What’s left / enhancements
- Replace mock geocoder with provider; add caching.
- Optional: enable real GCS upload in pipelines and document credentials.
- Demo video recording and link replacement.
- Revisit Stripe checkout integration once paid flow reinstated.

Current status
- Portfolio flows implemented; repo slimmed down; secrets and heavy paths ignored.

Known issues / risks
- Rightmove anti‑bot mitigations; use conservative defaults and `consent.txt`.
- Nominatim geocoding is rate limited (~1 req/sec); batch sizes should remain small.
- Snowflake SQL API path requires OAuth token or client session; ensure secret rotation and minimal logging.
- Pages rewrite rules can still bypass `config.json`; ensure inline config stays updated with Worker URL.
- Preview deployments require wildcard CORS to keep chat working; verify `ALLOW_ORIGIN` stays in sync with Pages domains.
