#!/usr/bin/env bash
set -euo pipefail

# Discover listing URLs from all slicers in a plan txt, write per-slice CSVs, and merge unique URLs.

export PYTHONPATH=${PYTHONPATH:-$PWD/src}

if [ "${ALLOW_DISCOVERY:-}" != "true" ]; then
  echo "Warning: ALLOW_DISCOVERY is not 'true'. Discovery will be blocked by the app."
fi
if [ ! -f "consent.txt" ]; then
  echo "Error: consent.txt not found in project root. Create it to enable discovery."
  exit 2
fi

OUT_DIR="./out"
PER_SLICE_DIR="$OUT_DIR/per_slice"

read -r -p "Path to adaptive plan txt: " PLAN_FILE
if [ ! -f "$PLAN_FILE" ]; then
  echo "Error: plan file not found: $PLAN_FILE"
  exit 1
fi

read -r -p "Start slice index (1-based, null for first): " START_SLICE
read -r -p "Start page (null for 1): " START_PAGE
read -r -p "Pages per slice (null for all): " PAGES

declare -a cmd
cmd=(python -m rightmove_scraper.cli discover-from-plan --plan-file "$PLAN_FILE" --out "$OUT_DIR" --per-slice-dir "$PER_SLICE_DIR")

to_null_lower() { printf "%s" "${1:-}" | tr '[:upper:]' '[:lower:]'; }

if [ "$(to_null_lower "$START_SLICE")" != "null" ] && [ -n "${START_SLICE:-}" ]; then
  cmd+=(--start-slice "$START_SLICE")
fi
if [ "$(to_null_lower "$PAGES")" = "null" ] || [ -z "${PAGES:-}" ]; then
  if [ "$(to_null_lower "$START_PAGE")" != "null" ] && [ -n "${START_PAGE:-}" ]; then
    cmd+=(--start-page "$START_PAGE")
  fi
else
  if [ "$(to_null_lower "$START_PAGE")" = "null" ] || [ -z "${START_PAGE:-}" ]; then
    cmd+=(--start-page "1")
  else
    cmd+=(--start-page "$START_PAGE")
  fi
  cmd+=(--pages "$PAGES")
fi

"${cmd[@]}"

echo "Per-slice CSVs written to: $PER_SLICE_DIR"
echo "Merging unique URLs into $OUT_DIR/discovered_adaptive_seeds.csv"

# Build merged CSV by scanning all per-slice files, removing duplicates
TMP_MERGED="$OUT_DIR/.merged_urls.tmp"
echo "url" > "$TMP_MERGED"

if compgen -G "$PER_SLICE_DIR/*.csv" > /dev/null; then
  awk -F, 'NR==1{next} {print $2}' "$PER_SLICE_DIR"/*.csv | sed 's/^\"\(.*\)\"$/\1/' | awk 'BEGIN{print "url"} {print}' | awk '!seen[$0]++' > "$OUT_DIR/discovered_adaptive_seeds.csv"
else
  echo "No per-slice CSVs found to merge."
fi

echo "Done."


