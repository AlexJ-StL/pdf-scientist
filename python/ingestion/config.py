# EPA Knowledge Graph - Python Ingestion Service Configuration
#
# Env-var convention matches the Rust service (config-rs, separator "__"):
#   EPA_KG__APP__HOST, EPA_KG__CHROMA__HOST, EPA_KG__EMBEDDING__PROVIDER, ...
# Secrets are read from the bare process environment (OPENROUTER_API_KEY,
# CHROMADB_API_KEY) and never from a committed file.

import os
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

# Find project root (where .env lives)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class _Base(BaseSettings):
    """Base settings that bind nested env vars: EPA_KG__<GROUP>__<FIELD>.

    Empty strings coming from the environment are normalized to None so a
    blank value never overrides a real default.
    """

    model_config = ConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="EPA_KG__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    @model_validator(mode="after")
    def _coerce_empty_strings(self):
        for field in self.model_fields:
            value = getattr(self, field)
            if isinstance(value, str) and value == "":
                setattr(self, field, None)
        return self


class AppSettings(_Base):
    host: str = "127.0.0.1"
    port: int = 8001
    log_level: str = "info"
    reload: bool = False
    data_dir: Path = Path("./data")


class ChromaSettings(_Base):
    host: str = "127.0.0.1"
    port: int = 8000
    collection: str = "epa_methods"
    persist_dir: Path = Path("./data/chroma")
    use_cloud: bool = False
    api_key: str | None = None
    tenant: str | None = None
    database: str | None = None


class IngestionSettings(_Base):
    pdf_dir: Path = Path(
        "C:/Users/AlexJ/Documents/Coding/Repos/my-repos/EPA-Project/EPA_Methods_PDF"
    )
    chunk_size: int = 512
    chunk_overlap: int = 64
    toc_aware: bool = True
    extract_tables: bool = True
    max_file_size_mb: int = 100


class EmbeddingSettings(_Base):
    provider: Literal["openrouter", "ollama", "fastembed"] = "fastembed"
    # OpenRouter
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    openrouter_dimensions: int | None = 1536
    openrouter_batch_size: int = 32
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "nomic-embed-text"
    ollama_batch_size: int = 32
    # FastEmbed
    fastembed_model: str = "BAAI/bge-small-en-v1.5"
    fastembed_batch_size: int = 32


class LlmSettings(_Base):
    provider: Literal["openrouter", "ollama", "none"] = "none"
    # OpenRouter
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_temperature: float = 0.1
    openrouter_max_tokens: int = 2048
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_temperature: float = 0.1
    ollama_max_tokens: int = 2048


class RerankerSettings(_Base):
    provider: Literal["openrouter", "none"] = "openrouter"
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    chroma: ChromaSettings = ChromaSettings()
    ingestion: IngestionSettings = IngestionSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    llm: LlmSettings = LlmSettings()
    reranker: RerankerSettings = RerankerSettings()

    # Shared OpenRouter key (single secret for embeddings + LLM + reranker).
    # Read from the bare OPENROUTER_API_KEY env var (no prefix).
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

        # Canonical secrets from the bare process environment (never from .env).
        # Each provider sub-model falls back to this shared key when its own
        # EPA_KG__*-prefixed key is unset.
        bare_key = os.environ.get("OPENROUTER_API_KEY")
        if bare_key and self.openrouter_api_key is None:
            self.openrouter_api_key = bare_key
        if bare_key and self.embedding.openrouter_api_key is None:
            self.embedding.openrouter_api_key = bare_key
        if bare_key and self.llm.openrouter_api_key is None:
            self.llm.openrouter_api_key = bare_key
        if bare_key and self.reranker.openrouter_api_key is None:
            self.reranker.openrouter_api_key = bare_key

        bare_chroma = os.environ.get("CHROMADB_API_KEY")
        if bare_chroma and self.chroma.api_key is None:
            self.chroma.api_key = bare_chroma


settings = Settings()
