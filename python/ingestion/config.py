# EPA Knowledge Graph - Python Ingestion Service Configuration

from pathlib import Path
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Find project root (where .env lives)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # App
    host: str = "127.0.0.1"
    port: int = 8001
    log_level: str = "info"
    reload: bool = False
    data_dir: Path = Path("./data")

    # ChromaDB
    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8000
    chroma_collection: str = "epa_methods"
    chroma_persist_dir: Path = Path("./data/chroma")
    chroma_use_cloud: bool = False
    chroma_api_key: str | None = None
    chroma_tenant: str | None = None
    chroma_database: str | None = None

    # Ingestion
    pdf_dir: Path = Path(
        "C:/Users/AlexJ/Documents/Coding/Repos/my-repos/EPA-Project/EPA_Methods_PDF"
    )
    chunk_size: int = 512
    chunk_overlap: int = 64
    toc_aware: bool = True
    extract_tables: bool = True
    max_file_size_mb: int = 100

    # Embeddings
    embedding_provider: Literal["openrouter", "ollama", "fastembed"] = "openrouter"

    # OpenRouter Embeddings
    openrouter_embedding_api_key: str | None = None
    openrouter_embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    openrouter_embedding_dimensions: int | None = 1536
    openrouter_embedding_batch_size: int = 32

    # Ollama Embeddings
    ollama_embedding_host: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_batch_size: int = 32

    # FastEmbed
    fastembed_model: str = "BAAI/bge-small-en-v1.5"
    fastembed_batch_size: int = 32

    # LLM (for metadata extraction)
    llm_provider: Literal["openrouter", "ollama", "none"] = "openrouter"
    openrouter_llm_api_key: str | None = None
    openrouter_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_llm_temperature: float = 0.1
    openrouter_llm_max_tokens: int = 2048
    ollama_llm_host: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:3b"
    ollama_llm_temperature: float = 0.1
    ollama_llm_max_tokens: int = 2048

    # Reranker (Phase 2+)
    reranker_provider: Literal["openrouter", "none"] = "openrouter"
    reranker_openrouter_api_key: str | None = None
    reranker_openrouter_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"

    # OpenRouter API Key (shared) - accepts both naming conventions
    openrouter_api_key: str | None = None

    model_config = ConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="EPA_KG__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for field in self.model_fields:
            value = getattr(self, field)
            if isinstance(value, str) and value == "":
                setattr(self, field, None)


settings = Settings()
