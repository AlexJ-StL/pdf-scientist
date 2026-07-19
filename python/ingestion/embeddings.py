# EPA Knowledge Graph - Embedding Providers

import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents."""
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return embedding dimensions."""
        pass


class FastEmbedProvider(EmbeddingProvider):
    """Local embeddings via fastembed (BGE, E5, etc.)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None
        self._dimensions = None

    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding

                logger.info(f"Loading fastembed model: {self.model_name}")
                self._model = TextEmbedding(model_name=self.model_name)
                # Get dimensions from a test embedding
                test_emb = list(self._model.embed(["test"]))[0]
                self._dimensions = len(test_emb)
                logger.info(f"Model loaded, dimensions: {self._dimensions}")
            except ImportError:
                logger.warning("fastembed not installed, falling back to character estimation")
                self._model = None
        return self._model

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed_documents([text])
        return embeddings[0] if embeddings else []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._get_model()

        if self._model is None:
            # Fallback: character-based estimation
            logger.warning("Using character-based embedding estimation")
            return [[0.0] * 384 for _ in texts]  # BGE-small dimensions

        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = list(self._model.embed(batch))
            all_embeddings.extend(embeddings)
        return all_embeddings

    def get_dimensions(self) -> int:
        if self._dimensions is None:
            self._get_model()
        return self._dimensions or 384


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """Remote embeddings via OpenRouter API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/text-embedding-3-small",
        dimensions: int | None = None,
        batch_size: int = 32,
    ):
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._dimensions = dimensions
        # Use httpx directly to avoid openai/httpx version conflicts
        self._client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/AlexJ-StL/epa-knowledge-graph",
                "X-Title": "EPA Knowledge Graph",
            },
            timeout=60.0,
        )

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed_documents([text])
        return embeddings[0] if embeddings else []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            payload = {
                "model": self.model,
                "input": batch,
            }
            if self.dimensions:
                payload["dimensions"] = self.dimensions

            try:
                response = await self._client.post("/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter embedding error: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"OpenRouter embedding failed: {e}")
                raise

        return all_embeddings

    def get_dimensions(self) -> int:
        if self._dimensions is None:
            model_dims = {
                "openai/text-embedding-3-small": 1536,
                "openai/text-embedding-3-large": 3072,
                "openai/text-embedding-ada-002": 1536,
                "mistral/mistral-embed": 1024,
                "nomic-ai/nomic-embed-text-v1.5": 768,
            }
            self._dimensions = model_dims.get(self.model, 1536)
        return self._dimensions

    async def close(self):
        await self._client.aclose()


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Local embeddings via Ollama (OpenAI-compatible /api/embeddings endpoint)."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        batch_size: int = 32,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self._dimensions = None
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed_documents([text])
        return embeddings[0] if embeddings else []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            # Ollama processes one at a time
            batch_embeddings = []
            for text in batch:
                try:
                    response = await self._client.post(
                        f"{self.host}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    batch_embeddings.append(data["embedding"])
                except httpx.HTTPStatusError as e:
                    logger.error(f"Ollama embedding error: {e.response.text}")
                    raise
                except Exception as e:
                    logger.error(f"Ollama embedding failed: {e}")
                    raise

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def get_dimensions(self) -> int:
        if self._dimensions is None:
            model_dims = {
                "nomic-embed-text": 768,
                "mxbai-embed-large": 1024,
                "all-minilm": 384,
                "bge-m3": 1024,
                "snowflake-arctic-embed": 768,
            }
            self._dimensions = model_dims.get(self.model, 768)
        return self._dimensions

    async def close(self):
        await self._client.aclose()


def get_embedding_provider(settings) -> EmbeddingProvider:
    """Factory function to get the configured embedding provider."""

    provider = settings.embedding.provider.lower()

    if provider == "fastembed":
        return FastEmbedProvider(
            model_name=settings.embedding.fastembed_model,
            batch_size=settings.embedding.fastembed_batch_size,
        )

    elif provider == "openrouter":
        api_key = settings.embedding.openrouter_api_key or settings.openrouter_api_key
        if not api_key:
            raise ValueError("OpenRouter API key required for openrouter embedding provider")
        return OpenRouterEmbeddingProvider(
            api_key=api_key,
            model=settings.embedding.openrouter_model,
            dimensions=settings.embedding.openrouter_dimensions,
            batch_size=settings.embedding.openrouter_batch_size,
        )

    elif provider == "ollama":
        return OllamaEmbeddingProvider(
            host=settings.embedding.ollama_host,
            model=settings.embedding.ollama_model,
            batch_size=settings.embedding.ollama_batch_size,
        )

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. Supported: fastembed, openrouter, ollama"
        )
