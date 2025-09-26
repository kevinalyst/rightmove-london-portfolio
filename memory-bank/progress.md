Progress

What works
- `make scrape10` → scrapes 10 listings with `rightmove_scraper.cli`, saves to `data/raw/listings_10.{csv,ndjson}`.
- `make transform10` → local transform builds `LOCATION`, `ZONE`, reverse-geocodes `ADDRESS`, writes `data/processed/...` and prints summary.
- `/docs` GitHub Pages mini chatbot renders and explains wiring; backend stubs present.
- Cloudflare Worker live with KV + CORS; Stripe Checkout + grant flow returns token; chat decrements credits.

What’s left / enhancements
- Replace mock geocoder with provider; add caching.
- Optional: enable real GCS upload in pipelines and document credentials.
- Demo video recording and link replacement.

Current status
- Portfolio flows implemented; repo slimmed down; secrets and heavy paths ignored.

Known issues / risks
- Rightmove anti‑bot mitigations; use conservative defaults and `consent.txt`.
- Nominatim geocoding is rate limited (~1 req/sec); batch sizes should remain small.
- Snowflake SQL API path requires OAuth token or client session; ensure secret rotation and minimal logging.
