# EPA Knowledge Graph - Python Ingestion Package

from .chroma_client import ChromaManager, create_chroma_manager
from .chunking import Chunk, EPAMethodChunker, chunk_pdf
from .config import Settings, settings
from .embeddings import (
    EmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    get_embedding_provider,
)
from .metadata import (
    MetadataExtractor,
    MethodMetadata,
    OllamaMetadataExtractor,
    OpenRouterMetadataExtractor,
    get_metadata_extractor,
)

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
