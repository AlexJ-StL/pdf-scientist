from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from ingestion.main import (
    IngestRequest,
    app,
    lifespan,
    process_pdf,
    query_knowledge_graph,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestLifespan:
    @pytest.mark.asyncio
    async def test_startup_initializes_components(self):
        mock_chroma = AsyncMock()
        mock_chroma.is_healthy.return_value = True
        mock_embed = MagicMock()
        mock_meta = MagicMock()
        mock_chunker = MagicMock()

        with patch("ingestion.main.ChromaManager", return_value=mock_chroma), patch(
            "ingestion.main.get_embedding_provider", return_value=mock_embed
        ), patch("ingestion.main.get_metadata_extractor", return_value=mock_meta), patch(
            "ingestion.main.EPAMethodChunker", return_value=mock_chunker
        ), patch("ingestion.main.chroma_manager", None), patch(
            "ingestion.main.embedding_provider", None
        ), patch("ingestion.main.metadata_extractor", None), patch(
            "ingestion.main.chunker", None
        ):
            async with lifespan(app):
                import ingestion.main as main_module

                assert main_module.chroma_manager is mock_chroma
                assert main_module.embedding_provider is mock_embed
                assert main_module.metadata_extractor is mock_meta
                assert main_module.chunker is mock_chunker

    @pytest.mark.asyncio
    async def test_shutdown_closes_chroma(self):
        mock_chroma = AsyncMock()
        mock_chroma.is_healthy.return_value = True
        mock_embed = MagicMock()
        mock_meta = MagicMock()
        mock_chunker = MagicMock()

        with patch("ingestion.main.ChromaManager", return_value=mock_chroma), patch(
            "ingestion.main.get_embedding_provider", return_value=mock_embed
        ), patch("ingestion.main.get_metadata_extractor", return_value=mock_meta), patch(
            "ingestion.main.EPAMethodChunker", return_value=mock_chunker
        ):
            async with lifespan(app):
                pass
            mock_chroma.close.assert_awaited_once()


class TestProcessPdf:
    @pytest.mark.asyncio
    async def test_no_chunks_returns_zero(self):
        mock_chunker = MagicMock()
        mock_chunker.chunk_pdf.return_value = []

        result = await process_pdf(
            pdf_file=MagicMock(name="test.pdf"),
            collection="epa_methods",
            chunker=mock_chunker,
            embedding_provider=MagicMock(),
            metadata_extractor=None,
            chroma_manager=MagicMock(),
        )
        assert result["chunks_created"] == 0

    @pytest.mark.asyncio
    async def test_process_pdf_stores_chunks(self):
        mock_chunker = MagicMock()
        mock_chunker.chunk_pdf.return_value = [
            {
                "text": "chunk text",
                "section": "1.0",
                "section_title": "Scope",
                "token_count": 10,
                "metadata": {},
                "page_start": 0,
                "page_end": 1,
            }
        ]

        mock_meta = MagicMock()
        mock_meta.extract_metadata = AsyncMock(return_value={"method_number": "8270E"})

        mock_embed = MagicMock()
        mock_embed.embed_documents = AsyncMock(return_value=[[0.1] * 384])

        mock_chroma = MagicMock()
        mock_chroma.get = AsyncMock(return_value=None)
        mock_chroma.upsert = AsyncMock()

        result = await process_pdf(
            pdf_file=MagicMock(name="EPA8270E.pdf"),
            collection="epa_methods",
            chunker=mock_chunker,
            embedding_provider=mock_embed,
            metadata_extractor=mock_meta,
            chroma_manager=mock_chroma,
            force_reindex=True,
        )

        assert result["chunks_created"] == 1
        mock_chroma.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_existing_chunks_when_not_force_reindex(self):
        mock_chunker = MagicMock()
        mock_chunker.chunk_pdf.return_value = [
            {
                "text": "chunk text",
                "section": "1.0",
                "section_title": "Scope",
                "token_count": 10,
                "metadata": {},
                "page_start": 0,
                "page_end": 1,
            }
        ]

        mock_meta = MagicMock()
        mock_meta.extract_metadata = AsyncMock(return_value={"method_number": "8270E"})

        mock_embed = MagicMock()
        mock_embed.embed_documents = AsyncMock(return_value=[[0.1] * 384])

        mock_chroma = MagicMock()
        mock_chroma.get = AsyncMock(return_value={"ids": ["existing"]})
        mock_chroma.upsert = AsyncMock()

        result = await process_pdf(
            pdf_file=MagicMock(name="EPA8270E.pdf"),
            collection="epa_methods",
            chunker=mock_chunker,
            embedding_provider=mock_embed,
            metadata_extractor=mock_meta,
            chroma_manager=mock_chroma,
            force_reindex=False,
        )

        assert result["chunks_created"] == 0
        mock_chroma.upsert.assert_not_awaited()


class TestQueryEndpoint:
    @pytest.mark.asyncio
    async def test_query_returns_answer(self, client, monkeypatch):
        mock_chroma = MagicMock()
        mock_chroma.is_healthy.return_value = True

        mock_embed = MagicMock()
        mock_embed.embed_query = AsyncMock(return_value=[0.1] * 384)

        mock_chroma.query = AsyncMock(
            return_value={
                "documents": [["doc text"]],
                "metadatas": [[{"method_number": "8270E", "section": "1.0", "chunk_index": 0}]],
                "distances": [[0.5]],
                "ids": [["id1"]],
            }
        )

        import ingestion.main as main_module

        monkeypatch.setattr(main_module, "chroma_manager", mock_chroma, raising=False)
        monkeypatch.setattr(main_module, "embedding_provider", mock_embed, raising=False)

        response = client.post("/query", json={"question": "test query", "top_k": 1})
        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert len(body["sources"]) == 1
        assert body["sources"][0]["method"] == "8270E"
