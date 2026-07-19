# EPA Knowledge Graph - Python Ingestion Service Main Application

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from .chroma_client import ChromaManager
from .chunking import EPAMethodChunker
from .config import settings
from .embeddings import EmbeddingProvider, get_embedding_provider
from .metadata import MetadataExtractor, get_metadata_extractor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
chroma_manager: ChromaManager | None = None
embedding_provider: EmbeddingProvider | None = None
metadata_extractor: MetadataExtractor | None = None
chunker: EPAMethodChunker | None = None


def sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Convert list/dict values to JSON strings for ChromaDB compatibility."""
    result = {}
    for key, value in meta.items():
        if value is None:
            continue
        elif isinstance(value, list | dict):
            result[key] = json.dumps(value)
        elif isinstance(value, str | int | float | bool):
            result[key] = value
        else:
            result[key] = str(value)
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global chroma_manager, embedding_provider, metadata_extractor, chunker

    logger.info("Starting EPA Knowledge Graph Ingestion Service...")

    # Initialize ChromaDB
    chroma_manager = ChromaManager(
        host=settings.chroma.host,
        port=settings.chroma.port,
        collection_name=settings.chroma.collection,
        persist_dir=settings.chroma.persist_dir,
        use_cloud=settings.chroma.use_cloud,
        api_key=settings.chroma.api_key,
        tenant=settings.chroma.tenant,
        database=settings.chroma.database,
    )
    await chroma_manager.initialize()
    logger.info("ChromaDB initialized")

    # Initialize embedding provider
    embedding_provider = get_embedding_provider(settings)
    logger.info(f"Embedding provider initialized: {settings.embedding.provider}")

    # Initialize metadata extractor
    metadata_extractor = get_metadata_extractor(settings)
    logger.info(f"Metadata extractor initialized: {settings.llm.provider}")

    # Initialize chunker
    chunker = EPAMethodChunker(
        chunk_size=settings.ingestion.chunk_size,
        chunk_overlap=settings.ingestion.chunk_overlap,
        toc_aware=settings.ingestion.toc_aware,
    )
    logger.info("Chunker initialized")

    yield

    # Cleanup
    logger.info("Shutting down...")
    if chroma_manager:
        await chroma_manager.close()


app = FastAPI(
    title="EPA Knowledge Graph - Ingestion Service",
    description="PDF parsing, chunking, embedding, and vector storage for EPA methods",
    version="0.1.0",
    lifespan=lifespan,
)


# Request/Response Models
class IngestRequest(BaseModel):
    pdf_dir: str | None = None
    collection: str = "epa_methods"
    force_reindex: bool = False
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    toc_aware: bool | None = None
    max_files: int | None = None


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int
    time_ms: int
    errors: list[str] = []


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    collection: str = "epa_methods"
    embedding_provider: str | None = None
    embedding_model: str | None = None


class Source(BaseModel):
    method: str
    section: str
    chunk_index: int
    text: str
    score: float
    metadata: dict[str, Any] = {}


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    query_time_ms: int


class HealthResponse(BaseModel):
    status: str
    chroma_connected: bool
    embedding_provider: str
    llm_provider: str


class GraphExtractRequest(BaseModel):
    collection: str = "epa_methods"


class CitationEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    confidence: float
    context: str | None = None


class GraphExtractResponse(BaseModel):
    status: str
    edges_extracted: int
    edges: list[CitationEdge] = []


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    chroma_ok = chroma_manager is not None and chroma_manager.is_healthy()
    return HealthResponse(
        status="ok" if chroma_ok else "degraded",
        chroma_connected=chroma_ok,
        embedding_provider=settings.embedding.provider,
        llm_provider=settings.llm.provider,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks):
    """Ingest EPA method PDFs into ChromaDB."""
    import time

    start_time = time.time()

    pdf_dir = Path(request.pdf_dir) if request.pdf_dir else settings.ingestion.pdf_dir
    collection = request.collection or settings.chroma.collection

    if not pdf_dir.exists():
        raise HTTPException(status_code=400, detail=f"PDF directory does not exist: {pdf_dir}")

    local_chunker = _get_chunker_for_request(request)

    pdf_files = _find_pdf_files(pdf_dir)
    if request.max_files is not None and request.max_files >= 0:
        pdf_files = pdf_files[: request.max_files]
    if not pdf_files:
        raise HTTPException(status_code=400, detail=f"No PDF files found in {pdf_dir}")

    logger.info(f"Starting ingestion of {len(pdf_files)} PDFs from {pdf_dir}")

    documents_processed = 0
    chunks_created = 0
    errors = []

    for pdf_file in pdf_files:
        try:
            file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.ingestion.max_file_size_mb:
                errors.append(
                    f"{pdf_file.name}: File too large ({file_size_mb:.1f}MB > {settings.ingestion.max_file_size_mb}MB)"
                )
                continue

            result = await _process_single_pdf(
                pdf_file=pdf_file,
                collection=collection,
                chunker=local_chunker,
                force_reindex=request.force_reindex,
            )

            documents_processed += 1
            chunks_created += result["chunks_created"]

        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
            errors.append(f"{pdf_file.name}: {str(e)}")

    elapsed_ms = int((time.time() - start_time) * 1000)

    return IngestResponse(
        status="completed" if not errors else "completed_with_errors",
        documents_processed=documents_processed,
        chunks_created=chunks_created,
        time_ms=elapsed_ms,
        errors=errors,
    )


def _get_chunker_for_request(request: IngestRequest) -> EPAMethodChunker:
    """Return the chunker to use, honoring request overrides when provided."""
    chunk_size = request.chunk_size or settings.ingestion.chunk_size
    chunk_overlap = request.chunk_overlap or settings.ingestion.chunk_overlap
    toc_aware = request.toc_aware if request.toc_aware is not None else settings.ingestion.toc_aware

    if (
        chunk_size != settings.ingestion.chunk_size
        or chunk_overlap != settings.ingestion.chunk_overlap
        or toc_aware != settings.ingestion.toc_aware
    ):
        return EPAMethodChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            toc_aware=toc_aware,
        )

    return chunker


def _find_pdf_files(pdf_dir: Path) -> list[Path]:
    """Return PDF files in the given directory."""
    return list(pdf_dir.glob("*.pdf"))


async def _process_single_pdf(
    pdf_file: Path,
    collection: str,
    chunker: EPAMethodChunker,
    force_reindex: bool,
) -> dict[str, int]:
    """Process a single PDF and return chunk count."""
    return await process_pdf(
        pdf_file=pdf_file,
        collection=collection,
        chunker=chunker,
        embedding_provider=embedding_provider,
        metadata_extractor=metadata_extractor,
        chroma_manager=chroma_manager,
        force_reindex=force_reindex,
    )


@app.post("/query", response_model=QueryResponse)
async def query_knowledge_graph(request: QueryRequest):
    """Query the knowledge graph with natural language."""
    import time

    start_time = time.time()

    if not chroma_manager or not embedding_provider:
        raise HTTPException(status_code=503, detail="Service not initialized")

    collection = request.collection or settings.chroma.collection

    # Generate query embedding
    query_embedding = await embedding_provider.embed_query(request.question)

    # Search ChromaDB
    results = await chroma_manager.query(
        collection_name=collection,
        query_embedding=query_embedding,
        n_results=request.top_k,
    )

    # Format sources
    sources = []
    for i, (doc, metadata, distance) in enumerate(
        zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        )
    ):
        sources.append(
            Source(
                method=metadata.get("method_number", "Unknown"),
                section=metadata.get("section", "Unknown"),
                chunk_index=metadata.get("chunk_index", i),
                text=doc,
                score=1.0 - distance,  # Convert distance to similarity score
                metadata=metadata,
            )
        )

    # Generate answer
    if sources:
        answer = f"Found {len(sources)} relevant sections for your query:\n\n"
        for src in sources:
            answer += f"**{src.method} §{src.section}** (score: {src.score:.3f})\n"
            answer += f"{src.text[:300]}...\n\n"
    else:
        answer = "No relevant sections found for your query."

    elapsed_ms = int((time.time() - start_time) * 1000)

    return QueryResponse(
        answer=answer,
        sources=sources,
        query_time_ms=elapsed_ms,
    )


@app.post("/graph/extract", response_model=GraphExtractResponse)
async def extract_graph_references(request: GraphExtractRequest):
    """Extract citation references from all chunks in a collection."""
    import re

    if not chroma_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")

    collection = request.collection or settings.chroma.collection

    # Get all chunks from the collection
    results = await chroma_manager.get_all(collection, include_embeddings=True)

    if not results or not results.get("documents"):
        return GraphExtractResponse(
            status="completed",
            edges_extracted=0,
            edges=[],
        )

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    ids = results["ids"][0] if results["ids"] else []
    embeddings = (
        results.get("embeddings", [None])[0]
        if results.get("embeddings")
        else [None] * len(documents)
    )

    if not documents:
        return GraphExtractResponse(
            status="completed",
            edges_extracted=0,
            edges=[],
        )

    # Regex patterns for reference extraction (matching Rust implementation)
    method_pattern = re.compile(r"(?i)(?:EPA\s+)?(?:Method|SW-846)\s+(\d{4}[A-Z]?)\b")
    section_pattern = re.compile(r"(?i)(?:Section|Sec\.|§)\s+(\d+(?:\.\d+)+)\b")
    supersedes_pattern = re.compile(
        r"(?i)(?:Method\s+)?(\d{4}[A-Z]?)\s+(?:supersedes?|replaces?)\s+(?:Method\s+)?(\d{4}[A-Z]?)"
    )

    edges = []
    seen = set()

    for doc_id, doc_text, metadata in zip(ids, documents, metadatas):
        method_num = metadata.get("method_number", "UNKNOWN")

        # Extract method references
        for match in method_pattern.finditer(doc_text):
            target_method = match.group(1).upper()
            source_id = doc_id
            target_id = f"METHOD_{target_method}"
            edge_key = (source_id, target_id, "REFERENCES")

            if edge_key not in seen:
                seen.add(edge_key)
                edges.append(
                    CitationEdge(
                        source_id=source_id,
                        target_id=target_id,
                        edge_type="REFERENCES",
                        confidence=0.9,
                        context=match.group(0),
                    )
                )

        # Extract section references (need source method to construct target)
        if method_num != "UNKNOWN":
            for match in section_pattern.finditer(doc_text):
                section = match.group(1)
                target_id = f"METHOD_{method_num}_{section.replace('.', '_')}"
                edge_key = (doc_id, target_id, "CITES_SECTION")

                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append(
                        CitationEdge(
                            source_id=doc_id,
                            target_id=target_id,
                            edge_type="CITES_SECTION",
                            confidence=0.85,
                            context=match.group(0),
                        )
                    )

        # Extract supersedes relationships
        for match in supersedes_pattern.finditer(doc_text):
            new_method = match.group(1).upper()
            old_method = match.group(2).upper()
            edge_key = (f"METHOD_{new_method}", f"METHOD_{old_method}", "SUPERSEDES")

            if edge_key not in seen:
                seen.add(edge_key)
                edges.append(
                    CitationEdge(
                        source_id=f"METHOD_{new_method}",
                        target_id=f"METHOD_{old_method}",
                        edge_type="SUPERSEDES",
                        confidence=0.95,
                        context=match.group(0),
                    )
                )

    logger.info(f"Extracted {len(edges)} citation edges from collection '{collection}'")

    # Enrich chunk metadata with graph information
    enriched_count = await _enrich_chunk_metadata(
        chroma_manager=chroma_manager,
        collection=collection,
        edges=edges,
        ids=ids,
        metadatas=metadatas,
        documents=documents,
        embeddings=embeddings,
    )

    logger.info(f"Enriched metadata for {enriched_count} chunks")

    return GraphExtractResponse(
        status="completed",
        edges_extracted=len(edges),
        edges=edges,
    )


async def _enrich_chunk_metadata(
    chroma_manager: ChromaManager,
    collection: str,
    edges: list[CitationEdge],
    ids: list[str],
    metadatas: list[dict[str, Any]],
    documents: list[str],
    embeddings: list[list[float] | None],
) -> int:
    """Enrich chunk metadata with graph cross-reference information.

    Groups edges by source method and updates chunk metadata with:
    - `references`: list of methods referenced by this chunk's method
    - `supersedes`: list of methods this method supersedes
    - `section_refs`: list of sections referenced by this chunk
    """
    from collections import defaultdict

    # Group edges by method (extracted from chunk IDs)
    method_edges = defaultdict(
        lambda: {"references": set(), "supersedes": set(), "sections": set()}
    )

    for edge in edges:
        # Extract method from source_id (format: METHOD_8270E_4_2_1 or METHOD_8270E)
        source_parts = edge.source_id.split("_")
        if len(source_parts) >= 2:
            method_num = source_parts[1]
            if method_num.isdigit() and len(method_num) == 4:
                # It's a method ID
                if edge.edge_type == "REFERENCES":
                    target_parts = edge.target_id.split("_")
                    if len(target_parts) >= 2:
                        target_method = target_parts[1]
                        method_edges[method_num]["references"].add(target_method)
                elif edge.edge_type == "SUPERSEDES":
                    target_parts = edge.target_id.split("_")
                    if len(target_parts) >= 2:
                        target_method = target_parts[1]
                        method_edges[method_num]["supersedes"].add(target_method)
                elif edge.edge_type == "CITES_SECTION":
                    # Extract section from target_id
                    section = edge.target_id.replace(f"METHOD_{method_num}_", "")
                    method_edges[method_num]["sections"].add(section)

    # Update chunk metadata
    enriched_count = 0
    for chunk_id, metadata, doc_text in zip(ids, metadatas, documents):
        method_num = metadata.get("method_number", "")
        if not method_num or method_num not in method_edges:
            continue

        edges_data = method_edges[method_num]
        updated_metadata = dict(metadata)

        if edges_data["references"]:
            updated_metadata["references"] = sorted(edges_data["references"])
        if edges_data["supersedes"]:
            updated_metadata["supersedes"] = sorted(edges_data["supersedes"])
        if edges_data["sections"]:
            updated_metadata["section_refs"] = sorted(edges_data["sections"])

        # Only update if metadata changed
        if updated_metadata != metadata:
            try:
                embedding = embeddings[enriched_count] if enriched_count < len(embeddings) else None
                await chroma_manager.upsert(
                    collection_name=collection,
                    documents=[doc_text],
                    metadatas=[sanitize_metadata(updated_metadata)],
                    ids=[chunk_id],
                    embeddings=[embedding] if embedding else [],
                )
                enriched_count += 1
            except Exception as e:
                logger.warning(f"Failed to enrich metadata for {chunk_id}: {e}")

    return enriched_count


async def process_pdf(
    pdf_file: Path,
    collection: str,
    chunker: EPAMethodChunker,
    embedding_provider: EmbeddingProvider,
    metadata_extractor: MetadataExtractor | None,
    chroma_manager: ChromaManager,
    force_reindex: bool = False,
) -> dict[str, int]:
    """Process a single PDF file with batch embeddings."""
    logger.info(f"Processing {pdf_file.name}...")

    chunks = chunker.chunk_pdf(pdf_file)

    if not chunks:
        logger.warning(f"No chunks extracted from {pdf_file.name}")
        return {"chunks_created": 0}

    doc_metadata = await _extract_document_metadata(chunks, pdf_file.name, metadata_extractor)
    method_num = doc_metadata.get("method_number", "UNKNOWN")

    new_chunks, new_texts = await _filter_new_chunks(
        chunks=chunks,
        method_num=method_num,
        collection=collection,
        force_reindex=force_reindex,
        chroma_manager=chroma_manager,
    )

    if not new_texts:
        logger.info(f"All {len(chunks)} chunks already indexed for {pdf_file.name}, skipping")
        return {"chunks_created": 0}

    new_embeddings = await embedding_provider.embed_documents(new_texts)

    documents, metadatas, ids, embeddings = _build_upsert_payload(
        new_chunks=new_chunks,
        new_embeddings=new_embeddings,
        method_num=method_num,
        doc_metadata=doc_metadata,
        pdf_file=pdf_file,
    )

    if documents:
        await chroma_manager.upsert(
            collection_name=collection,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )
        logger.info(f"Stored {len(documents)} chunks from {pdf_file.name}")

    return {"chunks_created": len(documents)}


async def _extract_document_metadata(
    chunks: list[dict[str, Any]],
    filename: str,
    metadata_extractor: MetadataExtractor | None,
) -> dict[str, Any]:
    """Extract document-level metadata from the first chunk."""
    if metadata_extractor and chunks:
        first_page_text = chunks[0].get("first_page_text", "")
        return await metadata_extractor.extract_metadata(
            chunks[0]["text"], filename, first_page_text=first_page_text
        )
    return {}


async def _filter_new_chunks(
    chunks: list[dict[str, Any]],
    method_num: str,
    collection: str,
    force_reindex: bool,
    chroma_manager: ChromaManager,
) -> tuple[list[tuple[int, dict[str, Any]]], list[str]]:
    """Return chunks that need indexing and their texts for batch embedding."""
    new_chunks = []
    new_texts = []

    for i, chunk in enumerate(chunks):
        section = chunk.get("section", "0")
        chunk_id = f"METHOD_{method_num}_{section}_{i}"

        if not force_reindex:
            existing = await chroma_manager.get(collection, [chunk_id])
            if existing and existing.get("ids"):
                logger.debug(f"Chunk {chunk_id} already exists, skipping")
                continue

        new_chunks.append((i, chunk))
        new_texts.append(chunk["text"])

    return new_chunks, new_texts


def _build_upsert_payload(
    new_chunks: list[tuple[int, dict[str, Any]]],
    new_embeddings: list[list[float]],
    method_num: str,
    doc_metadata: dict[str, Any],
    pdf_file: Path,
) -> tuple[list[str], list[dict[str, Any]], list[str], list[list[float]]]:
    """Build documents, metadatas, ids, and embeddings for ChromaDB upsert."""
    documents = []
    metadatas = []
    ids = []
    embeddings = []

    for idx, ((i, chunk), embedding) in enumerate(zip(new_chunks, new_embeddings)):
        section = chunk.get("section", "0")
        chunk_id = f"METHOD_{method_num}_{section}_{i}"

        metadata = sanitize_metadata(
            {
                "method_number": method_num,
                "method_title": doc_metadata.get("method_title", ""),
                "section": section,
                "section_title": chunk.get("section_title", ""),
                "chunk_index": i,
                "token_count": chunk.get("token_count", 0),
                "source_pdf": pdf_file.name,
                **doc_metadata,
                **chunk.get("metadata", {}),
            }
        )

        documents.append(chunk["text"])
        metadatas.append(metadata)
        ids.append(chunk_id)
        embeddings.append(embedding)

    return documents, metadatas, ids, embeddings


if __name__ == "__main__":
    import uvicorn

    module = "ingestion.main:app" if __package__ else "main:app"
    uvicorn.run(
        module,
        host=settings.app.host,
        port=settings.app.port,
        log_level=settings.app.log_level,
        reload=settings.app.reload,
    )
