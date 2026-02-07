"""
FloatChat RAG - Argo Float Data Pipeline with RAG Capabilities
"""

__version__ = "0.1.0"

from .pipeline.client import ArgoAPIClient
from .pipeline.processor import ArgoStreamProcessor
from .pipeline.runner import stream_multiple_floats
from .vector_db.embedder import ArgoMetadataEmbedder
from .vector_db.store import ArgoChromaStore

__all__ = [
    "ArgoAPIClient",
    "ArgoStreamProcessor",
    "stream_multiple_floats",
    "ArgoMetadataEmbedder",
    "ArgoChromaStore",
]
