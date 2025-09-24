# London Property Market Portfolio — Data Mining → Transformation → AI Agents

<br>
<p align="center">
  <img src="assets/social-preview.png" alt="London Property Portfolio" width="640" />
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/build-GitHub%20Actions-blue" alt="build" /></a>
  <a href="#"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code style" /></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-green" alt="license" /></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11+-yellow" alt="python" /></a>
</p>

**A polite Playwright scraper + Snowflake pipeline + AI agents to explore London property prices.**

### Try the portfolio demos
```bash
# A) CLI scrape 10 listings (writes data/raw/listings_10.{ndjson,csv})
make scrape10

# B) Local transform 10 (writes data/processed/listings_10_transformed.{parquet,csv})
make transform10
```

Open the mini chatbot at `docs/index.html` (served by GitHub Pages when enabled). See `docs/wire-up-cortex.md` to connect a real backend and Snowflake Cortex.

### Architecture
```mermaid
flowchart LR
  A[Playwright Scraper (Cloud Run)] -->|CSV/Parquet| B[GCS]
  B --> C[Snowflake Staging]
  C --> D[CTEs Transform]
  D --> E[RIGHTMOVE_ANALYSIS]
  E --> F[Cortex Analyst]
  E --> G[Cortex Search]
  subgraph Adaptive Slicer
  A
  end
```

### Demo
- **[Demo video — coming soon](https://youtu.be/PLACEHOLDER)**
- ![Demo GIF](assets/demo/placeholder.gif)

### What’s inside
- `scraper/`: Playwright + adaptive slicer, pipelines, exporters
- `pipeline/`: GCS→Snowflake loader, geocoding & zones
- `sql/`: schema, staging clean, transforms, views
- `agents/`: Cortex Analyst/Search examples
- `infra/`: Cloud Run, docker-compose, CI
- `docs/`: Static GitHub Pages demo (chat UI, wiring guide)

### Why it’s interesting
- Adaptive slicing bypasses pagination caps safely
- Clean separation: plan → discover → scrape; batch/resume semantics
- End‑to‑end: scrape → warehouse → AI agents

### Responsible Use
- Personal/educational use only. Respect website terms and robots.txt. Keep concurrency low, randomize delays, identify with a realistic desktop `USER_AGENT`. Cache results and avoid unnecessary traffic.

### Run it
See `make` targets, `.env.sample`, and folder READMEs.
- Snowflake: database `RIGHTMOVE_LONDON_SELL`, schema `CLOUDRUN_DXLVF`, warehouse `COMPUTE_WH`
- Demo: `https://youtu.be/PLACEHOLDER`
