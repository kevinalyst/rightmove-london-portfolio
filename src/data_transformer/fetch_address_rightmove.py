import os
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.point import Point
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from snowflake.connector.pandas_tools import pd_writer
import time
from tqdm import tqdm
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging

start_time = time.time()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize geocoder with timeout and user agent
geolocator = Nominatim(user_agent="rightmove_transformer", timeout=10)

def geocode_location(location_str):
    """
    Safely geocode a location string with error handling and retries.
    
    Args:
        location_str: String in format "lat,lon"
        
    Returns:
        str: Address string or None if geocoding fails
    """
    if not location_str or pd.isna(location_str):
        return None
        
    try:
        # Add small delay to respect Nominatim usage policy (1 req/sec)
        time.sleep(1.1)
        
        # Reverse geocode the coordinates
        location = geolocator.reverse(location_str)
        
        if location and location.address:
            return location.address
        else:
            logger.warning(f"No address found for coordinates: {location_str}")
            return None
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding failed for {location_str}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error geocoding {location_str}: {e}")
        return None

engine = create_engine(URL(
                account = os.getenv("SNOWFLAKE_ACCOUNT"),
                user = os.getenv("SNOWFLAKE_USER"),
                password = os.getenv("SNOWFLAKE_PASSWORD"),
                role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
                warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                database = os.getenv("SNOWFLAKE_DATABASE", "RIGHTMOVE_LONDON_SELL"),
                schema = os.getenv("SNOWFLAKE_SCHEMA", "CLOUDRUN_DXLVF")))

with engine.connect() as conn:
    try:
        query = """ SELECT
                      RIGHTMOVE_ID,
                      CONCAT(TO_VARCHAR(ROUND(LATITUDE,6)), ',', TO_VARCHAR(ROUND(LONGITUDE,6))) AS LOCATION
                    FROM rightmove_london_sell.cloudrun_dxlvf."03sep"
                    WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL;"""
        print("=== %s seconds ===" % (time.time() - start_time))

        df = pd.read_sql(query, conn)
        
        # Clean column names
        df.columns = [col.upper() for col in df.columns]
        
        logger.info(f"Loaded {len(df)} records from database")
        print(f"Sample data:")
        print(df.head())
        print("=== %s seconds ===" % (time.time() - start_time))
        
        # Geocode addresses using pandas with progress bar
        logger.info("Starting geocoding process...")
        
        # Initialize progress bar
        tqdm.pandas(desc="Geocoding addresses")
        
        # Apply geocoding with progress tracking
        df['ADDRESS'] = df['LOCATION'].progress_apply(geocode_location)
        
        print("=== %s seconds ===" % (time.time() - start_time))
        
        # Show results
        successful_geocodes = df['ADDRESS'].notna().sum()
        total_records = len(df)
        logger.info(f"Geocoding completed: {successful_geocodes}/{total_records} addresses found")
        
        print("Sample results:")
        print(df[['RIGHTMOVE_ID', 'LOCATION', 'ADDRESS']].head())
        print("=== %s seconds ===" % (time.time() - start_time))

        # Save results to database (only records with addresses)
        df_with_addresses = df[df['ADDRESS'].notna()]
        
        if len(df_with_addresses) > 0:
            logger.info(f"Saving {len(df_with_addresses)} records to database...")
            df_with_addresses.to_sql('rightmove_addresses', engine, if_exists='append', 
                                   index=False, chunksize=1000, method=pd_writer)
            logger.info("Data saved successfully to database")
        else:
            logger.warning("No addresses were successfully geocoded. Nothing saved to database.")
    except Exception as e:
        print('---ERROR---: %s' % e)
    finally:
        conn.close()
engine.dispose()

print("=== %s seconds ===" % (time.time() - start_time))
        
    

