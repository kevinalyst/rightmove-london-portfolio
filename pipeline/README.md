Pipeline — GCS → Snowflake; Geocoding & Zones

Components
- gcs_to_snowflake.py: staged COPY + MERGE with idempotency; chunked loads
- geocode_zones.py: pluggable geocoder (mock by default) + London zone mapping
- config/mapping_zones.csv: sample mapping docs

Quickstart
```bash
make load   # mock if Snowflake creds absent
make geocode
```

Snowflake strategy
- Stage CSV/Parquet to external stage, COPY INTO staging table, then MERGE into final.
- Keys: rightmove_id (natural id), url.
- Idempotent: MERGE on id; keep latest non-null fields.

Geocoding
- Provider set via GEOCODER_PROVIDER (mock|nominatim|google|...)
- Cache results locally (simple csv cache) to avoid re-requests.

Placeholders
- Snowflake: ORG.ACCOUNT / WAREHOUSE / DB / SCHEMA
- Stage: %RIGHTMOVE_STAGE (user stage example)

