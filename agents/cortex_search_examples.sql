-- Cortex Search examples (unstructured)
-- Example 1: Find listings mentioning "garden" and "period features"
SELECT url, property_title, description
FROM RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS
WHERE CONTAINS(description, 'garden') AND CONTAINS(description, 'period');

-- Example 2: Keyword + structured filter
-- "Family home with parking in Zone 2"
SELECT url, property_title, parking, zone
FROM RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS
WHERE zone = 'Zone 2' AND CONTAINS(description, 'family') AND (parking ILIKE '%Yes%' OR parking ILIKE '%garage%');

