# EPA Knowledge Graph - Python Ingestion Service Unit Tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_host(self):
        assert Settings().host == "127.0.0.1"

    def test_default_port(self):
        assert Settings().port == 8001

    def test_default_chroma_collection(self):
        assert Settings().chroma_collection == "epa_methods"

    def test_default_chunk_size(self):
        assert Settings().chunk_size == 512

    def test_default_chunk_overlap(self):
        assert Settings().chunk_overlap == 64

    def test_default_toc_aware(self):
        assert Settings().toc_aware is True

    def test_default_embedding_provider(self):
        assert Settings().embedding_provider == "fastembed"

    def test_default_llm_provider(self):
        assert Settings().llm_provider == "none"

    def test_default_max_file_size_mb(self):
        assert Settings().max_file_size_mb == 100

    def test_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("EPA_KG__HOST", "0.0.0.0")
        monkeypatch.setenv("EPA_KG__PORT", "9090")
        monkeypatch.setenv("EPA_KG__CHROMA_COLLECTION", "test_collection")
        monkeypatch.setenv("EPA_KG__CHUNK_SIZE", "256")
        monkeypatch.setenv("EPA_KG__LLM_PROVIDER", "none")
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9090
        assert settings.chroma_collection == "test_collection"
        assert settings.chunk_size == 256
        assert settings.llm_provider == "none"

    def test_settings_optional_fields_default_none(self):
        settings = Settings()
        assert settings.chroma_api_key is None
        assert settings.chroma_tenant is None
        assert settings.chroma_database is None
        assert settings.openrouter_embedding_api_key is None
        assert settings.openrouter_embedding_dimensions == 1536
