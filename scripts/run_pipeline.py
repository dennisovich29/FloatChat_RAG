"""
Main entry point for running the Argo data pipeline
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floatchat.pipeline.runner import stream_multiple_floats
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def query_data_example(db_url: str = "sqlite:///data/databases/argo_data.db"):
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
    NUM_FLOATS = 2        # Number of floats to process
    DB_URL = "sqlite:///data/databases/argo_data.db"
    
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
