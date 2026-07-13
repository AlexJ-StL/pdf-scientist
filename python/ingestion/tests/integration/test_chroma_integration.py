import pytest

from ingestion.chroma_client import ChromaManager


@pytest.mark.integration
class TestChromaIntegration:
    @pytest.mark.asyncio
    async def test_embedded_chroma(self, tmp_path):
        manager = ChromaManager(
            persist_dir=tmp_path / "chroma",
            collection_name="test_collection",
        )
        await manager.initialize()

        assert manager.is_healthy()

        await manager.upsert(
            collection_name="test_collection",
            documents=["test document 1", "test document 2"],
            metadatas=[{"source": "test1"}, {"source": "test2"}],
            ids=["id1", "id2"],
            embeddings=[[0.1] * 384, [0.2] * 384],
        )

        count = await manager.count("test_collection")
        assert count == 2

        results = await manager.query(
            collection_name="test_collection",
            query_embedding=[0.15] * 384,
            n_results=2,
        )

        assert "documents" in results
        assert len(results["documents"][0]) == 2
