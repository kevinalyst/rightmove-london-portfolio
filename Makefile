

.PHONY: setup scrape10 transform10

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup:
	@test -x $(VENV)/bin/python || python3 -m venv $(VENV)
	$(PYTHON) -m ensurepip --upgrade || true
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e '.[dev]'
	$(PYTHON) -m playwright install --with-deps || $(PYTHON) -m playwright install

# A) CLI SCRAPE (ten listings)
# - Produces NDJSON and CSV under data/raw/

scrape10: setup
	@mkdir -p data/raw
	@touch consent.txt
	ALLOW_DISCOVERY=true $(PYTHON) -m rightmove_scraper.cli scrape-search --pages 1 --max 10 --out data/raw --format csv
	@# Normalize filenames and emit NDJSON
	$(PYTHON) pipeline/csv_to_ndjson.py --input data/raw/listings.csv --csv-out data/raw/listings_10.csv --ndjson-out data/raw/listings_10.ndjson

# B) LOCAL TRANSFORM (no Snowflake)
# - Consumes raw sample and writes Parquet + CSV under data/processed/
transform10: setup
	@mkdir -p data/processed
	$(PYTHON) pipeline/local_rightmove_transform.py --input-csv data/raw/listings_10.csv --output-prefix data/processed/listings_10_transformed

