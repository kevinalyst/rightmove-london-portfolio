-- Materialize view on top of transforms
CREATE OR REPLACE VIEW ANALYSIS_READY AS
SELECT * FROM (
  WITH
  base AS (
    SELECT * FROM RIGHTMOVE_ANALYSIS
  ),
  dedup AS (
    SELECT * QUALIFY ROW_NUMBER() OVER (PARTITION BY rightmove_id ORDER BY updated_at DESC) = 1 FROM base
  )
  SELECT * FROM dedup
);

