"""
ARGO ChromaDB Store - Vector database for semantic search
"""

import logging
from typing import List, Dict
import pandas as pd
import chromadb
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ArgoChromaStore:
    """
    ChromaDB storage for Argo embeddings
    """
    
    def __init__(self, persist_dir: str = "./data/vector_db", collection_name: str = "argo_profiles"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Use a simple embedding function for the collection if we push text directly
        # But we will use our own embedder for more control
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Argo float profiles metadata"}
        )
        logger.info(f"Initialized ChromaDB at {persist_dir}, collection: {collection_name}")
        
    def add_profiles(self, profiles_df: pd.DataFrame, embedder):
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
        
    def search(self, query_text: str, embedder, k: int = 5) -> Dict:
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
