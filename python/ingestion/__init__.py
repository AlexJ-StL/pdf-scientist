# EPA Knowledge Graph - Python Ingestion Package

from .config import settings, Settings
from .chunking import EPAMethodChunker, Chunk, chunk_pdf
from .embeddings import (
    EmbeddingProvider,
    OpenRouterEmbeddingProvider,
    OllamaEmbeddingProvider,
    get_embedding_provider,
)
from .metadata import (
    MetadataExtractor,
    OpenRouterMetadataExtractor,
    OllamaMetadataExtractor,
    get_metadata_extractor,
    MethodMetadata,
)
from .chroma_client import ChromaManager, create_chroma_manager

__all__ = [
    "settings",
    "Settings",
    "EPAMethodChunker",
    "Chunk",
    "chunk_pdf",
    "EmbeddingProvider",
    "OpenRouterEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "get_embedding_provider",
    "MetadataExtractor",
    "OpenRouterMetadataExtractor",
    "OllamaMetadataExtractor",
    "get_metadata_extractor",
    "MethodMetadata",
    "ChromaManager",
    "create_chroma_manager",
]