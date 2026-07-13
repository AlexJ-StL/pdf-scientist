import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ingestion.metadata import (
    OpenRouterMetadataExtractor,
    OllamaMetadataExtractor,
    get_metadata_extractor,
)


class TestOpenRouterMetadataExtractor:
    @pytest.mark.asyncio
    async def test_extract_metadata_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "method_number": "8270E",
                                "method_title": "Test Method",
                                "revision": "E",
                            }
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        extractor = OpenRouterMetadataExtractor(api_key="secret")
        extractor._client = AsyncMock()
        extractor._client.post.return_value = mock_response

        result = await extractor.extract_metadata("Some text", "EPA8270E.pdf")
        assert result["method_number"] == "8270E"
        assert result["method_title"] == "Test Method"

    @pytest.mark.asyncio
    async def test_extract_metadata_fallback_on_json_error(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "not valid json"}}]
        }
        mock_response.raise_for_status = MagicMock()

        extractor = OpenRouterMetadataExtractor(api_key="secret")
        extractor._client = AsyncMock()
        extractor._client.post.return_value = mock_response

        result = await extractor.extract_metadata("METHOD 8270E", "EPA8270E.pdf")
        assert result["method_number"] == "8270E"

    @pytest.mark.asyncio
    async def test_extract_metadata_fallback_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
        mock_response.text = "bad request"
        extractor = OpenRouterMetadataExtractor(api_key="secret")
        extractor._client = AsyncMock()
        extractor._client.post.return_value = mock_response

        result = await extractor.extract_metadata("METHOD 8270E", "EPA8270E.pdf")
        assert result["method_number"] == "8270E"

    @pytest.mark.asyncio
    async def test_extract_metadata_fallback_on_generic_exception(self):
        extractor = OpenRouterMetadataExtractor(api_key="secret")
        extractor._client = AsyncMock()
        extractor._client.post.side_effect = RuntimeError("unexpected failure")

        result = await extractor.extract_metadata("METHOD 8270E", "EPA8270E.pdf")
        assert result["method_number"] == "8270E"

    @pytest.mark.asyncio
    async def test_close(self):
        extractor = OpenRouterMetadataExtractor(api_key="secret")
        extractor._client = AsyncMock()
        await extractor.close()
        extractor._client.aclose.assert_awaited_once()


class TestOllamaMetadataExtractor:
    @pytest.mark.asyncio
    async def test_extract_metadata_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps(
                {
                    "method_number": "8270E",
                    "method_title": "Test Method",
                }
            )
        }
        mock_response.raise_for_status = MagicMock()

        extractor = OllamaMetadataExtractor()
        extractor._client = AsyncMock()
        extractor._client.post.return_value = mock_response

        result = await extractor.extract_metadata("Some text", "EPA8270E.pdf")
        assert result["method_number"] == "8270E"

    @pytest.mark.asyncio
    async def test_extract_metadata_fallback_on_json_error(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "not valid json"}
        mock_response.raise_for_status = MagicMock()

        extractor = OllamaMetadataExtractor()
        extractor._client = AsyncMock()
        extractor._client.post.return_value = mock_response

        result = await extractor.extract_metadata("METHOD 6020B", "EPA6020B.pdf")
        assert result["method_number"] == "6020B"

    @pytest.mark.asyncio
    async def test_extract_metadata_fallback_on_generic_exception(self):
        extractor = OllamaMetadataExtractor()
        extractor._client = AsyncMock()
        extractor._client.post.side_effect = RuntimeError("unexpected failure")

        result = await extractor.extract_metadata("METHOD 6020B", "EPA6020B.pdf")
        assert result["method_number"] == "6020B"

    @pytest.mark.asyncio
    async def test_close(self):
        extractor = OllamaMetadataExtractor()
        extractor._client = AsyncMock()
        await extractor.close()
        extractor._client.aclose.assert_awaited_once()
