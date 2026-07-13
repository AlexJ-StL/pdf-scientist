import sys

import pytest

from ingestion.embeddings import (
    FastEmbedProvider,
    OllamaEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    get_embedding_provider,
)


class TestFastEmbedProvider:
    def test_fallback_when_fastembed_missing(self, monkeypatch):
        monkeypatch.setattr("ingestion.embeddings.FastEmbedProvider._get_model", lambda self: None)
        provider = FastEmbedProvider()
        assert provider.get_dimensions() == 384

    @pytest.mark.asyncio
    async def test_embed_query_delegates_to_documents(self, monkeypatch):
        provider = FastEmbedProvider()
        provider._model = None
        provider._dimensions = 384

        async def fake_embed_documents(texts):
            return [[0.1, 0.2], [0.3, 0.4]]

        monkeypatch.setattr(provider, "embed_documents", fake_embed_documents)
        result = await provider.embed_query("hello")
        assert result == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_embed_documents_fallback(self, monkeypatch):
        provider = FastEmbedProvider()
        provider._model = None
        provider._dimensions = 384
        result = await provider.embed_documents(["a", "b"])
        assert len(result) == 2
        assert all(len(v) == 384 for v in result)
        assert all(v == [0.0] * 384 for v in result)

    def test_get_model_returns_none_when_fastembed_missing(self, monkeypatch):
        provider = FastEmbedProvider()
        monkeypatch.setitem(sys.modules, "fastembed", None)
        monkeypatch.delattr(sys.modules.get("fastembed", object), "TextEmbedding", raising=False)
        model = provider._get_model()
        assert model is None
        assert provider._dimensions is None

    def test_get_dimensions_triggers_model_load(self, monkeypatch):
        provider = FastEmbedProvider()
        monkeypatch.setattr(provider, "_get_model", lambda: None)
        assert provider.get_dimensions() == 384


class TestOpenRouterEmbeddingProvider:
    def test_default_dimensions(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret")
        assert provider.get_dimensions() == 1536

    def test_model_specific_dimensions(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret", model="mistral/mistral-embed")
        assert provider.get_dimensions() == 1024

    def test_custom_dimensions(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret", dimensions=512)
        assert provider.get_dimensions() == 512

    def test_client_headers(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret")
        assert provider._client.headers["Authorization"] == "Bearer secret"
        assert provider._client.headers["HTTP-Referer"].endswith("epa-knowledge-graph")


class TestOllamaEmbeddingProvider:
    def test_default_dimensions(self):
        provider = OllamaEmbeddingProvider()
        assert provider.get_dimensions() == 768

    def test_model_specific_dimensions(self):
        provider = OllamaEmbeddingProvider(model="bge-m3")
        assert provider.get_dimensions() == 1024

    def test_host_trailing_slash_stripped(self):
        provider = OllamaEmbeddingProvider(host="http://localhost:11434/")
        assert provider.host == "http://localhost:11434"


class TestGetEmbeddingProvider:
    def test_fastembed_factory(self, monkeypatch):
        from ingestion.config import Settings

        monkeypatch.setenv("EPA_KG__EMBEDDING_PROVIDER", "fastembed")
        monkeypatch.setenv("EPA_KG__FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        monkeypatch.setenv("EPA_KG__FASTEMBED_BATCH_SIZE", "32")

        settings = Settings()
        provider = get_embedding_provider(settings)
        assert isinstance(provider, FastEmbedProvider)

    def test_unknown_provider_raises(self):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.embedding_provider = "unknown"

        with pytest.raises(ValueError):
            get_embedding_provider(settings)
