# EPA Knowledge Graph - Python Ingestion Service Unit Tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_host(self):
        assert Settings().app.host == "127.0.0.1"

    def test_default_port(self):
        assert Settings().app.port == 8001

    def test_default_chroma_collection(self):
        assert Settings().chroma.collection == "epa_methods"

    def test_default_chunk_size(self):
        assert Settings().ingestion.chunk_size == 512

    def test_default_chunk_overlap(self):
        assert Settings().ingestion.chunk_overlap == 64

    def test_default_toc_aware(self):
        assert Settings().ingestion.toc_aware is True

    def test_default_embedding_provider(self):
        assert Settings().embedding.provider == "fastembed"

    def test_default_llm_provider(self):
        assert Settings().llm.provider == "none"

    def test_default_max_file_size_mb(self):
        assert Settings().ingestion.max_file_size_mb == 100

    def test_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("EPA_KG__APP__HOST", "0.0.0.0")
        monkeypatch.setenv("EPA_KG__APP__PORT", "9090")
        monkeypatch.setenv("EPA_KG__CHROMA__COLLECTION", "test_collection")
        monkeypatch.setenv("EPA_KG__INGESTION__CHUNK_SIZE", "256")
        monkeypatch.setenv("EPA_KG__LLM__PROVIDER", "none")
        settings = Settings()
        assert settings.app.host == "0.0.0.0"
        assert settings.app.port == 9090
        assert settings.chroma.collection == "test_collection"
        assert settings.ingestion.chunk_size == 256
        assert settings.llm.provider == "none"

    def test_settings_optional_fields_default_none(self, monkeypatch):
        # Make the test hermetic: clear any ambient secret env vars so defaults
        # (None) are observable regardless of the local shell/CI environment.
        for var in ("OPENROUTER_API_KEY", "CHROMADB_API_KEY",
                    "EPA_KG__OPENROUTER_API_KEY", "EPA_KG__CHROMA__API_KEY"):
            monkeypatch.delenv(var, raising=False)
        settings = Settings()
        assert settings.chroma.api_key is None
        assert settings.chroma.tenant is None
        assert settings.chroma.database is None
        assert settings.embedding.openrouter_api_key is None
        assert settings.embedding.openrouter_dimensions == 1536

    def test_canonical_secret_from_bare_env(self, monkeypatch):
        # OPENROUTER_API_KEY (no prefix) is the single canonical secret name and
        # is shared across embedding/llm/reranker sub-configs.
        monkeypatch.delenv("EPA_KG__OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-canonical")
        settings = Settings()
        assert settings.openrouter_api_key == "sk-test-canonical"
        assert settings.embedding.openrouter_api_key == "sk-test-canonical"
        assert settings.llm.openrouter_api_key == "sk-test-canonical"
