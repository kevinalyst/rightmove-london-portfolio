#!/usr/bin/env bash
set -euo pipefail

python -m rightmove_scraper.cli scrape-seeds \
  --input ./seeds.csv \
  --out ./out \
  --format csv \
  --max 5


