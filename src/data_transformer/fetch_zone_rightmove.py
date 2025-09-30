import os
import pandas as pd
import numpy as np
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from snowflake.connector.pandas_tools import pd_writer
import time
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from convert_coordinate_tozone import TfLZoneConverter

start_time = time.time()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global converter for parallel processing
converter = TfLZoneConverter()

def convert_coordinate_to_zone(location_str):
    """
    Convert a coordinate string to TfL zone number with maximum speed.
    
    Args:
        location_str: String in format "lat,lon"
        
    Returns:
        int: Zone number (1-9) or None if conversion fails
    """
    if not location_str or pd.isna(location_str):
        return None
        
    try:
        # Parse coordinates from string
        lat_str, lon_str = location_str.split(',')
        latitude = float(lat_str.strip())
        longitude = float(lon_str.strip())
        
        # Convert to zone (no delays - full speed!)
        zone = converter.get_zone_from_coordinates(latitude, longitude)
        return zone
        
    except Exception as e:
        logger.warning(f"Zone conversion failed for {location_str}: {e}")
        return None

def process_batch_zones(batch_data):
    """
    Process a batch of coordinates to zones in parallel.
    
    Args:
        batch_data: List of (index, location_string) tuples
        
    Returns:
        List of (index, zone) tuples
    """
    results = []
    for idx, location_str in batch_data:
        zone = convert_coordinate_to_zone(location_str)
        results.append((idx, zone))
    return results

def parallel_zone_conversion(df, max_workers=10):
    """
    Convert coordinates to zones using parallel processing for maximum speed.
    
    Args:
        df: DataFrame with LOCATION column
        max_workers: Number of parallel workers (default 10 for brute force)
        
    Returns:
        Series with zone numbers
    """
    logger.info(f"Starting BRUTE FORCE parallel zone conversion with {max_workers} workers...")
    
    # Prepare data for parallel processing
    location_data = [(idx, location) for idx, location in enumerate(df['LOCATION'])]
    
    # Split into batches for parallel processing
    batch_size = max(1, len(location_data) // max_workers)
    batches = [location_data[i:i + batch_size] for i in range(0, len(location_data), batch_size)]
    
    logger.info(f"Processing {len(location_data)} coordinates in {len(batches)} batches...")
    
    # Initialize results array
    zones = [None] * len(df)
    
    # Process batches in parallel with threads (faster for I/O and geometric calculations)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batches
        future_to_batch = {executor.submit(process_batch_zones, batch): batch for batch in batches}
        
        # Collect results with progress bar
        completed_batches = 0
        with tqdm(total=len(batches), desc="Processing zone batches") as pbar:
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                
                # Store results back in original order
                for idx, zone in batch_results:
                    zones[idx] = zone
                
                completed_batches += 1
                pbar.update(1)
    
    logger.info("Parallel zone conversion completed!")
    return pd.Series(zones, index=df.index)

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
        
        # BRUTE FORCE ZONE CONVERSION WITH 10 PARALLEL WORKERS
        logger.info("Starting BRUTE FORCE zone conversion process...")
        logger.info("Using maximum parallel processing for fastest possible conversion...")
        
        # Convert coordinates to zones with parallel processing
        df['ZONE'] = parallel_zone_conversion(df, max_workers=10)
        
        print("=== %s seconds ===" % (time.time() - start_time))
        
        # Show results
        successful_conversions = df['ZONE'].notna().sum()
        total_records = len(df)
        logger.info(f"Zone conversion completed: {successful_conversions}/{total_records} zones assigned")
        
        # Show zone distribution
        zone_counts = df['ZONE'].value_counts().sort_index()
        logger.info("Zone distribution:")
        for zone, count in zone_counts.items():
            if pd.notna(zone):
                logger.info(f"  Zone {int(zone)}: {count} properties")
        
        print("Sample results:")
        print(df[['RIGHTMOVE_ID', 'LOCATION', 'ZONE']].head(10))
        print("=== %s seconds ===" % (time.time() - start_time))

        # Save results to database (only records with zones)
        df_with_zones = df[df['ZONE'].notna()]
        
        if len(df_with_zones) > 0:
            logger.info(f"Saving {len(df_with_zones)} records with zones to database...")
            
            # Convert zone to integer for database storage
            df_with_zones['ZONE'] = df_with_zones['ZONE'].astype(int)
            
            # Save with high-performance chunking
            df_with_zones.to_sql('rightmove_zones', engine, if_exists='replace', 
                               index=False, chunksize=5000, method=pd_writer)
            logger.info("Zone data saved successfully to database table 'rightmove_zones'")
            
            # Final statistics
            final_zone_counts = df_with_zones['ZONE'].value_counts().sort_index()
            logger.info("Final saved zone distribution:")
            for zone, count in final_zone_counts.items():
                logger.info(f"  Zone {zone}: {count} properties saved")
                
        else:
            logger.warning("No zones were successfully converted. Nothing saved to database.")
            
    except Exception as e:
        logger.error(f'ERROR: {e}')
        print('---ERROR---: %s' % e)
    finally:
        conn.close()
engine.dispose()

total_time = time.time() - start_time
logger.info(f"BRUTE FORCE zone conversion completed in {total_time:.2f} seconds")
print(f"=== TOTAL TIME: {total_time:.2f} seconds ===")
