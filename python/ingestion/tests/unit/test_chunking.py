# EPA Knowledge Graph - Chunking Unit Tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.chunking import EPAMethodChunker


class TestEPAMethodChunker:
    """Tests for EPAMethodChunker."""

    def test_count_tokens_with_tiktoken(self):
        chunker = EPAMethodChunker()
        text = "This is a test sentence."
        tokens = chunker.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty(self):
        chunker = EPAMethodChunker()
        tokens = chunker.count_tokens("")
        assert tokens >= 0

    def test_extract_sections_from_text(self):
        chunker = EPAMethodChunker()
        text = """1.0 Scope and Application
This method covers the determination of...

1.1 Summary of Method
A sample is extracted...

2.0 Summary of Method
The method uses..."""

        sections = chunker.extract_sections_from_text(text)
        assert len(sections) >= 2
        assert sections[0]["number"] == "1.0"
        assert "Scope" in sections[0]["title"]

    def test_extract_sections_no_match(self):
        chunker = EPAMethodChunker()
        text = "This is just plain text without any section headers."
        sections = chunker.extract_sections_from_text(text)
        assert len(sections) == 0

    def test_recursive_splitting(self):
        chunker = EPAMethodChunker(chunk_size=100, chunk_overlap=20)
        long_text = " ".join(["This is a sentence."] * 50)
        chunks = chunker._split_text_recursive(long_text, "1.0", "Test Section", "test.pdf")
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.chunk_size * 1.5

    def test_chunk_by_sections_short_section(self):
        chunker = EPAMethodChunker(chunk_size=512, chunk_overlap=64)
        text = "This is a short section that fits in one chunk."
        sections = [{"number": "1.0", "title": "Short", "start": 0, "end": len(text)}]
        chunks = chunker.chunk_by_sections(text, sections, "test.pdf", {0: 0})
        assert len(chunks) == 1
        assert chunks[0].section == "1.0"
        assert chunks[0].section_title == "Short"

    def test_chunk_by_sections_long_section(self):
        chunker = EPAMethodChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["Word"] * 200)
        sections = [{"number": "1.0", "title": "Long", "start": 0, "end": len(text)}]
        chunks = chunker.chunk_by_sections(text, sections, "test.pdf", {0: 0})
        assert len(chunks) > 1

    def test_chunk_dataclass_fields(self):
        chunker = EPAMethodChunker()
        text = "Short text"
        sections = [{"number": "1.0", "title": "Test", "start": 0, "end": len(text)}]
        chunks = chunker.chunk_by_sections(text, sections, "test.pdf", {0: 0})
        chunk = chunks[0]
        assert isinstance(chunk.text, str)
        assert isinstance(chunk.section, str)
        assert isinstance(chunk.token_count, int)
        assert isinstance(chunk.metadata, dict)
        assert isinstance(chunk.page_start, int)
        assert isinstance(chunk.page_end, int)

    def test_extract_toc_returns_list(self):
        chunker = EPAMethodChunker()
        # This will return empty list since we don't have a real PDF
        # but we test the method signature and return type
        import fitz

        doc = fitz.open()
        toc = chunker.extract_toc(doc)
        assert isinstance(toc, list)
        doc.close()

    def test_find_section_in_text_exact(self):
        chunker = EPAMethodChunker()
        text = "1.0 Scope and Application\nThis is the content."
        pos = chunker._find_section_in_text(text, "1.0 Scope and Application")
        assert pos >= 0

    def test_find_section_in_text_case_insensitive(self):
        chunker = EPAMethodChunker()
        text = "1.0 scope and application\nThis is the content."
        pos = chunker._find_section_in_text(text, "1.0 Scope and Application")
        assert pos >= 0

    def test_find_section_in_text_not_found(self):
        chunker = EPAMethodChunker()
        text = "This is just regular text."
        pos = chunker._find_section_in_text(text, "Nonexistent Section")
        assert pos == -1
