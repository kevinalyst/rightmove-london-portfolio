-- Create staging and final tables
CREATE TABLE IF NOT EXISTS RIGHTMOVE_STAGING LIKE RIGHTMOVE_ANALYSIS;
CREATE TABLE IF NOT EXISTS RIGHTMOVE_ANALYSIS (
  url STRING,
  rightmove_id STRING PRIMARY KEY,
  price_text STRING,
  price_value NUMBER,
  price_currency STRING,
  property_type STRING,
  property_title STRING,
  bedrooms FLOAT,
  bathrooms FLOAT,
  sizes STRING,
  tenure STRING,
  estate_agent STRING,
  key_features STRING,
  description STRING,
  council_tax STRING,
  parking STRING,
  garden STRING,
  accessibility STRING,
  latitude FLOAT,
  longitude FLOAT,
  address STRING,
  postal_district STRING,
  zone STRING,
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

