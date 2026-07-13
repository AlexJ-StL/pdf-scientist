from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ingestion.embeddings import (
    FastEmbedProvider,
    OpenRouterEmbeddingProvider,
    OllamaEmbeddingProvider,
    get_embedding_provider,
)


class TestFastEmbedWithModel:
    @pytest.mark.asyncio
    async def test_embed_documents_with_model(self):
        mock_model = MagicMock()
        mock_model.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        provider = FastEmbedProvider()
        provider._model = mock_model
        provider._dimensions = 2

        result = await provider.embed_documents(["text1", "text2"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_get_dimensions_after_model_load(self):
        provider = FastEmbedProvider()
        provider._model = MagicMock()
        provider._dimensions = 768
        assert provider.get_dimensions() == 768


class TestOpenRouterEmbedding:
    @pytest.mark.asyncio
    async def test_embed_documents_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]
        }
        mock_response.raise_for_status = MagicMock()

        provider = OpenRouterEmbeddingProvider(api_key="secret")
        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        result = await provider.embed_documents(["text1", "text2"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @pytest.mark.asyncio
    async def test_embed_documents_with_dimensions_payload(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1] * 512}]}
        mock_response.raise_for_status = MagicMock()

        provider = OpenRouterEmbeddingProvider(api_key="secret", dimensions=512)
        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        result = await provider.embed_documents(["text"])
        assert result == [[0.1] * 512]
        provider._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_embed_documents_http_error(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
        mock_response.text = "rate limited"
        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await provider.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_close(self):
        provider = OpenRouterEmbeddingProvider(api_key="secret")
        provider._client = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_awaited_once()


class TestOllamaEmbedding:
    @pytest.mark.asyncio
    async def test_embed_documents_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2]}
        mock_response.raise_for_status = MagicMock()

        provider = OllamaEmbeddingProvider()
        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        result = await provider.embed_documents(["text"])
        assert result == [[0.1, 0.2]]

    @pytest.mark.asyncio
    async def test_embed_documents_http_error(self):
        provider = OllamaEmbeddingProvider()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
        mock_response.text = "server error"
        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await provider.embed_documents(["text"])

    @pytest.mark.asyncio
    async def test_close(self):
        provider = OllamaEmbeddingProvider()
        provider._client = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_awaited_once()
