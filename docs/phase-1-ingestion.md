# Phase 1: Document Ingestion Pipeline

## Overview

Phase 1 builds the foundational ingestion pipeline: **EPA Method PDFs → Structured Chunks → Embeddings → ChromaDB → Queryable CLI/API**.

**Timeline:** Weeks 1-3
**Goal:** Working `epa-kg ingest` and `epa-kg query` commands with ≥80% test coverage.

**Status:** ✅ **Phase 1 Complete** (core pipeline functional, query endpoint stable)

---

## Deliverables

| # | Deliverable | Status | Done Criteria |
|---|-------------|--------|---------------|
| 1 | `epa-kg ingest` CLI command | ✅ Done | `cargo run --bin epa-kg -- ingest --pdf-dir ./epa-methods` processes all PDFs |
| 2 | PDF → structured chunks | ✅ Done | TOC-aware chunking preserves section hierarchy; tables extracted |
| 3 | Embedding generation | ✅ Done | FastEmbed (default) + OpenRouter + Ollama providers working |
| 4 | ChromaDB persistence | ✅ Done | Embedded mode survives restart; data in `./data/chroma/` |
| 5 | `epa-kg query` CLI command | ✅ Done | Natural language query returns top-K chunks with citations |
| 6 | Unit test suite | ✅ Done | `cargo test --workspace` + `pytest python/ingestion/tests/` ≥ 80% coverage |
| 7 | Dockerfile | ✅ Done | Single image runs API + CLI |
| 8 | Query endpoint stability | ✅ Done | `reload=False` prevents worker crash on file changes (WinError 10054 fixed) |
| 9 | Fast iteration mode | ✅ Done | `max_files` parameter limits PDFs for dev testing (e.g., 50 → ~18 min) |
| 10 | Metadata extraction | ✅ Done | `method_number` + `method_title` extracted from first page, not body chunks |

---

## Technical Specifications

### Chunking Strategy: TOC-Aware Recursive Splitter

```python
# python/ingestion/chunking.py
class EPAMethodChunker:
    def __init__(
        self,
        chunk_size: int = 512,      # Target tokens per chunk
        chunk_overlap: int = 64,    # Token overlap
        toc_aware: bool = True      # Use PDF TOC if available
    )
```

**Algorithm:**
1. **Extract TOC** via PyMuPDF (`doc.get_toc()`)
2. **If TOC exists:** Map TOC entries → text spans → chunk by section
3. **If no TOC:** Regex detect section headers (`^\s*\d+(?:\.\d+)*\s+`)
4. **If no headers:** Fallback to recursive character splitting
5. **Enforce token limits:** Split oversized sections recursively with overlap
6. **Preserve metadata:** section number, title, page range, token count

**Output per chunk:**
```python
{
    "text": "Section 4.2.1: Sample Preparation...",
    "section": "4.2.1",
    "section_title": "Sample Preparation",
    "token_count": 487,
    "metadata": {"source_pdf": "epa-8270e.pdf", "split": false},
    "page_start": 12,
    "page_end": 14
}
```

### Embedding Providers

| Provider | Class | Config Key | Default Model | Dimensions |
|----------|-------|------------|---------------|------------|
| FastEmbed | `FastEmbedProvider` | `fastembed` | `BAAI/bge-small-en-v1.5` | 384 |
| OpenRouter | `OpenRouterEmbeddingProvider` | `openrouter` | `openai/text-embedding-3-small` | 1536 |
| Ollama | `OllamaEmbeddingProvider` | `ollama` | `nomic-embed-text` | 768 |

**Factory:** `get_embedding_provider(settings) -> EmbeddingProvider`

### Metadata Extraction

| Provider | Class | Config Key | Default Model |
|----------|-------|------------|---------------|
| OpenRouter | `OpenRouterMetadataExtractor` | `openrouter` | `anthropic/claude-3.5-sonnet` |
| Ollama | `OllamaMetadataExtractor` | `ollama` | `llama3.2:3b` |
| None | Regex fallback | `none` | N/A |

**Extracted fields:**
```json
{
  "method_number": "8270E",
  "method_title": "Semivolatile Organic Compounds by GC/MS",
  "revision": "E",
  "revision_date": "2018-02-01",
  "supersedes": "8270D",
  "status": "Active",
  "matrix": ["water", "soil", "waste"],
  "analytes": ["PAHs", "phenols", "phthalates"],
  "references": ["3500C", "3600C", "8000D"],
  "section_count": 24
}
```

### ChromaDB Collections

**Primary:** `epa_methods` (EPA method chunks)

**Planned (Phase 4):**
- `tenant_{id}_sops` — Lab SOPs
- `tenant_{id}_qaps` — Lab QAPs

**Index config:** `{"hnsw:space": "cosine"}`

---

## Configuration

### Environment Variables (`.env`)

