"""
ARGO Data Pipeline - Direct API Access (No Downloads)
Access THREDDS OPeNDAP endpoint and stream data directly to SQL/Parquet
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArgoAPIClient:
    """
    Direct API access to ARGO data via THREDDS OPeNDAP
    No file downloads required!
    """
    
    def __init__(self, base_url: str = "https://www.ncei.noaa.gov/thredds-ocean"):
        self.base_url = base_url
        self.catalog_base = f"{base_url}/catalog/argo/gadr"
        self.opendap_base = f"{base_url}/dodsC/argo/gadr"
        
    def list_data_centers(self) -> List[str]:
        """List available ARGO data centers via API"""
        catalog_url = f"{self.catalog_base}/catalog.html"
        logger.info(f"Fetching data centers...")
        
        try:
            response = requests.get(catalog_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            centers = []
            for img in soup.find_all('img', alt='[DIR]'):
                parent = img.find_parent('tr')
                if parent:
                    link = parent.find('a')
                    if link:
                        center_name = link.text.strip().strip('/')
                        if center_name and center_name not in centers:
                            centers.append(center_name)
            
            logger.info(f"Found {len(centers)} data centers")
            return sorted(list(set(centers)))
        except Exception as e:
            logger.error(f"Error: {e}")
            # Fallback to known centers
            return ['aoml', 'atlantic', 'bodc', 'coriolis', 'csio', 'csiro', 
                    'incois', 'indian', 'jma', 'kiost', 'kma', 'kordi', 
                    'meds', 'nmdis', 'pacific']
    
    def list_floats(self, data_center: str, max_floats: Optional[int] = None) -> List[str]:
        """List available float IDs via API"""
        catalog_url = f"{self.catalog_base}/{data_center}/catalog.html"
        logger.info(f"Fetching floats from {data_center}...")
        
        try:
            response = requests.get(catalog_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            floats = []
            for img in soup.find_all('img', alt='[DIR]'):
                parent = img.find_parent('tr')
                if parent:
                    link = parent.find('a')
                    if link:
                        float_id = link.text.strip().strip('/')
                        if float_id.isdigit():
                            floats.append(float_id)
                            if max_floats and len(floats) >= max_floats:
                                break
            
            logger.info(f"Found {len(floats)} floats")
            return sorted(floats)
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def get_opendap_url(self, data_center: str, float_id: str) -> str:
        """Construct OPeNDAP URL for direct data access"""
        filename = f"{float_id}_prof.nc"
        return f"{self.opendap_base}/{data_center}/{float_id}/{filename}"
    
    def fetch_float_data(self, data_center: str, float_id: str) -> Optional[xr.Dataset]:
        """
        Fetch float data directly via OPeNDAP API
        No download required - data streams directly!
        """
        url = self.get_opendap_url(data_center, float_id)
        logger.info(f"Fetching via API: {float_id}")
        
        try:
            # Open dataset directly from OPeNDAP endpoint
            ds = xr.open_dataset(url, decode_times=False)
            logger.info(f"✓ Successfully accessed {float_id}")
            return ds
        except Exception as e:
            logger.error(f"✗ Error accessing {float_id}: {e}")
            return None
    
    def fetch_region_data(self, data_center: str, lat_min: float, lat_max: float, 
                          lon_min: float, lon_max: float, max_floats: int = 100) -> List[xr.Dataset]:
        """
        Fetch all floats in a geographic region via API
        """
        logger.info(f"Fetching floats in region: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
        
        floats = self.list_floats(data_center, max_floats=max_floats)
        datasets = []
        
        for float_id in floats:
            ds = self.fetch_float_data(data_center, float_id)
            if ds is not None:
                # Quick filter by region
                try:
                    lats = ds['LATITUDE'].values
                    lons = ds['LONGITUDE'].values
                    
                    # Check if any profile is in the region
                    in_region = np.any(
                        (lats >= lat_min) & (lats <= lat_max) &
                        (lons >= lon_min) & (lons <= lon_max)
                    )
                    
                    if in_region:
                        datasets.append(ds)
                        logger.info(f"✓ Float {float_id} is in region")
                    else:
                        ds.close()
                except:
                    ds.close()
        
        logger.info(f"Found {len(datasets)} floats in region")
        return datasets


class ArgoStreamProcessor:
    """
    Process ARGO data directly from API to SQL/Parquet
    No intermediate file storage!
    """
    
    def __init__(self, output_dir: str = "./argo_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_profiles(self, ds: xr.Dataset, float_id: str, data_center: str) -> pd.DataFrame:
        """Extract profile data from xarray Dataset"""
        profiles_data = []
        n_prof = ds.dims.get('N_PROF', 1)
        
        for i in range(n_prof):
            profile = {
                'float_id': float_id,
                'data_center': data_center,
                'profile_id': i,
                'cycle_number': self._get_value(ds, 'CYCLE_NUMBER', i),
                'platform_number': self._get_value(ds, 'PLATFORM_NUMBER', i),
                'latitude': self._get_value(ds, 'LATITUDE', i),
                'longitude': self._get_value(ds, 'LONGITUDE', i),
                'juld': self._get_value(ds, 'JULD', i),
            }
            
            # Convert Julian date to datetime
            if profile['juld'] is not None and not np.isnan(profile['juld']):
                try:
                    reference_date = pd.Timestamp('1950-01-01')
                    profile['datetime'] = reference_date + pd.Timedelta(days=float(profile['juld']))
                except:
                    profile['datetime'] = None
            else:
                profile['datetime'] = None
            
            profiles_data.append(profile)
        
        return pd.DataFrame(profiles_data)
    
    def extract_measurements(self, ds: xr.Dataset, float_id: str) -> pd.DataFrame:
        """Extract measurement data from xarray Dataset"""
        measurements = []
        n_prof = ds.dims.get('N_PROF', 1)
        n_levels = ds.dims.get('N_LEVELS', 0)
        
        for prof_idx in range(n_prof):
            for level_idx in range(n_levels):
                meas = {
                    'float_id': float_id,
                    'profile_id': prof_idx,
                    'level': level_idx,
                    'pressure': self._get_value(ds, 'PRES', (prof_idx, level_idx)),
                    'temperature': self._get_value(ds, 'TEMP', (prof_idx, level_idx)),
                    'salinity': self._get_value(ds, 'PSAL', (prof_idx, level_idx)),
                }
                
                # Only keep if we have pressure data
                if meas['pressure'] is not None and not np.isnan(meas['pressure']):
                    measurements.append(meas)
        
        df = pd.DataFrame(measurements)
        
        # Remove rows with all NaN measurements
        if not df.empty:
            df = df.dropna(subset=['pressure', 'temperature', 'salinity'], how='all')
        
        return df
    
    def _get_value(self, ds: xr.Dataset, var_name: str, index):
        """Safely extract value from dataset"""
        if var_name not in ds.variables:
            return None
        try:
            if isinstance(index, tuple):
                value = ds[var_name].values[index]
            else:
                value = ds[var_name].values[index]
            
            if isinstance(value, bytes):
                value = value.decode('utf-8').strip()
            elif isinstance(value, np.ndarray) and value.dtype.kind in ['S', 'U']:
                value = str(value).strip()
            
            if isinstance(value, (np.floating, float)) and (np.isnan(value) or abs(value) > 1e10):
                return None
            
            return value
        except:
            return None
    
    def stream_to_sql(self, ds: xr.Dataset, float_id: str, data_center: str, 
                      db_url: str = "sqlite:///argo_data.db"):
        """
        Stream data directly from API to SQL database
        No file storage needed!
        """
        logger.info(f"Streaming {float_id} to SQL...")
        
        # Extract data
        profiles_df = self.extract_profiles(ds, float_id, data_center)
        measurements_df = self.extract_measurements(ds, float_id)
        
        if profiles_df.empty:
            logger.warning(f"No profile data for {float_id}")
            return
        
        # Write to SQL
        engine = create_engine(db_url)
        profiles_df.to_sql('profiles', engine, if_exists='append', index=False, method='multi')
        
        if not measurements_df.empty:
            measurements_df.to_sql('measurements', engine, if_exists='append', index=False, method='multi')
        
        logger.info(f"✓ Streamed {float_id}: {len(profiles_df)} profiles, {len(measurements_df)} measurements")
    
    def stream_to_parquet(self, ds: xr.Dataset, float_id: str, data_center: str):
        """
        Stream data directly from API to Parquet files
        No intermediate storage!
        """
        logger.info(f"Streaming {float_id} to Parquet...")
        
        profiles_df = self.extract_profiles(ds, float_id, data_center)
        measurements_df = self.extract_measurements(ds, float_id)
        
        if not profiles_df.empty:
            profiles_df.to_parquet(
                self.output_dir / f"profiles_{data_center}_{float_id}.parquet",
                engine='pyarrow',
                compression='snappy',
                index=False
            )
        
        if not measurements_df.empty:
            measurements_df.to_parquet(
                self.output_dir / f"measurements_{data_center}_{float_id}.parquet",
                engine='pyarrow',
                compression='snappy',
                index=False
            )
        
        logger.info(f"✓ Streamed {float_id} to Parquet")
    
    def create_indexes(self, db_url: str = "sqlite:///argo_data.db"):
        """Create database indexes for better performance"""
        logger.info("Creating indexes...")
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_profiles_float ON profiles(float_id)"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_profiles_datetime ON profiles(datetime)"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_profiles_location ON profiles(latitude, longitude)"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_measurements_float ON measurements(float_id)"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_measurements_profile ON measurements(profile_id)"))
            conn.commit()


def stream_multiple_floats(data_center: str, num_floats: int = 10, 
                          db_url: str = "sqlite:///argo_data.db",
                          save_parquet: bool = True):
    """
    Stream multiple floats directly from API to SQL/Parquet
    NO DOWNLOADS REQUIRED!
    """
    
    # Initialize
    api = ArgoAPIClient()
    processor = ArgoStreamProcessor()
    
    # Get float list
    logger.info(f"Fetching float list from {data_center}...")
    floats = api.list_floats(data_center, max_floats=num_floats)
    
    if not floats:
        logger.error("No floats found!")
        return
    
    logger.info(f"Processing {len(floats)} floats via API...")
    
    # Process each float
    success_count = 0
    for i, float_id in enumerate(floats, 1):
        logger.info(f"[{i}/{len(floats)}] Processing {float_id}")
        
        # Fetch data via API
        ds = api.fetch_float_data(data_center, float_id)
        
        if ds is not None:
            try:
                # Stream to SQL
                processor.stream_to_sql(ds, float_id, data_center, db_url)
                
                # Stream to Parquet (optional)
                if save_parquet:
                    processor.stream_to_parquet(ds, float_id, data_center)
                
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing {float_id}: {e}")
            finally:
                ds.close()
        
        time.sleep(0.5)  # Be nice to the server
    
    # Create indexes
    processor.create_indexes(db_url)
    
    logger.info(f"\n✓ Complete! Successfully processed {success_count}/{len(floats)} floats")
    logger.info(f"  Database: {db_url}")
    if save_parquet:
        logger.info(f"  Parquet files: {processor.output_dir}/")


def query_data_example(db_url: str = "sqlite:///argo_data.db"):
    """Example queries on the streamed data"""
    engine = create_engine(db_url)
    
    print("\n=== Data Summary ===")
    
    # Count profiles
    query = "SELECT COUNT(*) as count FROM profiles"
    result = pd.read_sql(query, engine)
    print(f"Total profiles: {result['count'].values[0]}")
    
    # Count measurements
    query = "SELECT COUNT(*) as count FROM measurements"
    result = pd.read_sql(query, engine)
    print(f"Total measurements: {result['count'].values[0]}")
    
    # Geographic coverage
    query = """
    SELECT 
        MIN(latitude) as min_lat, MAX(latitude) as max_lat,
        MIN(longitude) as min_lon, MAX(longitude) as max_lon,
        COUNT(DISTINCT float_id) as num_floats
    FROM profiles
    """
    result = pd.read_sql(query, engine)
    print(f"\nGeographic coverage:")
    print(result)
    
    # Recent profiles
    query = """
    SELECT float_id, datetime, latitude, longitude, cycle_number
    FROM profiles
    WHERE datetime IS NOT NULL
    ORDER BY datetime DESC
    LIMIT 5
    """
    result = pd.read_sql(query, engine)
    print(f"\nRecent profiles:")
    print(result)


def main():
    """
    Complete API-based pipeline - NO DOWNLOADS!
    """
    
    print("=" * 60)
    print("ARGO Data Pipeline - Direct API Access")
    print("No file downloads required!")
    print("=" * 60)
    
    # Configuration
    DATA_CENTER = 'aoml'  # Change as needed
    NUM_FLOATS = 10       # Number of floats to process
    DB_URL = "sqlite:///argo_data.db"
    
    # Stream data directly from API
    stream_multiple_floats(
        data_center=DATA_CENTER,
        num_floats=NUM_FLOATS,
        db_url=DB_URL,
        save_parquet=True
    )
    
    # Query the data
    query_data_example(DB_URL)
    
    print("\n✓ Pipeline complete! Data ready for analysis.")


if __name__ == "__main__":
    main()
