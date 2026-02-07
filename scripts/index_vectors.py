"""
Vector Database Manager - Index and search Argo float data
"""

import logging
import sys
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def index_existing_db(db_url: str = "sqlite:///data/databases/argo_data.db"):
    """
    Read from SQL database and populate Vector DB
    """
    db_path = "data/databases/argo_data.db"
    if not os.path.exists(db_path) and "sqlite" in db_url:
        logger.error(f"Database {db_path} not found! Run pipeline first.")
        return

    logger.info(f"Reading from {db_url}...")
    try:
        engine = create_engine(db_url)
        # Read unique profiles (deduplicated by float_id and cycle_number)
        query = """
        SELECT DISTINCT float_id, cycle_number, latitude, longitude, datetime, data_center
        FROM profiles
        """
        profiles_df = pd.read_sql(query, engine)
        logger.info(f"Loaded {len(profiles_df)} profiles from SQL")
        
        if not profiles_df.empty:
            embedder = ArgoMetadataEmbedder()
            chroma = ArgoChromaStore()
            chroma.add_profiles(profiles_df, embedder)
            
    except Exception as e:
        logger.error(f"Error reading database: {e}")


def main():
    """
    Main execution for vector DB population/search
    """
    import argparse
    parser = argparse.ArgumentParser(description="Argo Vector DB Manager")
    parser.add_argument("--index", action="store_true", help="Index existing SQL database")
    parser.add_argument("--query", type=str, help="Search query string")
    parser.add_argument("--limit", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    
    if args.index:
        index_existing_db()
    
    if args.query:
        embedder = ArgoMetadataEmbedder()
        chroma = ArgoChromaStore()
        results = chroma.search(args.query, embedder, k=args.limit)
        
        print("\n=== Search Results ===")
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            print(f"\nResult {i+1}:")
            print(f"Text: {doc}")
            print(f"Metadata: {meta}")


if __name__ == "__main__":
    main()
