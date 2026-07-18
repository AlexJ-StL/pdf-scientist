# Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EPA Knowledge Graph                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────┐    │
│  │  EPA PDFs    │───▶│  Python Ingestion │───▶│  ChromaDB (Vector)     │    │
│  │  (local)     │    │  Service (FastAPI)│    │  - Embeddings          │    │
│  └──────────────┘    │  - Chunking       │    │  - Metadata            │    │
│                      │  - Embeddings     │    │  - Semantic Search     │    │
│  ┌──────────────┐    │  - LLM Metadata   │    └───────────┬────────────┘    │
│  │  Lab Docs    │───▶│                   │                │                 │
│  │  (SOP/QAP)   │    └────────┬──────────┘                │                 │
│  └──────────────┘             │                           │                 │
│                               ▼                           ▼                 │
│                      ┌──────────────────┐    ┌────────────────────────┐    │
│                      │  Rust Core       │◀──▶│  PostgreSQL (Relational)│    │
│                      │  (Workspace)     │    │  - Tenants/Users       │    │
│                      │                  │    │  - Audit Logs          │    │
│                      │ ┌──────────────┐ │    │  - Document Metadata   │    │
│                      │ │ epa-kg-core  │ │    └────────────────────────┘    │
│                      │ │ epa-kg-ingest│ │                  │                │
│                      │ │ epa-kg-api   │ │                  │                │
│                      │ │ epa-kg-graph │ │                  ▼                │
│                      │ │ epa-kg-tauri │ │    ┌────────────────────────┐    │
│                      │ └──────────────┘ │    │  Graph Layer           │    │
│                      └────────┬─────────┘    │  - SQLite (Phase 1)    │    │
│                               │              │  - Neo4j (Phase 2+)    │    │
│                               ▼              └───────────┬────────────┘    │
│                      ┌──────────────────┐                │                 │
│                      │  Tauri v2 App    │◀───────────────┘                 │
│                      │  (React/TS)      │    Frontend queries              │
│                      │  Desktop/Mobile  │    both vector + graph           │
│                      └──────────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Rust Workspace (`crates/`)

| Crate | Purpose | Key Dependencies |
|-------|---------|------------------|
| `epa-kg-core` | Shared types, config, errors | `config`, `thiserror`, `serde`, `sqlx`, `validator` |
| `epa-kg-ingest` | CLI binary + Python bridge | `clap`, `reqwest`, `tokio`, `epa-kg-core` |
| `epa-kg-api` | Axum HTTP server | `axum`, `tower-http`, `chromadb`, `epa-kg-core` |
| `epa-kg-graph` | Citation graph engine | `petgraph`, `epa-kg-core` |
| `epa-kg-tauri` | Tauri v2 entry point | `tauri`, `tauri-plugin-opener`, `epa-kg-*` |

**Workspace config:** `Cargo.toml` with shared dependencies via `[workspace.dependencies]`

### 2. Python Ingestion Service (`python/ingestion/`)

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app, lifespan, `/health`, `/ingest`, `/query` (reload disabled by default) |
| `chunking.py` | `EPAMethodChunker` — TOC-aware recursive splitter; returns `first_page_text` for metadata |
| `embeddings.py` | Provider abstraction: FastEmbed, OpenRouter, Ollama |
| `metadata.py` | LLM-assisted metadata extraction + regex fallback (extracts title from first page) |
| `chroma_client.py` | `ChromaManager` — embedded/remote/cloud client wrapper; batch upsert (1000 chunks) |
| `config.py` | `Settings` via `pydantic-settings` (env + `.env`); includes `reload`, `max_files` |

**Communication:** Rust CLI → HTTP → Python service (port 8001)

**Stability:** `EPA_KG__APP__RELOAD=false` (default) — prevents worker crash on file changes (WinError 10054)

### 3. ChromaDB (Vector Store)

- **Mode:** Embedded (default), HTTP server, or Cloud
- **Collection:** `epa_methods` (EPA method chunks)
- **Distance:** Cosine (`hnsw:space=cosine`)
- **Metadata:** Filterable fields (method_number, section, matrix, analytes)

### 4. PostgreSQL (Relational)

