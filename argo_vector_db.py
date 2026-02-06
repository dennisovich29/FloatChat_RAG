"""
ARGO Vector Database Integration
Enable semantic search over Argo float metadata using ChromaDB and Sentence Transformers.
"""

import logging
from typing import List, Dict, Optional, Any
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import sqlalchemy as sa
from sqlalchemy import create_engine
from tqdm import tqdm
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArgoMetadataEmbedder:
    """
    Generate embeddings for Argo float metadata
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        return self.model.encode(texts).tolist()
    
    def format_profile_for_embedding(self, profile: Dict[str, Any]) -> str:
        """
        Format a profile record into a descriptive string for embedding
        """
        # Create a rich textual description
        date_str = str(profile.get('datetime', 'unknown date'))
        lat = profile.get('latitude')
        lon = profile.get('longitude')
        float_id = profile.get('float_id')
        
        description = (
            f"Argo float profile {float_id} recorded on {date_str}. "
            f"Location: Latitude {lat}, Longitude {lon}. "
            f"Data center: {profile.get('data_center', 'unknown')}. "
            f"Cycle number: {profile.get('cycle_number', 'unknown')}."
        )
        return description


class ArgoChromaStore:
    """
    ChromaDB storage for Argo embeddings
    """
    
    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "argo_profiles"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Use a simple embedding function for the collection if we push text directly
        # But we will use our own embedder for more control
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Argo float profiles metadata"}
        )
        logger.info(f"Initialized ChromaDB at {persist_dir}, collection: {collection_name}")
        
    def add_profiles(self, profiles_df: pd.DataFrame, embedder: ArgoMetadataEmbedder):
        """
        Add profiles from DataFrame to ChromaDB
        """
        if profiles_df.empty:
            logger.warning("No profiles to add")
            return
            
        logger.info(f"Adding {len(profiles_df)} profiles to vector DB...")
        
        documents = []
        metadatas = []
        ids = []
        
        # Prepare data in batches
        for _, row in tqdm(profiles_df.iterrows(), total=len(profiles_df)):
            profile_dict = row.to_dict()
            
            # Create text representation
            text = embedder.format_profile_for_embedding(profile_dict)
            documents.append(text)
            
            # Create metadata (convert non-serializable types)
            meta = {
                "float_id": str(row['float_id']),
                "cycle_number": int(row['cycle_number']) if pd.notna(row['cycle_number']) else -1,
                "latitude": float(row['latitude']) if pd.notna(row['latitude']) else 0.0,
                "longitude": float(row['longitude']) if pd.notna(row['longitude']) else 0.0,
                "date": str(row['datetime'])
            }
            metadatas.append(meta)
            
            # Unique ID: float_id + cycle_number
            ids.append(f"{row['float_id']}_{row['cycle_number']}")
            
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = embedder.embed_text(documents)
        
        # Add to Chroma (upsert)
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self.collection.upsert(
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end]
            )
            
        logger.info(f"✓ Successfully indexed {len(ids)} profiles")
        
    def search(self, query_text: str, embedder: ArgoMetadataEmbedder, k: int = 5) -> Dict:
        """
        Semantic search for profiles
        """
        logger.info(f"Searching for: '{query_text}'")
        
        query_embedding = embedder.embed_text([query_text])
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k
        )
        
        return results

def index_existing_db(db_url: str = "sqlite:///argo_data.db"):
    """
    Read from SQL database and populate Vector DB
    """
    if not os.path.exists("argo_data.db") and "sqlite" in db_url:
        logger.error(f"Database {db_url} not found! Run pipeline first.")
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
