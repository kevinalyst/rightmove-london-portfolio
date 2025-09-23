"""
London TfL Zone Converter

This module provides functionality to convert latitude/longitude coordinates
to London Transport for London (TfL) zones (1-9).

Two methods are implemented:
1. Distance-based approximation (fallback method)
2. Official polygon-based lookup (requires TfL zone boundary data)

Author: London Property Price Analysis
Date: 2025-09-20
"""

import json
import os
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Union
from shapely.geometry import Point, shape
from geopy.distance import geodesic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Central London reference point (Charing Cross)
CENTRAL_LONDON = (51.5074, -0.1278)

# Approximate zone boundaries based on distance from Central London (km)
# These are rough approximations - official polygon data is more accurate
ZONE_BOUNDARIES_KM = {
    1: 0,      # Zone 1: Central London
    2: 5,      # Zone 2: ~5km from center
    3: 10,     # Zone 3: ~10km from center  
    4: 15,     # Zone 4: ~15km from center
    5: 20,     # Zone 5: ~20km from center
    6: 25,     # Zone 6: ~25km from center
    7: 30,     # Zone 7: ~30km from center
    8: 35,     # Zone 8: ~35km from center
    9: 40,     # Zone 9: ~40km from center
}

class TfLZoneConverter:
    """
    Converts coordinates to TfL zones using official polygon data or distance approximation.
    """
    
    def __init__(self, zone_data_path: Optional[str] = None):
        """
        Initialize the zone converter.
        
        Args:
            zone_data_path: Path to TfL zone polygon data (GeoJSON format)
                           If None, will use distance-based approximation
        """
        self.zone_polygons = None
        self.use_polygons = False
        
        if zone_data_path and os.path.exists(zone_data_path):
            self._load_zone_polygons(zone_data_path)
        else:
            logger.info("No zone polygon data provided. Using distance-based approximation.")
            logger.info("For more accurate results, download official TfL zone boundaries:")
            logger.info("- Transport for London: https://tfl.gov.uk/info-for/open-data-users/")
            logger.info("- London Datastore: https://data.london.gov.uk/")
            logger.info("- Save as GeoJSON format in data/tfl_zones.geojson")
    
    def _load_zone_polygons(self, zone_data_path: str):
        """Load TfL zone polygon data from GeoJSON file."""
        try:
            with open(zone_data_path, 'r') as f:
                geojson_data = json.load(f)
            
            self.zone_polygons = {}
            for feature in geojson_data['features']:
                zone = feature['properties'].get('zone') or feature['properties'].get('Zone')
                if zone:
                    self.zone_polygons[int(zone)] = shape(feature['geometry'])
            
            self.use_polygons = True
            logger.info(f"Loaded official TfL zone polygons for zones: {sorted(self.zone_polygons.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to load zone polygons from {zone_data_path}: {e}")
            logger.info("Falling back to distance-based approximation")
    
    def get_zone_from_coordinates(self, latitude: float, longitude: float) -> Optional[int]:
        """
        Get TfL zone from latitude/longitude coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Zone number (1-9) or None if outside London area
        """
        if pd.isna(latitude) or pd.isna(longitude):
            return None
        
        try:
            # Validate coordinates are in London area (rough bounds)
            if not (51.2 <= latitude <= 51.7 and -0.5 <= longitude <= 0.3):
                logger.warning(f"Coordinates ({latitude}, {longitude}) appear to be outside London")
                return None
            
            if self.use_polygons:
                return self._get_zone_from_polygons(latitude, longitude)
            else:
                return self._get_zone_from_distance(latitude, longitude)
                
        except Exception as e:
            logger.error(f"Error getting zone for coordinates ({latitude}, {longitude}): {e}")
            return None
    
    def _get_zone_from_polygons(self, latitude: float, longitude: float) -> Optional[int]:
        """Get zone using official polygon boundaries."""
        point = Point(longitude, latitude)
        
        # Check each zone polygon (starting from zone 1)
        for zone in sorted(self.zone_polygons.keys()):
            if self.zone_polygons[zone].contains(point):
                return zone
        
        return None
    
    def _get_zone_from_distance(self, latitude: float, longitude: float) -> Optional[int]:
        """Get zone using distance-based approximation from Central London."""
        # Calculate distance from Central London
        distance_km = geodesic(CENTRAL_LONDON, (latitude, longitude)).kilometers
        
        # Find appropriate zone based on distance
        for zone in sorted(ZONE_BOUNDARIES_KM.keys(), reverse=True):
            if distance_km >= ZONE_BOUNDARIES_KM[zone]:
                return zone
        
        return 1  # Default to zone 1 if very close to center
    
    def add_zones_to_dataframe(self, df: pd.DataFrame, 
                              lat_col: str = 'LATITUDE', 
                              lon_col: str = 'LONGITUDE',
                              zone_col: str = 'ZONE') -> pd.DataFrame:
        """
        Add TfL zone column to a pandas DataFrame.
        
        Args:
            df: DataFrame with coordinate columns
            lat_col: Name of latitude column
            lon_col: Name of longitude column  
            zone_col: Name of new zone column to create
            
        Returns:
            DataFrame with added zone column
        """
        logger.info(f"Adding TfL zones to {len(df)} records...")
        
        # Create a copy to avoid modifying original
        df_copy = df.copy()
        
        # Apply zone lookup to each row
        df_copy[zone_col] = df_copy.apply(
            lambda row: self.get_zone_from_coordinates(row[lat_col], row[lon_col]),
            axis=1
        )
        
        # Log results
        zone_counts = df_copy[zone_col].value_counts().sort_index()
        logger.info("Zone distribution:")
        for zone, count in zone_counts.items():
            if pd.notna(zone):
                logger.info(f"  Zone {int(zone)}: {count} records")
        
        null_count = df_copy[zone_col].isnull().sum()
        if null_count > 0:
            logger.warning(f"  {null_count} records could not be assigned to zones")
        
        return df_copy


