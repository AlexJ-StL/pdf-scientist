# Technology Stack

## Core Technologies

| Layer | Choice | Version | Rationale |
|-------|--------|---------|-----------|
| **Core Language** | **Rust** | 1.80+ | Memory safety, speed, single binary, your preference |
| **ML/Ingestion Pipeline** | **Python** | 3.12+ | PDF parsing, LangChain, embeddings ecosystem is Python-native |
| **Vector Store** | **ChromaDB** | 0.5+ | Zero-config, OSS, local-first, ships in Tauri bundle |
| **Graph Layer (Phase 1)** | **petgraph + SQLite** | — | Dependency-free, embedded, upgradeable to Neo4j |
| **Relational DB** | **PostgreSQL** | 16+ | ACID, JSONB, mature, you have it installed |
| **Frontend / Mobile** | **Tauri v2** | 2.0+ | Single codebase → desktop (Win/Mac/Linux) + iOS + Android |
| **UI Framework** | **React 18 + TypeScript + Tailwind + shadcn/ui** | — | Accessible, modern, your frontend stack |
| **CLI Framework** | **Clap** | 4.5+ | Derive-based, great UX, env/config integration |
| **HTTP Server** | **Axum** | 0.7+ | Tower ecosystem, type-safe, performant |
| **Async Runtime** | **Tokio** | 1.40+ | Industry standard, full-featured |
| **Serialization** | **Serde** | 1.0+ | Derive macros, zero-copy, multiple formats |
| **Config** | **config-rs** + **pydantic-settings** | — | File + env + CLI precedence, validated |
| **Errors** | **thiserror** / **anyhow** | — | Ergonomic error handling |
| **Validation** | **validator** (Rust) / **Pydantic** (Python) | — | Struct-level validation |

## Key Libraries

### Rust (Workspace Dependencies)

```toml
# Core
tokio = { version = "1.40", features = ["full", "tracing"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt", "json"] }
anyhow = "1.0"
thiserror = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
config = { version = "0.14", features = ["toml", "ini"] }
clap = { version = "4.5", features = ["derive", "env"] }
uuid = { version = "1.8", features = ["serde", "v4", "v7"] }
chrono = { version = "0.4", features = ["serde"] }
url = "2.5"

# HTTP / API
axum = "0.7"
tower = { version = "0.4", features = ["util"] }
tower-http = { version = "0.5", features = ["cors", "trace", "normalize-path"] }
hyper = { version = "1.2", features = ["full"] }
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }

# Database
sqlx = { version = "0.8", features = ["runtime-tokio-rustls", "postgres", "uuid", "chrono", "migrate", "json"] }
chromadb = "0.2"

# PDF / Text
pdfium = "0.6"
lopdf = "0.34"
regex = "1.10"
petgraph = "0.6"

# Testing
tempfile = "3.9"
assert_cmd = "2.0"
predicates = "3.0"
```

### Python (Requirements)

```txt
# API
fastapi==0.111.0
uvicorn==0.30.0
pydantic==2.7.4
pydantic-settings==2.3.3
python-dotenv==1.0.1

# PDF Processing
pymupdf==1.24.7          # fitz - text, TOC, tables
pdfplumber==0.11.4       # table extraction

# Embeddings
fastembed==0.4.1         # local BGE, E5, etc.
httpx==0.27.0            # OpenRouter/Ollama HTTP client

# ML / NLP
tiktoken==0.7.0          # token counting
numpy==1.26.4

# Database
chromadb==0.5.5          # vector store
psycopg2-binary==2.9.9   # PostgreSQL (future)

# Testing
pytest==8.2.2
pytest-asyncio==0.23.3
pytest-cov==5.0.0
```

## Environment Setup

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js 20+ (for Tauri UI - when ready)
# Via fnm/nvm/volta or system package manager

# Install PostgreSQL 16+
# macOS: brew install postgresql@16
# Linux: apt install postgresql-16
# Windows: winget install PostgreSQL.PostgreSQL

# Install Ollama (optional, for local LLMs)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Database Configuration

### PostgreSQL (Relational)

```sql
-- Run via sqlx migrate or manually
CREATE DATABASE epa_kg;

-- Tables created via sqlx migrations (crates/epa-kg-api/migrations/)
-- tenants, users, lab_documents, audit_sessions
```

### ChromaDB (Vector)

| Mode | Connection | Use Case |
|------|------------|----------|
| **Embedded** | `PersistentClient(path="./data/chroma")` | Dev, single-user, Tauri bundle |
| **Server** | `HttpClient(host="127.0.0.1", port=8000)` | Multi-user, shared |
| **Cloud** | `CloudClient(api_key, tenant, database)` | Production, zero-ops |

### SQLite (Graph - Phase 1)

```sql
-- Simple adjacency list
CREATE TABLE citation_edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence REAL,
    context TEXT,
    PRIMARY KEY (source_id, target_id, edge_type)
);
```

## Common Commands

```bash
# Rust workspace
cargo build --workspace                 # Debug build
cargo build --release --workspace       # Release build (LTO, strip)
cargo test --workspace                  # All tests
cargo fmt --all                         # Format
cargo clippy --workspace -- -D warnings # Lint
cargo audit                             # Security audit

# Python ingestion
cd python/ingestion
uv sync                                 # Install deps
uv run python -m main                   # Run service
uv run pytest -v --cov=ingestion        # Test + coverage
uv run ruff check . --fix               # Lint + fix
uv run ruff format .                    # Format

# CLI (from workspace root)
cargo run --bin epa-kg -- ingest --pdf-dir ./epa-methods
cargo run --bin epa-kg -- query "How do I prepare soil for 8270E?"
cargo run --bin epa-kg -- graph --method 8270E --depth 2
cargo run --bin epa-kg -- serve --port 8080

# Tauri (when UI exists)
cargo tauri dev                         # Dev mode (hot reload)
cargo tauri build                       # Production bundle
```

## API Keys Required

| Service | Key | Used For | Required? |
|---------|-----|----------|-----------|
| **OpenRouter** | `OPENROUTER_API_KEY` | Embeddings (OpenRouter), LLM metadata, LLM answers | No (local defaults) |
| **ChromaDB Cloud** | `CHROMADB_API_KEY` | Managed vector DB | No (local default) |
| **PostgreSQL** | Connection string | Relational data | Yes (Phase 3+) |

**All keys via `.env` (never committed):**
```bash
# Embeddings
EPA_KG__EMBEDDING__PROVIDER=openrouter
EPA_KG__EMBEDDING__OPENROUTER__API_KEY=sk-or-v1-...

# LLM Metadata
EPA_KG__LLM__PROVIDER=openrouter
EPA_KG__LLM__OPENROUTER__API_KEY=sk-or-v1-...

# Or use Ollama (no key needed)
EPA_KG__EMBEDDING__PROVIDER=ollama
EPA_KG__LLM__PROVIDER=ollama
```