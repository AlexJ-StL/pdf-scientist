from ingestion.metadata import (
    HeuristicMetadataExtractor,
    MethodMetadata,
    OllamaMetadataExtractor,
    OpenRouterMetadataExtractor,
    _build_fallback_metadata,
    _extract_date,
    _extract_matrix_keywords,
    _extract_method_number,
    _extract_revision,
    _extract_supersedes,
    get_metadata_extractor,
)


class TestMethodMetadata:
    def test_default_values(self):
        meta = MethodMetadata()
        assert meta.method_number == ""
        assert meta.matrix == []
        assert meta.analytes == []

    def test_valid_metadata(self):
        meta = MethodMetadata(
            method_number="8270E",
            method_title="Test Method",
            matrix=["water", "soil"],
        )
        assert meta.method_number == "8270E"
        assert len(meta.matrix) == 2


class TestFallbackExtract:
    def test_extracts_method_number_from_filename(self):
        text = "Some EPA method content."
        filename = "EPA8270E.pdf"
        extractor = OpenRouterMetadataExtractor(api_key="secret")
        result = extractor._fallback_extract(text, filename)
        assert result["method_number"] == "8270E"

    def test_extracts_method_number_from_text(self):
        text = "METHOD 6020B revision information here."
        filename = "unknown.pdf"
        extractor = OpenRouterMetadataExtractor(api_key="secret")
        result = extractor._fallback_extract(text, filename)
        assert result["method_number"] == "6020B"

    def test_extracts_revision(self):
        text = "REVISION E of this method."
        result = OpenRouterMetadataExtractor(api_key="secret")._fallback_extract(text, "x.pdf")
        assert result["revision"] == "E"

    def test_extracts_date(self):
        text = "Issued on 2024-01-15 and revised 2023/06/30."
        result = OpenRouterMetadataExtractor(api_key="secret")._fallback_extract(text, "x.pdf")
        assert result["revision_date"] == "2024-01-15"

    def test_extracts_supersedes(self):
        text = "This method supersedes METHOD 8270D."
        result = OpenRouterMetadataExtractor(api_key="secret")._fallback_extract(text, "x.pdf")
        assert result["supersedes"] == "8270D"

    def test_extracts_supersedes_without_method_keyword(self):
        text = "This method supersedes 8270D."
        result = OpenRouterMetadataExtractor(api_key="secret")._fallback_extract(text, "x.pdf")
        assert result["supersedes"] == "8270D"

    def test_returns_empty_on_no_match(self):
        text = "No method metadata here."
        result = OpenRouterMetadataExtractor(api_key="secret")._fallback_extract(text, "x.pdf")
        assert result["method_number"] == ""
        assert result["matrix"] == []


class TestFallbackHelpers:
    def test_extract_method_number_from_filename(self):
        assert _extract_method_number("content", "EPA8270E.pdf") == "8270E"

    def test_extract_method_number_from_text(self):
        assert _extract_method_number("METHOD 6020B here", "unknown.pdf") == "6020B"

    def test_extract_method_number_filename_takes_precedence(self):
        assert _extract_method_number("METHOD 6020B here", "EPA8270E.pdf") == "8270E"

    def test_extract_method_number_returns_empty_string_when_missing(self):
        assert _extract_method_number("no method here", "unknown.pdf") == ""

    def test_extract_revision(self):
        assert _extract_revision("REVISION E of this method.") == "E"

    def test_extract_revision_returns_empty_when_missing(self):
        assert _extract_revision("No revision info.") == ""

    def test_extract_date_normalizes_slashes(self):
        assert _extract_date("Issued on 2024/01/15.") == "2024-01-15"

    def test_extract_date_returns_empty_when_missing(self):
        assert _extract_date("No date here.") == ""

    def test_extract_supersedes(self):
        assert _extract_supersedes("This method supersedes METHOD 8270D.") == "8270D"

    def test_extract_supersedes_without_method_keyword(self):
        assert _extract_supersedes("This method supersedes 8270D.") == "8270D"

    def test_extract_supersedes_returns_empty_when_missing(self):
        assert _extract_supersedes("No supersedes info.") == ""

    def test_extract_matrix_keywords_matches_known_keywords(self):
        text = "Applicable to water, soil, and waste matrices."
        keywords = _extract_matrix_keywords(text)
        assert "water" in keywords
        assert "soil" in keywords
        assert "waste" in keywords

    def test_extract_matrix_keywords_case_insensitive(self):
        text = "WATER and SOIL samples."
        keywords = _extract_matrix_keywords(text)
        assert "water" in keywords
        assert "soil" in keywords

    def test_extract_matrix_keywords_returns_empty_when_no_match(self):
        assert _extract_matrix_keywords("No matrix keywords here.") == []

    def test_build_fallback_metadata_assembles_all_fields(self):
        text = "METHOD 8270E REVISION E supersedes 8270D. 2024-01-15 water soil"
        result = _build_fallback_metadata(text, "EPA8270E.pdf")
        assert result["method_number"] == "8270E"
        assert result["revision"] == "E"
        assert result["revision_date"] == "2024-01-15"
        assert result["supersedes"] == "8270D"
        assert "water" in result["matrix"]
        assert "soil" in result["matrix"]


class TestGetMetadataExtractor:
    def test_openrouter_factory(self, monkeypatch):
        from ingestion.config import Settings

        monkeypatch.setenv("EPA_KG__LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("EPA_KG__OPENROUTER_API_KEY", "secret")
        monkeypatch.setenv("EPA_KG__OPENROUTER_LLM_MODEL", "claude-3.5-sonnet")

        settings = Settings()
        extractor = get_metadata_extractor(settings)
        assert isinstance(extractor, OpenRouterMetadataExtractor)

    def test_ollama_factory(self, monkeypatch):
        from ingestion.config import Settings

        monkeypatch.setenv("EPA_KG__LLM_PROVIDER", "ollama")
        settings = Settings()

        extractor = get_metadata_extractor(settings)
        assert isinstance(extractor, OllamaMetadataExtractor)

    def test_none_returns_heuristic(self, monkeypatch):
        from ingestion.config import Settings

        monkeypatch.setenv("EPA_KG__LLM_PROVIDER", "none")
        settings = Settings()

        extractor = get_metadata_extractor(settings)
        assert isinstance(extractor, HeuristicMetadataExtractor)

    def test_unknown_returns_none(self):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.llm_provider = "unknown"

        extractor = get_metadata_extractor(settings)
        assert extractor is None

    def test_openrouter_missing_api_key_returns_none(self, monkeypatch):
        from ingestion.config import Settings

        for key in [
            "EPA_KG__OPENROUTER_API_KEY",
            "EPA_KG__OPENROUTER_LLM_API_KEY",
            "EPA_KG__OPENROUTER_EMBEDDING_API_KEY",
            "OPENROUTER_API_KEY",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = Settings(_env_file=None)
        settings.llm_provider = "openrouter"

        extractor = get_metadata_extractor(settings)
        assert extractor is None