```bash
# Ingestion
EPA_KG__INGESTION__PDF_DIR=./epa-methods
EPA_KG__INGESTION__CHUNK_SIZE=512
EPA_KG__INGESTION__CHUNK_OVERLAP=64
EPA_KG__INGESTION__TOC_AWARE=true
EPA_KG__INGESTION__MAX_FILE_SIZE_MB=100
EPA_KG__INGESTION__MAX_FILES=0           # 0 = all files, or limit for testing (e.g., 50)

# Service behavior
EPA_KG__APP__RELOAD=false                 # Disable auto-reload for stability

# Embeddings (choose one)
EPA_KG__EMBEDDING__PROVIDER=fastembed
# FastEmbed
EPA_KG__EMBEDDING__FASTEMBED__MODEL=BAAI/bge-small-en-v1.5
EPA_KG__EMBEDDING__FASTEMBED__BATCH_SIZE=32
# OpenRouter
# EPA_KG__EMBEDDING__PROVIDER=openrouter
# EPA_KG__EMBEDDING__OPENROUTER__API_KEY=sk-or-...
# EPA_KG__EMBEDDING__OPENROUTER__MODEL=openai/text-embedding-3-small
# EPA_KG__EMBEDDING__OPENROUTER__DIMENSIONS=1536
# Ollama
# EPA_KG__EMBEDDING__PROVIDER=ollama
# EPA_KG__EMBEDDING__OLLAMA__HOST=http://localhost:11434
# EPA_KG__EMBEDDING__OLLAMA__MODEL=nomic-embed-text

# LLM Metadata (choose one)
EPA_KG__LLM__PROVIDER=ollama
# OpenRouter
# EPA_KG__LLM__PROVIDER=openrouter
# EPA_KG__LLM__OPENROUTER__API_KEY=sk-or-...
# EPA_KG__LLM__OPENROUTER__MODEL=anthropic/claude-3.5-sonnet
# Ollama
# EPA_KG__LLM__OLLAMA__HOST=http://localhost:11434
# EPA_KG__LLM__OLLAMA__MODEL=llama3.2:3b
# None
# EPA_KG__LLM__PROVIDER=none
```

---

## Testing Strategy

### Rust Tests (`cargo test --workspace`)

| Test | Location | Coverage |
|------|----------|----------|
| Config loading | `epa-kg-core/tests/config.rs` | Settings + env precedence |
| Error types | `epa-kg-core/tests/error.rs` | Error conversions |
| CLI commands | `epa-kg-ingest/tests/cli.rs` | `ingest`, `query`, `graph`, `serve` |
| Graph engine | `epa-kg-graph/tests/engine.rs` | Add nodes/edges, neighbors |

### Python Tests (`pytest python/ingestion/tests/`)

| Test | Coverage |
|------|----------|
| `test_chunker.py` | Token counting, section extraction, recursive splitting |
| `test_embeddings.py` | Provider factory, batch embedding, dimensions |
| `test_chroma.py` | Embedded client, upsert, query, count, collections |
| `test_metadata.py` | LLM extraction, regex fallback, field validation |
| `test_main.py` | `/health`, `/ingest`, `/query` endpoints |

**Run:**
```bash
# Rust
cargo test --workspace

# Python
cd python/ingestion && uv run pytest -v --cov=ingestion
```

---

## Docker

### Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Build Rust
FROM rust:1.80 as rust-builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
RUN cargo build --release --workspace

# Stage 2: Python deps
FROM python:3.12-slim as python-deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen

# Stage 3: Runtime
FROM debian:bookworm-slim
WORKDIR /app

# Install runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy binaries
COPY --from=rust-builder /app/target/release/epa-kg /usr/local/bin/
COPY --from=rust-builder /app/target/release/epa-kg-tauri /usr/local/bin/

# Copy Python service
COPY --from=python-deps /root/.local /root/.local
COPY python/ingestion ./python/ingestion

# Ensure uv is in PATH
ENV PATH="/root/.local/bin:${PATH}"

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8001 8080
ENTRYPOINT ["/entrypoint.sh"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: epa_kg
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  chroma:
    image: chromadb/chroma:latest
    ports: ["8000:8000"]
    volumes:
      - chromadata:/chroma/data

  api:
    build: .
    command: ["epa-kg", "serve", "--port", "8080"]
    ports: ["8080:8080"]
    environment:
      - EPA_KG__DATABASE__URL=postgresql://postgres:postgres@postgres:5432/epa_kg
      - EPA_KG__CHROMA__HOST=chroma
      - EPA_KG__CHROMA__PORT=8000
    depends_on: [postgres, chroma]

  ingestion:
    build: .
    command: ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
    working_dir: /app/python/ingestion
    ports: ["8001:8001"]
    environment:
      - EPA_KG__CHROMA__HOST=chroma
      - EPA_KG__CHROMA__PORT=8000
    depends_on: [chroma]

volumes:
  pgdata:
  chromadata:
```

---

## Quickstart (Phase 1)

```bash
# 1. Prerequisites
# - Rust 1.80+ (rustup)
# - Python 3.12+ (uv)
# - PostgreSQL 16+ (or Docker)
# - Ollama (optional, for local LLM)

# 2. Clone & configure
git clone https://github.com/AlexJ-StL/epa-knowledge-graph
cd epa-knowledge-graph
cp .env.example .env
# Edit .env with your paths / API keys

# 3. Start services (Docker recommended)
docker compose up -d postgres chroma

# 4. Build Rust
cargo build --release --workspace

# 5. Start Python ingestion service
cd python/ingestion
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8001

# 6. Ingest EPA methods
cd ../..
./target/release/epa-kg ingest --pdf-dir /path/to/epa-methods

# 7. Query
./target/release/epa-kg query "How do I prepare soil for 8270E?"
```

---

## Acceptance Criteria (Phase 1 Complete)

- [x] `epa-kg ingest` processes 50+ EPA method PDFs without errors
- [x] `epa-kg query` returns relevant results with method/section citations
- [x] Embedded ChromaDB persists across restarts
- [x] All embedding providers work (FastEmbed default, OpenRouter, Ollama)
- [x] Metadata extraction works with Ollama (local) and OpenRouter (cloud)
- [x] Unit tests pass: `cargo test --workspace` + `pytest python/ingestion/tests/`
- [x] Docker image builds and runs: `docker compose up`
- [x] Code coverage ≥ 80% on ingestion logic
- [x] Query endpoint stable (auto-reload disabled)
- [x] Metadata extraction: method_number + method_title from first page
- [x] Fast iteration: `max_files` parameter for dev testing