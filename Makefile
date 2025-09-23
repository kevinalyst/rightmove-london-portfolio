.PHONY: setup scrape export-gcs load sql geocode agents-demo lint test docs

PYTHON := python3
PIP := pip

setup:
	$(PIP) install -U pip
	$(PIP) install -e '.[dev]'
	$(PYTHON) -m playwright install
	pre-commit install || true

scrape:
	# Quick smoke: discover 1 page and scrape max 5
	$(PYTHON) -m rightmove_scraper.cli scrape-search --pages 1 --max 5 --out out --format csv

export-gcs:
	# Export latest listings to GCS (requires google-cloud-storage and GCP auth)
	PYTHONPATH=scraper/src $(PYTHON) -m exporters.cli export-gcs --input out/listings.csv

load:
	# Load GCS files to Snowflake (mock path runs if creds missing)
	$(PYTHON) pipeline/gcs_to_snowflake.py --run

sql:
	# Apply SQL files in /sql sequentially
	$(PYTHON) pipeline/apply_sql.py --dir sql

geocode:
	# Enrich listings with address + zones (mock by default)
	$(PYTHON) pipeline/geocode_zones.py --input out/listings.csv --output out/listings_geocoded.csv

agents-demo:
	@echo "Run these in Snowflake Worksheets against the transformed view:"
	@echo "--- Cortex Analyst ---" && sed -n '1,200p' agents/cortex_analyst_examples.sql
	@echo "--- Cortex Search ---" && sed -n '1,200p' agents/cortex_search_examples.sql

lint:
	ruff check .
	black --check .
	mypy src scraper pipeline || true

test:
	pytest -q

docs:
	mkdocs build -q

