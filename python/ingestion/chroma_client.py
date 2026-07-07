# EPA Knowledge Graph - ChromaDB Client

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)


class ChromaManager:
    """Manages ChromaDB connections and operations."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        collection_name: str = "epa_methods",
        persist_dir: Path = Path("./data/chroma"),
        use_cloud: bool = False,
        api_key: Optional[str] = None,
        tenant: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.use_cloud = use_cloud
        self.api_key = api_key
        self.tenant = tenant
        self.database = database
        
        self._client = None
        self._collection = None
    
    async def initialize(self):
        """Initialize ChromaDB client and collection."""
        if self.use_cloud and self.api_key:
            # ChromaDB Cloud
            logger.info("Connecting to ChromaDB Cloud...")
            self._client = chromadb.CloudClient(
                api_key=self.api_key,
                tenant=self.tenant,
                database=self.database,
            )
        else:
            # Local embedded or server
            if self.host == "127.0.0.1" and self.port == 8000:
                # Embedded mode
                logger.info(f"Initializing embedded ChromaDB at {self.persist_dir}")
                self.persist_dir.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
            else:
                # Remote server
                logger.info(f"Connecting to ChromaDB server at {self.host}:{self.port}")
                self._client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                )
        
        # Get or create collection
        try:
            self._collection = self._client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self._collection = self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def is_healthy(self) -> bool:
        """Check if ChromaDB connection is healthy."""
        try:
            if self._client:
                self._client.heartbeat()
                return True
        except Exception:
            pass
        return False
    
    async def close(self):
        """Close connections."""
        # ChromaDB client doesn't need explicit close
        pass
    
    def get_collection(self) -> Collection:
        """Get the collection instance."""
        if not self._collection:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._collection
    
    async def upsert(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]],
    ):
        """Upsert documents into collection."""
        if collection_name != self.collection_name:
            # Get or create different collection
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                collection = self._client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        else:
            collection = self._collection
        
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )
        logger.debug(f"Upserted {len(documents)} documents to {collection_name}")
    
    async def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query collection for similar documents."""
        if collection_name != self.collection_name:
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
        else:
            collection = self._collection
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        return results
    
    async def get(
        self,
        collection_name: str,
        ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Get documents by IDs."""
        if collection_name != self.collection_name:
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                return None
        else:
            collection = self._collection
        
        return collection.get(ids=ids)
    
    async def delete(
        self,
        collection_name: str,
        ids: List[str],
    ):
        """Delete documents by IDs."""
        if collection_name != self.collection_name:
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                return
        else:
            collection = self._collection
        
        collection.delete(ids=ids)
        logger.debug(f"Deleted {len(ids)} documents from {collection_name}")
    
    async def count(self, collection_name: str = None) -> int:
        """Count documents in collection."""
        if collection_name is None:
            collection_name = self.collection_name
        
        if collection_name != self.collection_name:
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                return 0
        else:
            collection = self._collection
        
        return collection.count()
    
    async def list_collections(self) -> List[str]:
        """List all collection names."""
        return [c.name for c in self._client.list_collections()]


# Convenience function
async def create_chroma_manager(
    host: str = "127.0.0.1",
    port: int = 8000,
    collection_name: str = "epa_methods",
    persist_dir: Path = Path("./data/chroma"),
    use_cloud: bool = False,
    api_key: Optional[str] = None,
) -> ChromaManager:
    """Create and initialize a ChromaManager."""
    manager = ChromaManager(
        host=host,
        port=port,
        collection_name=collection_name,
        persist_dir=persist_dir,
        use_cloud=use_cloud,
        api_key=api_key,
    )
    await manager.initialize()
    return manager