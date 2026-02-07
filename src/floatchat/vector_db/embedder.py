"""
ARGO Metadata Embedder - Generate vector embeddings for float profiles
"""

import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

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
