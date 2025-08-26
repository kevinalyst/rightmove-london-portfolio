#!/usr/bin/env bash
set -euo pipefail

# Generate an adaptive slice plan and save it as a txt file under ./out/<query>/<min>/<max>/<type>.txt
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

OUT_DIR="./out"

read -r -p "Keywords query (null for none): " QUERY
read -r -p "Min price (null for none): " MIN_PRICE
read -r -p "Max price (null for none): " MAX_PRICE
read -r -p "Property type [flat|detached|semi-detached|terraced|bungalow] (null for all): " PROP_TYPE

to_null_lower() { printf "%s" "${1:-}" | tr '[:upper:]' '[:lower:]'; }

declare -a plan_cmd
plan_cmd=(python -m rightmove_scraper.cli plan-adaptive --plan-dir "$OUT_DIR")

if [ "$(to_null_lower "$QUERY")" != "null" ] && [ -n "${QUERY:-}" ]; then
  plan_cmd+=(--query "$QUERY")
fi
if [ "$(to_null_lower "$MIN_PRICE")" != "null" ] && [ -n "${MIN_PRICE:-}" ]; then
  plan_cmd+=(--min-price "$MIN_PRICE")
fi
if [ "$(to_null_lower "$MAX_PRICE")" != "null" ] && [ -n "${MAX_PRICE:-}" ]; then
  plan_cmd+=(--max-price "$MAX_PRICE")
fi
if [ "$(to_null_lower "$PROP_TYPE")" != "null" ] && [ -n "${PROP_TYPE:-}" ]; then
  plan_cmd+=(--type "$PROP_TYPE")
fi

echo "Generating adaptive slice plan..."
PLAN_PATH="$(${plan_cmd[@]})"

echo "Plan saved to: $PLAN_PATH"
echo "You can pass this path to scripts/run_discover_and_scrape.sh when prompted."


