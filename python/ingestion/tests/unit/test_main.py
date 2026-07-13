from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ingestion.main import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    Source,
    app,
    sanitize_metadata,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestSanitizeMetadata:
    def test_removes_none_values(self):
        assert sanitize_metadata({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}

    def test_passes_through_scalar_types(self):
        meta = {"str": "a", "int": 1, "float": 1.5, "bool": True}
        assert sanitize_metadata(meta) == meta

    def test_json_encodes_lists(self):
        assert sanitize_metadata({"items": [1, 2, 3]}) == {"items": "[1, 2, 3]"}

    def test_json_encodes_dicts(self):
        assert sanitize_metadata({"nested": {"a": 1}}) == {"nested": '{"a": 1}'}

    def test_stringifies_other_types(self):
        result = sanitize_metadata({"path": Path("/tmp/x")})
        assert result["path"] == str(Path("/tmp/x"))


class TestRequestResponseModels:
    def test_ingest_request_defaults(self):
        req = IngestRequest()
        assert req.collection == "epa_methods"
        assert req.force_reindex is False
        assert req.pdf_dir is None

    def test_ingest_response(self):
        resp = IngestResponse(
            status="completed",
            documents_processed=2,
            chunks_created=5,
            time_ms=123,
            errors=[],
        )
        assert resp.status == "completed"
        assert resp.time_ms == 123

    def test_query_request_defaults(self):
        req = QueryRequest(question="test")
        assert req.top_k == 5
        assert req.collection == "epa_methods"
        assert req.embedding_provider is None

    def test_query_response_with_sources(self):
        source = Source(
            method="8270E",
            section="1.0",
            chunk_index=0,
            text="sample text",
            score=0.9,
            metadata={},
        )
        resp = QueryResponse(answer="ok", sources=[source], query_time_ms=10)
        assert len(resp.sources) == 1
        assert resp.sources[0].method == "8270E"

    def test_health_response(self):
        data = {
            "status": "ok",
            "chroma_connected": True,
            "embedding_provider": "fastembed",
            "llm_provider": "openrouter",
        }
        assert data["chroma_connected"] is True


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "chroma_connected" in body

    def test_health_when_uninitialized(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"


class TestIngestEndpoint:
    def test_ingest_missing_pdf_dir(self, client):
        response = client.post("/ingest", json={"pdf_dir": "/nonexistent"})
        assert response.status_code == 400

    def test_ingest_no_pdfs(self, client, tmp_path):
        response = client.post("/ingest", json={"pdf_dir": str(tmp_path)})
        assert response.status_code == 400
        assert "No PDF files found" in response.json()["detail"]

    def test_ingest_file_too_large(self, client, tmp_path):
        pdf = tmp_path / "big.pdf"
        pdf.write_bytes(b"%PDF-1.4\n" + b"x" * (200 * 1024 * 1024))
        response = client.post("/ingest", json={"pdf_dir": str(tmp_path)})
        assert response.status_code == 200
        body = response.json()
        assert len(body["errors"]) > 0
        assert "File too large" in body["errors"][0]

    def test_ingest_default_collection(self, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        response = client.post("/ingest", json={"pdf_dir": str(tmp_path)})
        assert response.status_code == 200
        body = response.json()
        assert "documents_processed" in body
        assert "chunks_created" in body


class TestQueryEndpoint:
    def test_query_before_initialization(self, client):
        response = client.post("/query", json={"question": "test"})
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

    def test_query_request_deserializes(self):
        req = QueryRequest(question="test", top_k=3)
        assert req.top_k == 3
        assert req.collection == "epa_methods"

    def test_query_request_with_overrides(self):
        req = QueryRequest(
            question="test",
            collection="custom",
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
        )
        assert req.embedding_provider == "ollama"
        assert req.collection == "custom"
