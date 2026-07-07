# EPA Knowledge Graph - Python Ingestion Service Tests

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chunking import EPAMethodChunker
from embeddings import OpenRouterEmbeddingProvider, OllamaEmbeddingProvider
from chroma_client import ChromaManager


class TestChunker:
    """Tests for EPAMethodChunker."""
    
    def test_token_counting(self):
        chunker = EPAMethodChunker()
        text = "This is a test sentence."
        tokens = chunker.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
    
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
    
    def test_recursive_splitting(self):
        chunker = EPAMethodChunker(chunk_size=100, chunk_overlap=20)
        long_text = " ".join(["This is a sentence."] * 50)  # Long text
        
        chunks = chunker._split_text_recursive(
            long_text, "1.0", "Test Section", "test.pdf"
        )
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.chunk_size * 1.5  # Allow some overflow


class TestEmbeddingProviders:
    """Tests for embedding providers (require network/API keys)."""
    
    @pytest.mark.skip(reason="Requires OpenRouter API key")
    def test_openrouter_embedding(self):
        # This would test with actual API key
        pass
    
    @pytest.mark.skip(reason="Requires running Ollama")
    def test_ollama_embedding(self):
        # This would test with local Ollama
        pass


class TestChromaManager:
    """Tests for ChromaManager."""
    
    @pytest.mark.asyncio
    async def test_embedded_chroma(self, tmp_path):
        manager = ChromaManager(
            persist_dir=tmp_path / "chroma",
            collection_name="test_collection",
        )
        await manager.initialize()
        
        assert manager.is_healthy()
        
        # Test upsert and query
        await manager.upsert(
            collection_name="test_collection",
            documents=["test document 1", "test document 2"],
            metadatas=[{"source": "test1"}, {"source": "test2"}],
            ids=["id1", "id2"],
            embeddings=[[0.1] * 384, [0.2] * 384],
        )
        
        count = await manager.count("test_collection")
        assert count == 2
        
        # Test query
        results = await manager.query(
            collection_name="test_collection",
            query_embedding=[0.15] * 384,
            n_results=2,
        )
        
        assert "documents" in results
        assert len(results["documents"][0]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])