System Patterns

Architecture overview
- Modules (portfolio scope)
  - `src/rightmove_scraper/*`: discovery + scrape CLI used by `make scrape10`.
  - `pipeline/local_rightmove_transform.py`: local transform, builds LOCATION, computes ZONE, reverse‑geocodes ADDRESS.
  - `docs/*`: static chatbot SPA with live streaming, Vega-Lite charts, dark UI.
  - `backend/cloudflare/*`: production Worker with SSE streaming, Cortex Agent/Search proxy, CORS, health check.

Control flow (A/B/C)
1) A: `make scrape10` → discover/search + scrape 10 listings → `data/raw/listings_10.{csv,ndjson}`.
2) B: `make transform10` → local enrich (LOCATION, ZONE, ADDRESS) → `data/processed/listings_10_transformed.{csv,parquet}`.
3) C: Production chatbot (`https://london-property-analysis.uk/`) → Cloudflare Worker → Snowflake Cortex Agents/Search.

Chatbot architecture (streaming)
- **Frontend** (EventSource): 
  - Connects to `GET /api/chat/stream?question=...&mode=analyst`
  - Receives SSE events: `response.status`, `response.thinking.delta`, `execution_trace`, `response.chart`, `response.text.delta`, `response`
  - Progressive rendering: thinking → SQL → answer → chart
  - Auto-collapse thinking/SQL when complete
- **Worker** (SSE passthrough):
  - Streams Snowflake events without buffering
  - CORS headers for cross-origin SSE
  - Correlation IDs for debugging
  - Timeout: 30s via AbortController
- **Snowflake** (Cortex Agents):
  - Agent: `SNOWFLAKE_INTELLIGENCE.AGENTS.RIGHTMOVE_ANALYSIS`
  - Returns SSE stream with Vega-Lite chart specs
  - `execution_trace` events contain actual SQL in attributes
  - Auth: Bearer PAT token

Reliability & compliance
- Worker retry logic: exponential backoff for 429/503/504, no retry on 4xx.
- SSE error handling: graceful degradation, user-friendly messages.
- Streaming timeout: 30s per request, auto-close connections.
- CORS: wildcard for Pages preview subdomains, explicit for production domain.
- SQL extraction: parses `execution_trace` JSON attributes for transparency.
- Chart rendering: native Vega-Lite (no transformation, zero impedance mismatch).

Data model themes (non‑exhaustive)
- Identification: `url`, `rightmove_id`.
- Pricing: `price_text`, `price_value`, `price_currency`, `price_per_sqm`.
- Property meta: `property_type`, `bedrooms`, `bathrooms`, `sizes`, `tenure`.
- Location: `zone`, `address`, `borough` (extracted from address).
- Agent & listing: `estate_agent`, `key_features`, `description`.
- Temporal: `timestamp`, `ingested_at` for trend analysis.

Operational patterns
- Analyst mode → streaming SSE (real-time feedback during 25-35s LLM processing).
- Search mode → batch JSON (instant <2s semantic search results).
- Charts → Vega-Lite specs from `response.chart` event (industry standard).
- Layout → single-column flexbox (Thinking → SQL → Answer → Viz).
- Secrets → Worker Secrets only (`SNOWFLAKE_PAT_TOKEN`), never in repo or frontend.
