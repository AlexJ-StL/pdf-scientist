# EPA Knowledge Graph - PDF Chunking for EPA Methods

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Try to import tiktoken, fallback to character-based estimation
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using character-based token estimation")


@dataclass
class Chunk:
    text: str
    section: str
    section_title: str
    token_count: int
    metadata: dict[str, Any]
    page_start: int
    page_end: int


class EPAMethodChunker:
    """
    TOC-aware recursive chunker for EPA method PDFs.

    EPA methods have a standard structure with numbered sections (1.0, 1.1, 2.0, etc.)
    and a table of contents. This chunker preserves that structure.
    """

    # Approximate characters per token (for estimation without tiktoken)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        toc_aware: bool = True,
        encoding_name: str = "cl100k_base",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.toc_aware = toc_aware

        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.get_encoding(encoding_name)
            except Exception:
                self.encoding = None
        else:
            self.encoding = None

        # EPA method section pattern (e.g., "1.0", "1.1.1", "2.0", "A.1")
        self.section_pattern = re.compile(
            r"^\s*(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*|[IVX]+\.\d+)\s+(.+?)\s*$", re.MULTILINE
        )

        # Fallback: heading-like patterns
        self.heading_pattern = re.compile(r"^\s*(\d+\.\d+(?:\.\d+)?)\s+(.+?)\s*$", re.MULTILINE)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text (uses tiktoken if available, else character estimation)."""
        if self.encoding:
            return len(self.encoding.encode(text))
        # Rough estimation: ~4 chars per token for English text
        return max(1, len(text) // self.CHARS_PER_TOKEN)

    def extract_toc(self, doc: fitz.Document) -> list[dict[str, Any]]:
        """Extract table of contents from PDF."""
        toc = doc.get_toc()
        if not toc:
            return []

        result = []
        for level, title, page in toc:
            result.append(
                {
                    "level": level,
                    "title": title.strip(),
                    "page": page - 1,  # Convert to 0-indexed
                }
            )
        return result

    def extract_sections_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract sections from text using regex patterns."""
        sections = []

        # Try primary section pattern
        for match in self.section_pattern.finditer(text):
            section_num = match.group(1)
            section_title = match.group(2).strip()
            start_pos = match.start()

            sections.append(
                {
                    "number": section_num,
                    "title": section_title,
                    "start": start_pos,
                }
            )

        # If no sections found, try fallback
        if not sections:
            for match in self.heading_pattern.finditer(text):
                sections.append(
                    {
                        "number": match.group(1),
                        "title": match.group(2).strip(),
                        "start": match.start(),
                    }
                )

        # Add end positions
        for i, sec in enumerate(sections):
            if i + 1 < len(sections):
                sec["end"] = sections[i + 1]["start"]
            else:
                sec["end"] = len(text)

        return sections

    def chunk_by_sections(
        self,
        text: str,
        sections: list[dict[str, Any]],
        source_pdf: str,
        page_map: dict[int, int],
    ) -> list[Chunk]:
        """Chunk text by detected sections."""
        chunks = []

        for section in sections:
            section_text = text[section["start"] : section.get("end", len(text))]
            section_tokens = self.count_tokens(section_text)

            if section_tokens <= self.chunk_size:
                # Section fits in one chunk
                chunks.append(
                    Chunk(
                        text=section_text.strip(),
                        section=section["number"],
                        section_title=section["title"],
                        token_count=section_tokens,
                        metadata={"source_pdf": source_pdf},
                        page_start=page_map.get(section["start"], 0),
                        page_end=page_map.get(section.get("end", len(text)), 0),
                    )
                )
            else:
                # Section too large, split recursively
                sub_chunks = self._split_text_recursive(
                    section_text,
                    section["number"],
                    section["title"],
                    source_pdf,
                )
                chunks.extend(sub_chunks)

        return chunks

    def _split_text_recursive(
        self,
        text: str,
        section_num: str,
        section_title: str,
        source_pdf: str,
    ) -> list[Chunk]:
        """Recursively split text into chunks with overlap."""
        chunks = []
        start = 0

        # Character estimates for chunk boundaries
        chunk_chars = self.chunk_size * self.CHARS_PER_TOKEN
        overlap_chars = self.chunk_overlap * self.CHARS_PER_TOKEN

        while start < len(text):
            end = start + chunk_chars

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                for punct in [". ", ".\n", "? ", "!\n"]:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct > start + chunk_chars // 2:
                        end = last_punct + len(punct)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                token_count = self.count_tokens(chunk_text)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        section=section_num,
                        section_title=section_title,
                        token_count=token_count,
                        metadata={"source_pdf": source_pdf, "split": True},
                        page_start=0,
                        page_end=0,
                    )
                )

            # Move start with overlap
            start = max(start + 1, end - overlap_chars)

        return chunks

    def chunk_pdf(self, pdf_path: Path) -> list[dict[str, Any]]:
        """
        Main entry point: chunk a PDF into structured chunks.
        Returns list of chunk dicts compatible with ChromaDB.
        """
        logger.info(f"Chunking {pdf_path.name}...")

        # Open with PyMuPDF for text + TOC
        doc = fitz.open(str(pdf_path))

        # Extract TOC
        toc = self.extract_toc(doc) if self.toc_aware else []

        # Extract full text with page mapping
        full_text = ""
        page_map = {}  # char_position -> page_number

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            page_start = len(full_text)
            full_text += page_text + "\n\n"
            page_map[page_start] = page_num

        doc.close()

        # Extract sections
        if toc:
            # Convert TOC to section format
            sections = []
            for i, entry in enumerate(toc):
                start_char = self._find_section_in_text(full_text, entry["title"])
                if start_char >= 0:
                    sections.append(
                        {
                            "number": f"{i+1}.0",
                            "title": entry["title"],
                            "start": start_char,
                            "page": entry["page"],
                        }
                    )

            # Add end positions
            for i, sec in enumerate(sections):
                if i + 1 < len(sections):
                    sec["end"] = sections[i + 1]["start"]
                else:
                    sec["end"] = len(full_text)
        else:
            # Fallback: regex-based section detection
            sections = self.extract_sections_from_text(full_text)

        if not sections:
            # Last resort: treat entire document as one section
            sections = [
                {
                    "number": "1.0",
                    "title": "Full Document",
                    "start": 0,
                    "end": len(full_text),
                }
            ]

        # Chunk by sections
        chunks = self.chunk_by_sections(full_text, sections, pdf_path.name, page_map)

        # Convert to dict format
        result = []
        for i, chunk in enumerate(chunks):
            result.append(
                {
                    "text": chunk.text,
                    "section": chunk.section,
                    "section_title": chunk.section_title,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                }
            )

        logger.info(f"Created {len(result)} chunks from {pdf_path.name}")
        return result

    def _find_section_in_text(self, text: str, section_title: str) -> int:
        """Find section title in text (fuzzy match)."""
        # Try exact match first
        pos = text.find(section_title)
        if pos >= 0:
            return pos

        # Try case-insensitive
        pos = text.lower().find(section_title.lower())
        if pos >= 0:
            return pos

        # Try first 50 chars of title
        short_title = section_title[:50]
        pos = text.lower().find(short_title.lower())
        return pos


# Convenience function
async def chunk_pdf(
    pdf_path: Path, chunk_size: int = 512, chunk_overlap: int = 64
) -> list[dict[str, Any]]:
    """Quick chunking function."""
    chunker = EPAMethodChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_pdf(pdf_path)
