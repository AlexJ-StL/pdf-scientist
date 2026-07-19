# EPA Knowledge Graph - Metadata Extraction for EPA Methods

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_METHOD_NUMBER_PATTERNS = [
    (r"(\d{4}[A-Z]?)", False),
    (r"METHOD\s+(\d{3,4}(\.\d+)?[A-Z]?)", True),
]

_REVISION_PATTERN = r"REVISION\s+([A-Z])(?![A-Z])"
_DATE_PATTERN = r"(\d{4}[-/]\d{2}[-/]\d{2})"
_SUPERSEDES_PATTERN = r"SUPERSEDES\s+(METHOD\s+)?(\d{4}[A-Z]?)"
_MATRIX_KEYWORDS = ["water", "soil", "sediment", "waste", "air", "tissue", "sludge"]


def _extract_method_number(text: str, filename: str) -> str:
    """Extract EPA method number from filename or body text."""
    upper_filename = filename.upper()
    for pattern, _ in _METHOD_NUMBER_PATTERNS:
        match = re.search(pattern, upper_filename)
        if match:
            return match.group(1)
    for pattern, _ in _METHOD_NUMBER_PATTERNS:
        match = re.search(pattern, text.upper())
        if match:
            return match.group(1)
    return ""


def _extract_revision(text: str) -> str:
    """Extract revision letter from text."""
    match = re.search(_REVISION_PATTERN, text.upper())
    return match.group(1) if match else ""


def _extract_date(text: str) -> str:
    """Extract and normalize revision date from text."""
    match = re.search(_DATE_PATTERN, text)
    if not match:
        return ""
    raw = match.group(1)
    return raw.replace("/", "-")


def _extract_supersedes(text: str) -> str:
    """Extract superseded method number from text."""
    match = re.search(_SUPERSEDES_PATTERN, text.upper())
    return match.group(2) if match else ""


def _extract_matrix_keywords(text: str) -> list[str]:
    """Return EPA matrix keywords present in text."""
    lower_text = text.lower()
    return [kw for kw in _MATRIX_KEYWORDS if kw in lower_text]


def _extract_method_title(header_text: str, filename: str) -> str:
    """Extract the EPA method title from the document header / first page.

    EPA method PDFs place a block like:
        METHOD 0011
        SAMPLING FOR SELECTED ALDEHYDE AND KETONE EMISSIONS
        FROM STATIONARY SOURCES
    on the first page. The method number is captured separately; here we
    grab the lines following it as the title.
    """
    if not header_text:
        return ""

    # Normalize separators that can appear between a method number and its
    # title (soft hyphen, em/en dash) so they don't break word boundaries.
    for sep in ("\u00ad", "\u2014", "\u2013"):
        header_text = header_text.replace(sep, " ")
    lines = [ln.strip() for ln in header_text.splitlines()]

    # Find the "METHOD XXXX" marker. Accept decimal methods like "200.8"
    # and revision suffixes, and don't require it to start the line.
    method_re = re.compile(r"METHOD\s+(\d{3,4}(\.\d+)?[A-Z]?)", re.IGNORECASE)
    method_idx = -1
    for i, ln in enumerate(lines):
        if method_re.search(ln):
            method_idx = i
            break

    if method_idx == -1:
        # Fall back to filename-based title
        m = re.match(r"(\d{3,4}(?:[._]\w+)*)", filename.upper())
        return m.group(1) if m else ""

    # The title may be on the same line as "METHOD XXXX" (e.g.
    # "METHOD 25D DETERMINATION OF THE VOLATILE ORGANIC...") or on the
    # following lines. Strip the "METHOD XXXX" prefix from that line.
    first_line = lines[method_idx]
    inline = first_line[method_re.search(first_line).end() :].strip()
    inline = re.sub(r"^[\s\-–:]+", "", inline)
    # Truncate the inline portion at the first section heading on the line
    # (e.g. " 1.0 SCOPE ...") so we don't swallow the body text.
    inline = re.split(r"\s+\d+\.\d+(\.\d+)*\b", inline)[0].strip()
    title_parts: list[str] = [inline] if inline else []

    # Collect non-empty lines after the METHOD marker until we hit a stop
    # condition: a standalone/suffixed section number ("1.0", "1.0 SCOPE"),
    # a CD-ROM / Revision footer, another "METHOD X" line, or the start of
    # body prose (line begins lowercase or with boilerplate like "SW-846").
    stop_re = re.compile(
        r"^(\d+\.\d+(\.\d+)*\s?)|^CD-ROM|REVISION\s+\d|^METHOD\s+\d|^(sw-846|note:|this)",
        re.IGNORECASE,
    )
    for ln in lines[method_idx + 1 :]:
        if not ln:
            if title_parts:
                break
            continue
        if stop_re.match(ln):
            break
        title_parts.append(ln)

    title = " ".join(title_parts).strip()
    title = re.sub(r"\s+", " ", title)
    return title


def _build_fallback_metadata(
    text: str, filename: str, header_text: str = ""
) -> dict[str, Any]:
    """Build metadata dict from regex-based fallback extraction.

    Method number/title are drawn from ``header_text`` (first-page header) when
    available, falling back to the full ``text`` so extraction still works when
    no dedicated header was supplied.
    """
    number_source = header_text or text
    title_source = header_text or text
    return {
        "method_number": _extract_method_number(number_source, filename),
        "method_title": _extract_method_title(title_source, filename),
        "revision": _extract_revision(text),
        "revision_date": _extract_date(text),
        "supersedes": _extract_supersedes(text),
        "status": "",
        "matrix": _extract_matrix_keywords(text),
        "analytes": [],
        "references": [],
        "section_count": 0,
    }


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

    async def extract_metadata(
        self, text: str, filename: str, first_page_text: str = ""
    ) -> dict[str, Any]:
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
        return _build_fallback_metadata(text, filename)

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

    async def extract_metadata(
        self, text: str, filename: str, first_page_text: str = ""
    ) -> dict[str, Any]:
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
        return _build_fallback_metadata(text, filename)

    async def close(self):
        await self._client.aclose()


class HeuristicMetadataExtractor(MetadataExtractor):
    """Regex-based metadata extraction without an LLM."""

    async def extract_metadata(
        self, text: str, filename: str, first_page_text: str = ""
    ) -> dict[str, Any]:
        return _build_fallback_metadata(text, filename, header_text=first_page_text)

    async def close(self):
        pass


def get_metadata_extractor(settings) -> MetadataExtractor | None:
    """Factory function to get the configured metadata extractor."""

    provider = settings.llm.provider.lower()

    if provider == "openrouter":
        api_key = settings.llm.openrouter_api_key or settings.openrouter_api_key
        if not api_key:
            logger.warning("OpenRouter API key not set, metadata extraction disabled")
            return None
        return OpenRouterMetadataExtractor(
            api_key=api_key,
            model=settings.llm.openrouter_model,
            temperature=settings.llm.openrouter_temperature,
            max_tokens=settings.llm.openrouter_max_tokens,
        )

    elif provider == "ollama":
        return OllamaMetadataExtractor(
            host=settings.llm.ollama_host,
            model=settings.llm.ollama_model,
            temperature=settings.llm.ollama_temperature,
        )

    elif provider == "none":
        logger.info("No LLM provider configured, using heuristic metadata extraction")
        return HeuristicMetadataExtractor()

    else:
        logger.warning(f"Unknown LLM provider: {provider}")
        return None
