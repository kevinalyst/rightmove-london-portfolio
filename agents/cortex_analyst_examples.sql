-- Cortex Analyst prompts (use with Snowflake Cortex Analyst)
-- Context: Semantic View RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS

-- 1) Price band distribution by London zone
-- Prompt: "Show me the number of listings per price_band by zone."
SELECT zone, price_band, COUNT(*) AS listings
FROM RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS
GROUP BY zone, price_band
ORDER BY zone, price_band;

-- 2) Median price by property_type for Zone 2
-- Prompt: "Median price by property type in Zone 2"
SELECT property_type, MEDIAN(price_value) AS median_price
FROM RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS
WHERE zone = 'Zone 2'
GROUP BY property_type
ORDER BY median_price DESC;

-- 3) Top districts by count and average price
-- Prompt: "Top 10 postal districts by count and average price"
SELECT postal_district, COUNT(*) AS n, AVG(price_value) AS avg_price
FROM RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS
GROUP BY postal_district
ORDER BY n DESC
LIMIT 10;

