"""
ARGO Data Processor - Extract and stream data to SQL/Parquet
"""

import logging
import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path
from sqlalchemy import create_engine
import sqlalchemy as sa

logger = logging.getLogger(__name__)


class ArgoStreamProcessor:
    """
    Process ARGO data directly from API to SQL/Parquet
    No intermediate file storage!
    """
    
    def __init__(self, output_dir: str = "./data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_profiles(self, ds: xr.Dataset, float_id: str, data_center: str) -> pd.DataFrame:
        """Extract profile data from xarray Dataset"""
        profiles_data = []
        n_prof = ds.sizes.get('N_PROF', 1)
        
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
        n_prof = ds.sizes.get('N_PROF', 1)
        n_levels = ds.sizes.get('N_LEVELS', 0)
        
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
                      db_url: str = "sqlite:///data/databases/argo_data.db"):
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
    
    def create_indexes(self, db_url: str = "sqlite:///data/databases/argo_data.db"):
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
