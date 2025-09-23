London Property Price — Repo Polishing Plan

Scope: Convert this project into a hiring‑manager‑ready portfolio repo with clean structure, CI, docs, and runnable stubs that won’t leak secrets.

Audit (current state)
- Language/runtime: Python 3.11+, Playwright, Typer CLI (`rightmove-scraper`).
- Existing modules: slicer/scraper in `src/rightmove_scraper/` with jobs + scripts; outputs in `out/`.
- Memory Bank present with architecture and norms; Dockerfile exists; Cloud Run job shards available.
- Gaps vs. target: missing structured top‑level folders (scraper/, pipeline/, sql/, agents/, infra/, docs/), CI, Makefile, pre-commit, policies, and GitHub templates. README is informative but not portfolio‑polished.

Proposed changes
1) Structure: add `scraper/`, `pipeline/`, `sql/`, `agents/`, `infra/`, `docs/`, `.github/`, `assets/` with READMEs/stubs.
2) README: add banner + badges, concise value prop, Quickstart (3 cmds), architecture diagram, demo placeholders, tour, responsible use.
3) Scraper stubs: adaptive slicer interface + pure functions + tests; exporters for CSV/Parquet and GCS (env‑driven).
4) Pipeline: loader GCS→Snowflake (copy/merge, resumable), pluggable geocoding (mock default), zones mapping sample.
5) SQL: schema, staging clean, transforms CTEs to output `analysis_ready_<date>`; view materialization.
6) Agents: Snowflake Cortex Analyst/Search example queries and README.
7) Infra/CI: Cloud Run service.yaml, GitHub Actions (lint/test/build), optional docs deploy.
8) Dev UX: Makefile targets, `.env.sample`, pre‑commit hooks; ruff/black/mypy config.
9) Docs site: MkDocs Material skeleton mirroring README + demo script.
10) Policies & templates: LICENSE (MIT), SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, ROADMAP, CHANGELOG; issue/PR templates.

Smoke test plan
- Local: `make setup && make lint && make docs` should pass.
- Scraper: `make scrape` writes sample CSV locally (mock path ok if Playwright not installed).
- Pipeline: `make load` runs mocked copy/merge if Snowflake creds absent; docs explain real flow.
- Agents: run example SQL in Snowflake worksheet referencing transformed view.

PR draft summary
- Restructured repo with clear domains and docs.
- Added CI, pre‑commit, Makefile, and docs site.
- Implemented slicer/exporter/pipeline stubs with tests and env‑driven config.
- Added SQL CTEs and agents examples.
- Added policies and GitHub templates.

Next steps after merge
- Replace placeholders (GCS bucket, Snowflake org/account, demo video).
- Connect real geocoding provider and enable non‑mocked paths.


