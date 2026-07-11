# EPA Knowledge Graph - Metadata Extraction for EPA Methods

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MethodMetadata(BaseModel):
    """Extracted metadata for an EPA method."""

    method_number: str = ""
    method_title: str = ""
    revision: str = ""
    revision_date: str = ""
    supersedes: str = ""
    status: str = ""  # Active, Withdrawn, etc.
    matrix: list[str] = []
    analytes: list[str] = []
    references: list[str] = []
    section_count: int = 0


class MetadataExtractor(ABC):
    """Abstract base for metadata extraction."""

    @abstractmethod
    async def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        """Extract metadata from document text."""
        pass


class OpenRouterMetadataExtractor(MetadataExtractor):
    """Extract metadata using OpenRouter LLM."""

    SYSTEM_PROMPT = """You are an expert at parsing EPA method documents. Extract structured metadata from the provided text.

Return ONLY valid JSON with these fields:
- method_number: EPA method number (e.g., "8270E", "6020B", "1664A")
- method_title: Full method title
- revision: Revision letter (e.g., "E", "B", "A")
- revision_date: Date in YYYY-MM-DD format if found
- supersedes: Previous method it supersedes (e.g., "8270D")
- status: "Active", "Withdrawn", "Draft", or ""
- matrix: List of matrices (e.g., ["water", "soil", "waste", "air"])
- analytes: List of target analytes/chemicals
- references: List of other methods/standards referenced
- section_count: Number of major sections

If a field is not found, use empty string or empty list. Be precise."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/AlexJ-StL/epa-knowledge-graph",
                "X-Title": "EPA Knowledge Graph",
            },
            timeout=120.0,
        )

    async def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        # Truncate text to first 8000 chars for metadata extraction
        sample_text = text[:8000]

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Filename: {filename}\n\nText:\n{sample_text}"},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            metadata = json.loads(content)
            logger.info(
                f"Extracted metadata for {filename}: method={metadata.get('method_number')}"
            )
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM metadata response: {e}")
            return self._fallback_extract(text, filename)
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter metadata error: {e.response.text}")
            return self._fallback_extract(text, filename)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return self._fallback_extract(text, filename)

    def _fallback_extract(self, text: str, filename: str) -> dict[str, Any]:
        """Regex-based fallback extraction."""
        import re

        metadata = {
            "method_number": "",
            "method_title": "",
            "revision": "",
            "revision_date": "",
            "supersedes": "",
            "status": "",
            "matrix": [],
            "analytes": [],
            "references": [],
            "section_count": 0,
        }

        # Extract method number from filename or text
        method_match = re.search(r"(\d{4}[A-Z]?)", filename.upper())
        if not method_match:
            method_match = re.search(r"METHOD\s+(\d{4}[A-Z]?)", text.upper())
        if method_match:
            metadata["method_number"] = method_match.group(1)

        # Extract revision
        rev_match = re.search(r"REVISION\s+([A-Z])", text.upper())
        if rev_match:
            metadata["revision"] = rev_match.group(1)

        # Extract date
        date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", text)
        if date_match:
            metadata["revision_date"] = date_match.group(1).replace("/", "-")

        # Extract supersedes
        super_match = re.search(r"SUPERSEDES\s+(METHOD\s+)?(\d{4}[A-Z]?)", text.upper())
        if super_match:
            metadata["supersedes"] = super_match.group(2)

        # Extract matrix keywords
        matrix_keywords = ["water", "soil", "sediment", "waste", "air", "tissue", "sludge"]
        for kw in matrix_keywords:
            if kw in text.lower():
                metadata["matrix"].append(kw)

        return metadata

    async def close(self):
        await self._client.aclose()


class OllamaMetadataExtractor(MetadataExtractor):
    """Extract metadata using local Ollama LLM."""

    SYSTEM_PROMPT = """You are an expert at parsing EPA method documents. Extract structured metadata from the provided text.