def load_coordinates_from_file(file_path: str, 
                              lat_col: str = 'LATITUDE',
                              lon_col: str = 'LONGITUDE') -> pd.DataFrame:
    """
    Load coordinates from CSV file.
    
    Args:
        file_path: Path to CSV file with coordinates
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        
    Returns:
        DataFrame with coordinates
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} records from {file_path}")
        
        # Validate required columns exist
        if lat_col not in df.columns or lon_col not in df.columns:
            raise ValueError(f"Required columns {lat_col}, {lon_col} not found in file")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        raise


def save_results_to_file(df: pd.DataFrame, output_path: str):
    """Save DataFrame with zones to CSV file."""
    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving results to {output_path}: {e}")
        raise


def main():
    """
    Example usage of the TfL zone converter.
    """
    # Example coordinates in London
    test_coordinates = [
        (51.5074, -0.1278, "Charing Cross"),      # Zone 1
        (51.5155, -0.0922, "Liverpool Street"),   # Zone 1
        (51.5034, -0.2196, "Paddington"),         # Zone 1
        (51.4946, -0.1353, "Victoria"),           # Zone 1
        (51.5379, -0.1978, "Camden Town"),        # Zone 2
        (51.4656, -0.1141, "Stockwell"),          # Zone 2
        (51.5618, -0.1058, "Arsenal"),            # Zone 2
        (51.5907, -0.0640, "Finsbury Park"),      # Zone 2
    ]
    
    print("TfL Zone Converter - Test Run")
    print("=" * 40)
    
    # Initialize converter (without official polygon data)
    converter = TfLZoneConverter()
    
    # Test individual coordinates
    print("\nTesting individual coordinates:")
    for lat, lon, location in test_coordinates:
        zone = converter.get_zone_from_coordinates(lat, lon)
        print(f"{location:15} ({lat:.4f}, {lon:.4f}) -> Zone {zone}")
    
    # Test with DataFrame
    print("\nTesting with DataFrame:")
    test_df = pd.DataFrame({
        'LOCATION': [coord[2] for coord in test_coordinates],
        'LATITUDE': [coord[0] for coord in test_coordinates],
        'LONGITUDE': [coord[1] for coord in test_coordinates]
    })
    
    result_df = converter.add_zones_to_dataframe(test_df)
    print("\nResults:")
    print(result_df[['LOCATION', 'LATITUDE', 'LONGITUDE', 'ZONE']])
    
    # Instructions for using official data
    print("\n" + "=" * 60)
    print("IMPORTANT: Using Distance-Based Approximation")
    print("=" * 60)
    print("For production use, download official TfL zone boundaries:")
    print("1. Visit: https://tfl.gov.uk/info-for/open-data-users/")
    print("2. Or: https://data.london.gov.uk/")
    print("3. Download TfL Travelcard Zones boundary data")
    print("4. Save as GeoJSON format: data/tfl_zones.geojson")
    print("5. Initialize converter with: TfLZoneConverter('data/tfl_zones.geojson')")


if __name__ == "__main__":
    main()
