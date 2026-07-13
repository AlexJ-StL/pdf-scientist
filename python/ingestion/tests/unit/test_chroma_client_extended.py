from unittest.mock import MagicMock, patch

import pytest

from ingestion.chroma_client import ChromaManager


class TestChromaCloudMode:
    @pytest.mark.asyncio
    async def test_cloud_initialization(self):
        mock_client = MagicMock()
        mock_client.get_collection.return_value = MagicMock()

        with patch("ingestion.chroma_client.chromadb.CloudClient", return_value=mock_client):
            manager = ChromaManager(
                use_cloud=True,
                api_key="cloud_key",
                tenant="tenant_id",
                database="db_name",
            )
            await manager.initialize()
            assert manager._client is mock_client


class TestChromaRemoteMode:
    @pytest.mark.asyncio
    async def test_remote_server_initialization(self):
        mock_client = MagicMock()
        mock_client.get_collection.return_value = MagicMock()

        with patch("ingestion.chroma_client.chromadb.HttpClient", return_value=mock_client):
            manager = ChromaManager(host="10.0.0.1", port=9999)
            await manager.initialize()
            assert manager._client is mock_client


class TestChromaListCollections:
    @pytest.mark.asyncio
    async def test_list_collections(self, tmp_path):
        manager = ChromaManager(persist_dir=tmp_path / "chroma")
        await manager.initialize()

        mock_coll = MagicMock()
        mock_coll.name = "coll1"
        manager._client.list_collections = MagicMock(return_value=[mock_coll])

        names = await manager.list_collections()
        assert names == ["coll1"]


class TestChromaHealthEdgeCases:
    def test_is_healthy_client_raises(self):
        manager = ChromaManager()
        manager._client = MagicMock()
        manager._client.heartbeat.side_effect = Exception("connection lost")
        assert manager.is_healthy() is False

    def test_is_healthy_client_none(self):
        manager = ChromaManager()
        assert manager.is_healthy() is False
