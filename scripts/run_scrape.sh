#!/usr/bin/env bash
set -euo pipefail

# Scrape listings from discovered seeds, supporting resume by rightmove_id and batch saving.

export PYTHONPATH=${PYTHONPATH:-$PWD/src}

OUT_DIR="./out"
FORMAT="csv"
SEEDS_FILE="$OUT_DIR/discovered_adaptive_seeds.csv"

if [ ! -f "$SEEDS_FILE" ]; then
  echo "Seeds file not found: $SEEDS_FILE"
  exit 1
fi

read -r -p "Start from Rightmove ID (null for first): " START_ID

# Build a temporary seeds file filtered by start id if provided
FILTERED_SEEDS="$OUT_DIR/discovered_adaptive_seeds.filtered.csv"

if [ -z "${START_ID:-}" ] || [ "${START_ID,,}" = "null" ]; then
  cp "$SEEDS_FILE" "$FILTERED_SEEDS"
else
  # Keep header and rows whose property id >= START_ID (lexicographically compare numeric string)
  {
    IFS=, read -r header
    echo "$header"
    while IFS=, read -r url; do
      pid=$(echo "$url" | sed -nE 's#.*properties/([0-9]+).*#\1#p')
      if [ -n "$pid" ] && [ "$pid" \>="$START_ID" ]; then
        echo "$url"
      fi
    done
  } < "$SEEDS_FILE" > "$FILTERED_SEEDS"
fi

URL_COUNT=$(($(wc -l < "$FILTERED_SEEDS") - 1))
if [ "$URL_COUNT" -le 0 ]; then
  echo "No URLs to scrape after filtering."
  exit 1
fi

echo "Scraping $URL_COUNT URLs..."
PYTHONPATH=$PWD/src python -m rightmove_scraper.cli scrape-seeds \
  --input "$FILTERED_SEEDS" \
  --out "$OUT_DIR" \
  --format "$FORMAT" \
  --max "$URL_COUNT" \
  --batch-size 100

echo "Done."


