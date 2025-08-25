#!/usr/bin/env bash
set -euo pipefail

# This script interactively runs discovery (adaptive or simple) and then scrapes the discovered URLs.
# Requirements:
# - .env has ALLOW_DISCOVERY=true
# - consent.txt exists in project root
# - Dependencies installed and Playwright browsers set up

# Ensure Python can import the package from src
export PYTHONPATH=${PYTHONPATH:-$PWD/src}

if [ "${ALLOW_DISCOVERY:-}" != "true" ]; then
  echo "Warning: ALLOW_DISCOVERY is not 'true'. Discovery will be blocked by the app."
fi
if [ ! -f "consent.txt" ]; then
  echo "Error: consent.txt not found in project root. Create it to enable discovery."
  exit 2
fi

read -r -p "Use adaptive slicer? (y/N): " USE_ADAPTIVE

read -r -p "Keywords query (null for none): " QUERY
read -r -p "Min price (null for none): " MIN_PRICE
read -r -p "Max price (null for none): " MAX_PRICE
read -r -p "Property type [flat|detached|semi-detached|terraced|bungalow] (null for all): " PROP_TYPE


OUT_DIR="./out"
FORMAT="csv"

to_null_lower() { printf "%s" "${1:-}" | tr '[:upper:]' '[:lower:]'; }

if [[ "${USE_ADAPTIVE:-}" =~ ^[Yy]$ ]]; then
  echo "Running adaptive discovery..."
  declare -a disc_cmd
  disc_cmd=(python -m rightmove_scraper.cli discover-adaptive --out "$OUT_DIR")
  # First, list slices only
  disc_cmd+=(--list-only)
  if [ "$(to_null_lower "$QUERY")" != "null" ] && [ -n "${QUERY:-}" ]; then
    disc_cmd+=(--query "$QUERY")
  fi
  if [ "$(to_null_lower "$MIN_PRICE")" != "null" ] && [ -n "${MIN_PRICE:-}" ]; then
    disc_cmd+=(--min-price "$MIN_PRICE")
  fi
  if [ "$(to_null_lower "$MAX_PRICE")" != "null" ] && [ -n "${MAX_PRICE:-}" ]; then
    disc_cmd+=(--max-price "$MAX_PRICE")
  fi
  if [ "$(to_null_lower "$PROP_TYPE")" != "null" ] && [ -n "${PROP_TYPE:-}" ]; then
    disc_cmd+=(--type "$PROP_TYPE")
  fi
  echo "Available slices:"
  SLICE_LIST=$("${disc_cmd[@]}")
  echo "$SLICE_LIST" | sed 's/^/- /'

  # Prompt for slice selection and pagination after listing
  read -r -p "Slices (comma-separated names, null for all): " SLICE_FILTER
  read -r -p "Start page (null for 1): " START_PAGE
  read -r -p "Pages (null for all): " PAGES

  # Build the actual discovery command
  declare -a run_cmd
  run_cmd=(python -m rightmove_scraper.cli discover-adaptive --out "$OUT_DIR")
  if [ "$(to_null_lower "$QUERY")" != "null" ] && [ -n "${QUERY:-}" ]; then
    run_cmd+=(--query "$QUERY")
  fi
  if [ "$(to_null_lower "$MIN_PRICE")" != "null" ] && [ -n "${MIN_PRICE:-}" ]; then
    run_cmd+=(--min-price "$MIN_PRICE")
  fi
  if [ "$(to_null_lower "$MAX_PRICE")" != "null" ] && [ -n "${MAX_PRICE:-}" ]; then
    run_cmd+=(--max-price "$MAX_PRICE")
  fi
  if [ "$(to_null_lower "$PROP_TYPE")" != "null" ] && [ -n "${PROP_TYPE:-}" ]; then
    run_cmd+=(--type "$PROP_TYPE")
  fi
  if [ "$(to_null_lower "$SLICE_FILTER")" != "null" ] && [ -n "${SLICE_FILTER:-}" ]; then
    run_cmd+=(--slices "$SLICE_FILTER")
  fi
  if [ "$(to_null_lower "$PAGES")" = "null" ] || [ -z "${PAGES:-}" ]; then
    if [ "$(to_null_lower "$START_PAGE")" != "null" ] && [ -n "${START_PAGE:-}" ]; then
      run_cmd+=(--start-page "$START_PAGE")
    fi
  else
    if [ "$(to_null_lower "$START_PAGE")" = "null" ] || [ -z "${START_PAGE:-}" ]; then
      run_cmd+=(--start-page "1")
    else
      run_cmd+=(--start-page "$START_PAGE")
    fi
    run_cmd+=(--pages "$PAGES")
  fi
  "${run_cmd[@]}"

  SEEDS="$OUT_DIR/discovered_adaptive_seeds.csv"
else
  echo "Running simple discovery..."
  declare -a disc_cmd
  disc_cmd=(python -m rightmove_scraper.cli discover-search --out "$OUT_DIR")
  if [ "$(to_null_lower "$QUERY")" != "null" ] && [ -n "${QUERY:-}" ]; then
    disc_cmd+=(--query "$QUERY")
  fi
  if [ "$(to_null_lower "$MIN_PRICE")" != "null" ] && [ -n "${MIN_PRICE:-}" ]; then
    disc_cmd+=(--min-price "$MIN_PRICE")
  fi
  if [ "$(to_null_lower "$MAX_PRICE")" != "null" ] && [ -n "${MAX_PRICE:-}" ]; then
    disc_cmd+=(--max-price "$MAX_PRICE")
  fi
  if [ "$(to_null_lower "$PROP_TYPE")" != "null" ] && [ -n "${PROP_TYPE:-}" ]; then
    disc_cmd+=(--type "$PROP_TYPE")
  fi
  # Prompt for pagination only for simple discovery
  read -r -p "Start page (null for 1): " START_PAGE
  read -r -p "Pages (null for all): " PAGES
  if [ "$(to_null_lower "$PAGES")" = "null" ] || [ -z "${PAGES:-}" ]; then
    if [ "$(to_null_lower "$START_PAGE")" != "null" ] && [ -n "${START_PAGE:-}" ]; then
      disc_cmd+=(--start-page "$START_PAGE")
    fi
    disc_cmd+=(--all)
  else
    if [ "$(to_null_lower "$START_PAGE")" = "null" ] || [ -z "${START_PAGE:-}" ]; then
      disc_cmd+=(--start-page "1")
    else
      disc_cmd+=(--start-page "$START_PAGE")
    fi
    disc_cmd+=(--pages "$PAGES")
  fi
  "${disc_cmd[@]}"

  SEEDS="$OUT_DIR/discovered_seeds.csv"
fi

if [ ! -f "$SEEDS" ]; then
  echo "No seeds file found at $SEEDS"
  exit 1
fi

URL_COUNT=$(($(wc -l < "$SEEDS") - 1))
if [ "$URL_COUNT" -le 0 ]; then
  echo "No URLs discovered."
  exit 1
fi

echo "Discovered $URL_COUNT URLs. Starting scraper..."
PYTHONPATH=$PWD/src python -m rightmove_scraper.cli scrape-seeds \
  --input "$SEEDS" \
  --out "$OUT_DIR" \
  --format "$FORMAT" \
  --max "$URL_COUNT"

echo "Done."