Return ONLY valid JSON with these fields:
- method_number: EPA method number (e.g., "8270E", "6020B", "1664A")
- method_title: Full method title
- revision: Revision letter (e.g., "E", "B", "A")
- revision_date: Date in YYYY-MM-DD format if found
- supersedes: Previous method it supersedes (e.g., "8270D")
- status: "Active", "Withdrawn", "Draft", or ""
- matrix: List of matrices (e.g., ["water", "soil", "waste", "air"])
- analytes: List of target analytes/chemicals
- references: List of other methods/standards referenced
- section_count: Number of major sections

If a field is not found, use empty string or empty list. Be precise."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        temperature: float = 0.1,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self._client = httpx.AsyncClient(timeout=180.0)

    async def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        sample_text = text[:8000]

        payload = {
            "model": self.model,
            "prompt": f"{self.SYSTEM_PROMPT}\n\nFilename: {filename}\n\nText:\n{sample_text}\n\nJSON:",
            "temperature": self.temperature,
            "format": "json",
            "stream": False,
        }

        try:
            response = await self._client.post(
                f"{self.host}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("response", "{}")

            metadata = json.loads(content)
            logger.info(
                f"Extracted metadata for {filename}: method={metadata.get('method_number')}"
            )
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama metadata response: {e}")
            return self._fallback_extract(text, filename)
        except Exception as e:
            logger.error(f"Ollama metadata extraction failed: {e}")
            return self._fallback_extract(text, filename)

    def _fallback_extract(self, text: str, filename: str) -> dict[str, Any]:
        """Same fallback as OpenRouter."""
        import re

        metadata = {
            "method_number": "",
            "method_title": "",
            "revision": "",
            "revision_date": "",
            "supersedes": "",
            "status": "",
            "matrix": [],
            "analytes": [],
            "references": [],
            "section_count": 0,
        }

        method_match = re.search(r"(\d{4}[A-Z]?)", filename.upper())
        if not method_match:
            method_match = re.search(r"METHOD\s+(\d{4}[A-Z]?)", text.upper())
        if method_match:
            metadata["method_number"] = method_match.group(1)

        rev_match = re.search(r"REVISION\s+([A-Z])", text.upper())
        if rev_match:
            metadata["revision"] = rev_match.group(1)

        date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", text)
        if date_match:
            metadata["revision_date"] = date_match.group(1).replace("/", "-")

        super_match = re.search(r"SUPERSEDES\s+(METHOD\s+)?(\d{4}[A-Z]?)", text.upper())
        if super_match:
            metadata["supersedes"] = super_match.group(2)

        matrix_keywords = ["water", "soil", "sediment", "waste", "air", "tissue", "sludge"]
        for kw in matrix_keywords:
            if kw in text.lower():
                metadata["matrix"].append(kw)

        return metadata

    async def close(self):
        await self._client.aclose()


def get_metadata_extractor(settings) -> MetadataExtractor | None:
    """Factory function to get the configured metadata extractor."""

    provider = settings.llm_provider.lower()

    if provider == "openrouter":
        api_key = settings.openrouter_llm_api_key or settings.openrouter_api_key
        if not api_key:
            logger.warning("OpenRouter API key not set, metadata extraction disabled")
            return None
        return OpenRouterMetadataExtractor(
            api_key=api_key,
            model=settings.openrouter_llm_model,
            temperature=settings.openrouter_llm_temperature,
            max_tokens=settings.openrouter_llm_max_tokens,
        )

    elif provider == "ollama":
        return OllamaMetadataExtractor(
            host=settings.ollama_llm_host,
            model=settings.ollama_llm_model,
            temperature=settings.ollama_llm_temperature,
        )

    elif provider == "none":
        logger.info("No LLM provider configured, metadata extraction disabled")
        return None

    else:
        logger.warning(f"Unknown LLM provider: {provider}")
        return None
