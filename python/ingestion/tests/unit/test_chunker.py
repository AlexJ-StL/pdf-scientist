import sys
from unittest.mock import patch

from ingestion.chunking import Chunk, EPAMethodChunker


class TestChunkerDefaults:
    def test_defaults(self):
        chunker = EPAMethodChunker()
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 64
        assert chunker.toc_aware is True

    def test_custom_settings(self):
        chunker = EPAMethodChunker(chunk_size=256, chunk_overlap=32, toc_aware=False)
        assert chunker.chunk_size == 256
        assert chunker.chunk_overlap == 32
        assert chunker.toc_aware is False


class TestTokenCounting:
    def test_token_counting_positive(self):
        chunker = EPAMethodChunker()
        text = "This is a test sentence."
        tokens = chunker.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_empty_text_returns_one(self):
        chunker = EPAMethodChunker()
        assert chunker.count_tokens("") == 1

    def test_long_text_estimation(self):
        chunker = EPAMethodChunker()
        text = "word " * 1000
        tokens = chunker.count_tokens(text)
        assert tokens > 0

    def test_fallback_when_tiktoken_missing(self, monkeypatch):
        monkeypatch.setattr("ingestion.chunking.TIKTOKEN_AVAILABLE", False)
        chunker = EPAMethodChunker()
        assert chunker.encoding is None
        assert chunker.count_tokens("hello world") == max(1, len("hello world") // 4)

    def test_fallback_when_get_encoding_raises(self):
        with patch.dict(sys.modules, {"tiktoken": None}):
            chunker = EPAMethodChunker()
            assert chunker.encoding is None
            assert chunker.count_tokens("abc") == max(1, 3 // 4)


class TestSectionExtraction:
    def test_section_extraction(self):
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

    def test_no_sections_returns_empty(self):
        chunker = EPAMethodChunker()
        sections = chunker.extract_sections_from_text("No sections here.")
        assert sections == []

    def test_fallback_heading_pattern(self):
        chunker = EPAMethodChunker()
        text = "1.1 Introduction\nSome text\n2.0 Methods\nMore text"
        sections = chunker.extract_sections_from_text(text)
        assert len(sections) >= 1

    def test_section_end_positions(self):
        chunker = EPAMethodChunker()
        text = "1.0 First\nbody\n2.0 Second\nbody"
        sections = chunker.extract_sections_from_text(text)
        for i, sec in enumerate(sections):
            if i + 1 < len(sections):
                assert "end" in sec
                assert sec["end"] == sections[i + 1]["start"]
            else:
                assert sec["end"] == len(text)


class TestRecursiveSplitting:
    def test_recursive_splitting(self):
        chunker = EPAMethodChunker(chunk_size=100, chunk_overlap=20)
        long_text = " ".join(["This is a sentence."] * 50)

        chunks = chunker._split_text_recursive(long_text, "1.0", "Test Section", "test.pdf")

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.chunk_size * 1.5
            assert chunk.section == "1.0"
            assert chunk.section_title == "Test Section"

    def test_split_respects_overlap(self):
        chunker = EPAMethodChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["word"] * 200)
        chunks = chunker._split_text_recursive(text, "1.0", "Test", "x.pdf")
        assert len(chunks) > 1


class TestTocExtraction:
    def test_extract_toc_empty(self):
        chunker = EPAMethodChunker()
        import fitz

        doc = fitz.open()
        toc = chunker.extract_toc(doc)
        assert toc == []
        doc.close()

    def test_extract_toc_converts_pages(self):
        chunker = EPAMethodChunker()
        import fitz

        doc = fitz.open()
        doc.new_page()
        doc.set_toc([(1, "Introduction", 1), (2, "Methods", 1)])
        toc = chunker.extract_toc(doc)
        assert toc[0]["title"] == "Introduction"
        assert toc[0]["page"] == 0
        doc.close()


class TestFindSection:
    def test_exact_match(self):
        chunker = EPAMethodChunker()
        text = "Scope and Application\n1.0 Scope\nDetails"
        pos = chunker._find_section_in_text(text, "Scope and Application")
        assert pos == 0

    def test_case_insensitive_match(self):
        chunker = EPAMethodChunker()
        text = "scope and application\nDetails"
        pos = chunker._find_section_in_text(text, "Scope and Application")
        assert pos == 0

    def test_short_title_fallback(self):
        chunker = EPAMethodChunker()
        text = "Some text here without the full title"
        pos = chunker._find_section_in_text(text, "Very Long Title That Is Cut")
        assert pos == -1


class TestBuildSections:
    def test_uses_toc_when_provided(self):
        chunker = EPAMethodChunker(toc_aware=True)
        text = "Introduction\n1.0 Scope\n2.0 Methods"
        toc = [{"level": 1, "title": "Scope", "page": 1}]
        sections = chunker._build_sections(text, toc)
        assert len(sections) == 1
        assert sections[0]["title"] == "Scope"
        assert sections[0]["number"] == "1.0"

    def test_falls_back_to_regex_when_no_toc(self):
        chunker = EPAMethodChunker()
        text = "1.0 Scope\n2.0 Methods"
        sections = chunker._build_sections(text, [])
        assert len(sections) >= 1
        assert sections[0]["number"] == "1.0"

    def test_returns_full_document_when_no_sections_found(self):
        chunker = EPAMethodChunker()
        text = "No sections here."
        sections = chunker._build_sections(text, [])
        assert len(sections) == 1
        assert sections[0]["title"] == "Full Document"
        assert sections[0]["start"] == 0
        assert sections[0]["end"] == len(text)


class TestConvertChunksToDicts:
    def test_converts_chunk_dataclasses(self):
        chunker = EPAMethodChunker()
        chunks = [
            Chunk(
                text="hello",
                section="1.0",
                section_title="Scope",
                token_count=5,
                metadata={"src": "a"},
                page_start=0,
                page_end=1,
            )
        ]
        result = chunker._convert_chunks_to_dicts(chunks, "test.pdf")
        assert result[0]["text"] == "hello"
        assert result[0]["section"] == "1.0"
        assert result[0]["page_start"] == 0
