-- Produce analysis_ready_<date> via CTEs
WITH
base AS (
  SELECT * FROM STG_CLEAN
),
dedup AS (
  SELECT * QUALIFY ROW_NUMBER() OVER (PARTITION BY rightmove_id ORDER BY updated_at DESC) = 1 FROM base
),
price_aug AS (
  SELECT *, CASE WHEN price_value < 500000 THEN 'sub_500k' WHEN price_value < 1000000 THEN '500k_to_1m' ELSE '1m_plus' END AS price_band FROM dedup
)
SELECT * FROM price_aug;

