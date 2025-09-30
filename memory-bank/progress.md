Progress

What works ✅
- `make scrape10` → scrapes 10 listings, saves to `data/raw/listings_10.{csv,ndjson}`.
- `make transform10` → local transform builds LOCATION, ZONE, ADDRESS, writes `data/processed/...`.
- **Production chatbot** at `https://london-property-analysis.uk/` with full Cortex integration:
  - **Analyst mode**: Live streaming SSE with EventSource, progressive thinking/SQL/answer rendering
  - **Search mode**: Batch semantic search over unstructured property descriptions
  - **Charts**: Native Vega-Lite rendering from `response.chart` events
  - **Layout**: Single-column vertical stacking (Thinking → SQL → Answer → Viz)
- Cloudflare Worker (`london-portfolio-backend.axiuluo40.workers.dev`):
  - Health check: `GET /api/health` → 200
  - CORS: `OPTIONS /api/chat` → 204
  - Streaming: `GET /api/chat/stream` → SSE passthrough from Snowflake
  - Batch: `POST /api/chat` → JSON response
  - Retry logic, timeout control (30s), correlation IDs
- **Snowflake integration** (account `ZSVBFIR-AJ21181`):
  - Agent: `SNOWFLAKE_INTELLIGENCE.AGENTS.RIGHTMOVE_ANALYSIS`
  - Search: `RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.UNSTRUCTURED_RAG`
  - Auth: Bearer PAT token (no X-Snowflake header needed)
  - Endpoints: `.../agents/{name}:run` (streaming), `.../cortex-search-services/{name}:query`
- **Actual SQL visibility**: Extracted from `execution_trace` event attributes, displayed live during execution.
- **Vega-Lite charts**: Native rendering of agent-generated visualizations (bar, line, histograms).

What's left / enhancements
- Optional: Add syntax highlighting for SQL code blocks.
- Optional: Add loading spinner/progress indicator during streaming.
- Optional: Implement Chart/Table view toggle buttons.
- Demo video recording showing live streaming + Vega charts.
- Consider caching common queries (CDN or KV).

Current status
- ✅ **Production ready**: No 5xx errors, live streaming operational, charts rendering.
- ✅ **Performance**: Analyst 25-35s (acceptable for LLM), Search <2s.
- ✅ **UX**: Matches Snowflake native UI (live thinking, SQL, auto-collapse).

Known issues / risks (resolved)
- ~~503 errors~~ → FIXED (account mismatch, endpoint correction, SSE parsing)
- ~~526 auth errors~~ → FIXED (correct account, Bearer token)
- ~~Charts not rendering~~ → FIXED (switched to Vega-Lite)
- ~~Side-by-side layout~~ → FIXED (content wrapper flexbox)

Active risks
- Rightmove anti-bot mitigations; use conservative scraping defaults.
- Nominatim geocoding rate limited (~1 req/sec).
- PAT token expiry (90 days max); needs rotation plan.
- EventSource browser compatibility (IE11 not supported, modern browsers OK).