| Table | Phase | Purpose |
|-------|-------|---------|
| `tenants` | 4+ | Lab organizations |
| `users` | 3+ | Lab personnel with roles |
| `lab_documents` | 4 | Uploaded SOPs/QAPs |
| `audit_sessions` | 5 (commercial) | Compliance audits |
| `migrations` | 1+ | SQLx migration tracking |

### 5. Graph Layer

| Phase | Technology | Use Case |
|-------|------------|----------|
| 1 | In-memory `petgraph` | CLI `graph` command |
| 2 | SQLite adjacency table | Persistent cross-references |
| 3+ | Neo4j (optional) | Complex traversals, multi-tenant |

**Edge Types:** `SUPERSEDES`, `REFERENCES`, `CITES_SECTION`, `SHARES_ANALYTE`, `SAME_MATRIX`

### 6. Tauri Frontend (Planned)

- **Stack:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui
- **Targets:** Windows, macOS, Linux, iOS, Android
- **Architecture:** Commands → Rust backend → Python service / DB
- **Offline-first:** ChromaDB bundled, works without network

---

## Data Flow

### Ingestion Pipeline

```
PDF File
    │
    ▼
PyMuPDF (text + TOC + tables)
    │
    ▼
EPAMethodChunker.chunk_pdf()
    │
    ├── TOC-aware sections → chunks
    ├── Regex fallback → chunks
    └── Recursive split (oversized)
    │
    ▼
MetadataExtractor.extract_metadata(first_chunk)
    │
    ▼
EmbeddingProvider.embed_documents(chunks)
    │
    ▼
ChromaManager.upsert(collection, docs, metadata, ids, embeddings)
    │
    ▼
PostgreSQL: log ingestion event (optional)
```

### Query Pipeline

```
User Question
    │
    ▼
EmbeddingProvider.embed_query(question)
    │
    ▼
ChromaManager.query(collection, embedding, top_k)
    │
    ▼
Format sources with citations
    │
    ▼
(Optional) LLM generates synthesized answer
    │
    ▼
Return: { answer, sources[], query_time_ms }
```

---

## Technology Choices

| Category | Choice | Rationale |
|----------|--------|-----------|
| Core Language | Rust | Memory safety, speed, single binary, your preference |
| ML Pipeline | Python | Ecosystem (pdfium, fastembed, LangChain, LLM clients) |
| Vector DB | ChromaDB | Embedded, zero-config, OSS, Tauri-bundlable |
| Relational DB | PostgreSQL | ACID, JSONB, mature, you have it installed |
| Graph | petgraph → SQLite → Neo4j | Progressive complexity |
| Frontend | Tauri v2 + React | Single codebase → desktop + mobile |
| Embeddings | FastEmbed (BGE-small) | Local, no API key, 384-dim, good retrieval |
| LLM | Ollama (local) / OpenRouter (cloud) | User choice, privacy options |
| PDF Parsing | PyMuPDF (fitz) + pdfplumber | Best table/structure extraction |

---

## Security

- **No credentials in code** — all via `.env` + `pydantic-settings` / `config` crate
- **Input validation** — `validator` crate (Rust), Pydantic (Python)
- **SQL injection** — Parameterized queries via `sqlx::query!` / `sqlx::query_as!`
- **CORS** — Configured via `tower-http` with explicit origins
- **Rate limiting** — Planned for Phase 4 (multi-tenant)

---

## Deployment Modes

| Mode | Use Case | Components |
|------|----------|------------|
| **Local Dev** | Development | `cargo run`, `uvicorn`, Docker DBs |
| **Docker Compose** | Local prod-like | All services containerized |
| **Tauri Bundle** | End-user desktop/mobile | Single binary + bundled Chroma + React |
| **Server** | Lab server / CI | Rust binary + Python service + PostgreSQL + Chroma |

---

## Extensibility Points

1. **Embedding Providers** — Implement `EmbeddingProvider` trait
2. **Metadata Extractors** — Implement `MetadataExtractor` trait
3. **Chunking Strategies** — Subclass `EPAMethodChunker`
4. **Graph Backends** — Swap `GraphEngine` implementation
5. **Auth Providers** — OIDC/OAuth2 via `tower-http` middleware