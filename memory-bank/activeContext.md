Active Context

Current focus
- Production chatbot with live streaming Cortex Agent integration matching Snowflake UI experience.
- Full reliability: 503 errors resolved, SSE streaming operational, native Vega-Lite charts rendering.

Repo state
- Repo: `rightmove-london-portfolio` (remote `portfolio`, GitHub auto-redirects to `kevinalyst/rightmove-london-portfolio`).
- Live site: `https://london-property-analysis.uk/` (Cloudflare Pages).
- Worker: `https://london-portfolio-backend.axiuluo40.workers.dev` (account: `bd3a78c20e61142b0cbec2c465e0af83`).
- Snowflake: Account `ZSVBFIR-AJ21181`, agent `SNOWFLAKE_INTELLIGENCE.AGENTS.RIGHTMOVE_ANALYSIS`.

Recent changes (Sept 30, 2025)
- **MAJOR FIX**: Resolved HTTP 503 errors (4 root causes identified):
  1. Account mismatch: Changed `SNOWFLAKE_ACCOUNT` from KA89655 to ZSVBFIR-AJ21181 (526→404).
  2. Endpoint fix: Corrected to `.../agents/{name}:run` with :run suffix (404→200).
  3. SSE parsing: Added stream parser for `event: response.*` format.
  4. Search endpoint: Updated to `.../cortex-search-services/{name}:query` (v2, no columns param).
- **Authentication**: Bearer PAT token, no `X-Snowflake-Authorization-Token-Type` header needed (auto-detect works).
- **STREAMING**: Implemented live SSE passthrough:
  - New endpoint: `GET /api/chat/stream?question=...&mode=analyst`
  - EventSource frontend with progressive rendering
  - Real-time thinking process (word-by-word streaming)
  - Actual SQL extraction from `execution_trace` attributes (`snow.ai.observability.agent.tool.cortex_analyst.sql_query`)
  - Auto-collapse thinking when response completes
- **CHARTS**: Migrated Chart.js → Vega-Lite:
  - Listen to `response.chart` SSE event
  - Render native Vega-Lite v5 specs from agent
  - Dark theme config matching UI
  - Interactive tooltips, export PNG/SVG
- **LAYOUT**: Fixed single-column stacking (no side-by-side grid issue):
  - Added `message-content-wrapper` for vertical flexbox
  - Order: Thinking → SQL → Answer → Visualization
- Documentation: RUNLOG.md (14 steps), SNOWFLAKE_PAT_GUIDE.md, FIX_SUMMARY.md, STREAMING_IMPLEMENTATION.md, CHART_INVESTIGATION.md, VEGA_MIGRATION_COMPLETE.md.

Next steps
- Optional: Add loading spinner during thinking stream.
- Optional: Syntax highlighting for SQL code blocks.
- Demo video recording showing live streaming + charts.

Active decisions
- Analyst mode uses streaming (`/api/chat/stream`), Search mode uses batch (`POST /api/chat`).
- Vega-Lite chosen over Chart.js for native Cortex compatibility (industry standard, zero transformation).
- Single-column layout enforced via content wrapper flexbox.
- PAT token approach preferred over key-pair JWT (simpler, Snowflake recommendation for 2025+).
- Correlation IDs logged for every request; execution_trace events captured for SQL visibility.
