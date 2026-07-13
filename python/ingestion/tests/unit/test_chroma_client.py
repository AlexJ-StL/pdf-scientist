from pathlib import Path

import pytest

from ingestion.chroma_client import ChromaManager, create_chroma_manager


class TestChromaManagerInitialization:
    def test_defaults(self):
        manager = ChromaManager()
        assert manager.host == "127.0.0.1"
        assert manager.port == 8000
        assert manager.collection_name == "epa_methods"
        assert manager.use_cloud is False
        assert manager._client is None
        assert manager._collection is None

    def test_embedded_mode(self):
        manager = ChromaManager(
            host="127.0.0.1",
            port=8000,
            persist_dir=Path("./data/chroma"),
        )
        assert manager.use_cloud is False

    def test_remote_mode(self):
        manager = ChromaManager(host="10.0.0.1", port=9999)
        assert manager.host == "10.0.0.1"
        assert manager.port == 9999

    def test_cloud_mode(self):
        manager = ChromaManager(use_cloud=True, api_key="key", tenant="t", database="db")
        assert manager.use_cloud is True
        assert manager.api_key == "key"
        assert manager.tenant == "t"
        assert manager.database == "db"


class TestChromaManagerHealth:
    def test_is_healthy_when_uninitialized(self):
        manager = ChromaManager()
        assert manager.is_healthy() is False

    def test_get_collection_before_init_raises(self):
        manager = ChromaManager()
        with pytest.raises(RuntimeError):
            manager.get_collection()


class TestChromaManagerOperations:
    @pytest.mark.asyncio
    async def test_upsert_uses_different_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        await manager.upsert(
            collection_name="other",
            documents=["doc1"],
            metadatas=[{"key": "value"}],
            ids=["id1"],
            embeddings=[[0.1] * 384],
        )
        assert manager._collection.name == "epa_methods"

    @pytest.mark.asyncio
    async def test_count_returns_zero_for_missing_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        count = await manager.count("nonexistent_collection")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        result = await manager.get("nonexistent_collection", ["id1"])
        assert result is None

    @pytest.mark.asyncio
    async def test_query_returns_empty_for_missing_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        result = await manager.query(
            collection_name="nonexistent_collection",
            query_embedding=[0.1] * 384,
            n_results=5,
        )
        assert result["documents"] == [[]]

    @pytest.mark.asyncio
    async def test_delete_returns_early_for_missing_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        await manager.delete("nonexistent_collection", ["id1"])

    @pytest.mark.asyncio
    async def test_get_collection_after_init(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        collection = manager.get_collection()
        assert collection is not None
        assert collection.name == "epa_methods"

    @pytest.mark.asyncio
    async def test_count_same_collection(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        count = await manager.count()
        assert count >= 0


class TestCreateChromaManager:
    @pytest.mark.asyncio
    async def test_convenience_function(self, tmp_path):
        manager = await create_chroma_manager(
            persist_dir=tmp_path / "chroma",
            collection_name="test_coll",
        )
        assert manager.collection_name == "test_coll"
        assert manager.is_healthy() is True
