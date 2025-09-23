-- Basic normalization for staging
CREATE OR REPLACE TEMP VIEW STG_CLEAN AS
SELECT
  url,
  rightmove_id,
  TRIM(price_text) AS price_text,
  TRY_TO_NUMBER(price_value) AS price_value,
  UPPER(price_currency) AS price_currency,
  LOWER(property_type) AS property_type,
  property_title,
  TRY_TO_NUMBER(bedrooms) AS bedrooms,
  TRY_TO_NUMBER(bathrooms) AS bathrooms,
  sizes,
  tenure,
  estate_agent,
  key_features,
  description,
  council_tax,
  parking,
  garden,
  accessibility,
  TRY_TO_NUMBER(latitude) AS latitude,
  TRY_TO_NUMBER(longitude) AS longitude
FROM RIGHTMOVE_STAGING;

