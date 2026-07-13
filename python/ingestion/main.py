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
        elif isinstance(value, (list, dict)):
            result[key] = json.dumps(value)
        elif isinstance(value, (str, int, float, bool)):
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
        host=settings.chroma_host,
        port=settings.chroma_port,
        collection_name=settings.chroma_collection,
        persist_dir=settings.chroma_persist_dir,
        use_cloud=settings.chroma_use_cloud,
        api_key=settings.chroma_api_key,
        tenant=settings.chroma_tenant,
        database=settings.chroma_database,
    )
    await chroma_manager.initialize()
    logger.info("ChromaDB initialized")

    # Initialize embedding provider
    embedding_provider = get_embedding_provider(settings)
    logger.info(f"Embedding provider initialized: {settings.embedding_provider}")

    # Initialize metadata extractor
    metadata_extractor = get_metadata_extractor(settings)
    logger.info(f"Metadata extractor initialized: {settings.llm_provider}")

    # Initialize chunker
    chunker = EPAMethodChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        toc_aware=settings.toc_aware,
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


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    chroma_ok = chroma_manager is not None and chroma_manager.is_healthy()
    return HealthResponse(
        status="ok" if chroma_ok else "degraded",
        chroma_connected=chroma_ok,
        embedding_provider=settings.embedding_provider,
        llm_provider=settings.llm_provider,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks):
    """Ingest EPA method PDFs into ChromaDB."""
    import time

    start_time = time.time()

    pdf_dir = Path(request.pdf_dir) if request.pdf_dir else settings.pdf_dir
    collection = request.collection or settings.chroma_collection

    if not pdf_dir.exists():
        raise HTTPException(status_code=400, detail=f"PDF directory does not exist: {pdf_dir}")

    local_chunker = _get_chunker_for_request(request)

    pdf_files = _find_pdf_files(pdf_dir)
    if not pdf_files:
        raise HTTPException(status_code=400, detail=f"No PDF files found in {pdf_dir}")

    logger.info(f"Starting ingestion of {len(pdf_files)} PDFs from {pdf_dir}")

    documents_processed = 0
    chunks_created = 0
    errors = []

    for pdf_file in pdf_files:
        try:
            file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_file_size_mb:
                errors.append(
                    f"{pdf_file.name}: File too large ({file_size_mb:.1f}MB > {settings.max_file_size_mb}MB)"
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
    chunk_size = request.chunk_size or settings.chunk_size
    chunk_overlap = request.chunk_overlap or settings.chunk_overlap
    toc_aware = request.toc_aware if request.toc_aware is not None else settings.toc_aware

    if (
        chunk_size != settings.chunk_size
        or chunk_overlap != settings.chunk_overlap
        or toc_aware != settings.toc_aware
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

    collection = request.collection or settings.chroma_collection

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
        return await metadata_extractor.extract_metadata(chunks[0]["text"], filename)
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

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True,
    )
