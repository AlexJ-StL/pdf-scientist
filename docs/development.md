# Development Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Rust | 1.80+ | `rustup` |
| Python | 3.12+ | `uv` (recommended) or system |
| PostgreSQL | 16+ | Docker or native |
| Ollama | Latest | Optional (local LLM) |
| Node.js | 20+ | For Tauri UI (planned) |

---

## Environment Setup

```bash
# 1. Clone
git clone https://github.com/AlexJ-StL/epa-knowledge-graph
cd epa-knowledge-graph

# 2. Rust toolchain
rustup update stable
rustup component add rustfmt clippy

# 3. Python deps
cd python/ingestion
uv sync
cd ../..

# 4. Environment
cp .env.example .env
# Edit .env with your settings

# 5. PostgreSQL (Docker)
docker run -d \
  --name epa-kg-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=epa_kg \
  -p 5432:5432 \
  postgres:16

# 6. Run migrations (when available)
# cargo install sqlx-cli
# sqlx migrate run
```

---

## Running Services

### Python Ingestion Service

```bash
cd python/ingestion
uv run python -m main
# Or with auto-reload
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8001

# Health check
curl http://127.0.0.1:8001/health
```

### Rust CLI

```bash
# Build
cargo build --workspace

# Run CLI
cargo run --bin epa-kg -- --help

# Commands
cargo run --bin epa-kg -- ingest --pdf-dir ./epa-methods
cargo run --bin epa-kg -- query "soil preparation 8270E"
cargo run --bin epa-kg -- graph --method 8270E --depth 2
cargo run --bin epa-kg -- serve --port 8080
```

### Rust API Server

```bash
# From epa-kg-ingest (current implementation)
cargo run --bin epa-kg -- serve --port 8080

# Future: dedicated binary
cargo run --bin epa-kg-api
```

### Tauri App (Planned)

```bash
cd crates/epa-kg-tauri
cargo tauri dev
```

---

## Testing

### Rust

```bash
# All workspace tests
cargo test --workspace

# Specific crate
cargo test -p epa-kg-core
cargo test -p epa-kg-graph

# With output
cargo test --workspace -- --nocapture

# Integration tests (require services)
cargo test --workspace --test integration
```

### Python

```bash
cd python/ingestion

# All tests
uv run pytest

# With coverage
uv run pytest --cov=ingestion --cov-report=term-missing

# Specific test
uv run pytest tests/test_ingestion.py::TestChunker::test_token_counting -v

# Async tests
uv run pytest -v --asyncio-mode=auto
```

### Pre-commit Checks

```bash
# Rust
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo audit

# Python
cd python/ingestion
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv run pytest
```

---

## Project Structure

```
pdf-scientist/
├── Cargo.toml                    # Workspace root
├── crates/
│   ├── epa-kg-core/              # Shared: config, errors, types
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── config.rs         # Settings (env + files)
│   │       ├── error.rs          # Error enum + Result<T>
│   │       └── lib.rs
│   ├── epa-kg-ingest/            # CLI binary + Python bridge
│   │   ├── Cargo.toml
│   │   └── src/main.rs           # clap CLI, HTTP to Python
│   ├── epa-kg-api/               # Axum HTTP API
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── state.rs          # AppState (DI container)
│   │       ├── routes.rs         # Router + routes
│   │       ├── handlers.rs       # Request handlers
│   │       └── error.rs          # API error types
│   ├── epa-kg-graph/             # Citation graph
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── models.rs         # EdgeType, CitationEdge
│   │       └── engine.rs         # GraphEngine (petgraph)
│   └── epa-kg-tauri/             # Tauri v2 entry
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       ├── build.rs
│       └── src/main.rs           # Tauri commands
├── python/
│   └── ingestion/                # FastAPI service
│       ├── main.py
│       ├── chunking.py
│       ├── embeddings.py
│       ├── metadata.py
│       ├── chroma_client.py
│       ├── config.py
│       ├── pyproject.toml
│       └── tests/
```

---

## Adding a New Crate

1. Create directory: `mkdir crates/epa-kg-new`
2. Add `Cargo.toml` with `epa-kg-core` dependency
3. Add to workspace `Cargo.toml` members
4. Implement `lib.rs` with public API
5. Add tests in `tests/` or `src/`
6. Update documentation

---

## Adding a New Embedding Provider

1. Implement `EmbeddingProvider` trait in `python/ingestion/embeddings.py`
2. Add factory case in `get_embedding_provider()`
3. Add config fields in `python/ingestion/config.py`
4. Add environment variable docs in `.env.example`
5. Write tests

---

## Adding a New Metadata Extractor

1. Implement `MetadataExtractor` trait in `python/ingestion/metadata.py`
2. Add factory case in `get_metadata_extractor()`
3. Add config fields
4. Write tests with mocked LLM responses

---

## Debugging

### Rust

```bash
# Enable debug logging
RUST_LOG=debug cargo run --bin epa-kg -- ingest ...

# Specific crate
RUST_LOG=epa_kg_ingest=debug cargo run ...

# Backtraces
RUST_BACKTRACE=1 cargo run ...
```

### Python

```bash
# Debug logging
LOG_LEVEL=debug uv run python -m main

# Interactive debugging
uv run python -m pdb main.py

# Test single function
uv run python -c "from chunking import EPAMethodChunker; c=EPAMethodChunker(); print(c.count_tokens('test'))"
```

### ChromaDB

```bash
# List collections
python -c "
import chromadb
c = chromadb.PersistentClient('./data/chroma')
print([col.name for col in c.list_collections()])
"

# Inspect collection
python -c "
import chromadb
c = chromadb.PersistentClient('./data/chroma')
col = c.get_collection('epa_methods')
print(f'Count: {col.count()}')
print(col.peek(3))
"
```

---

## Code Style

### Rust

- Edition 2021
- `rustfmt` (default config)
- `clippy` with `-D warnings`
- `thiserror` for error types
- `anyhow` for application errors
- `tracing` for logging

### Python

- `ruff` for linting + formatting (replaces black/isort/flake8)
- `mypy --strict` for type checking
- `pydantic` v2 for settings/validation
- `async`/`await` throughout
- Type hints on all public functions

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(ingest): add TOC-aware chunking for EPA methods
fix(api): handle empty query results gracefully
docs(readme): update quickstart for Python service
test(graph): add golden-file tests for cross-ref extraction
refactor(core): extract Settings into separate module
chore(deps): update tokio to 1.40
```

---

## CI Pipeline (Planned)

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo fmt --check
      - run: cargo clippy --workspace -- -D warnings
      - run: cargo test --workspace
      - run: cargo audit
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd python/ingestion && uv sync
      - run: cd python/ingestion && uv run ruff check .
      - run: cd python/ingestion && uv run pytest
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t epa-kg .
      - run: trivy image epa-kg
```

---

## Release Process

1. Update `CHANGELOG.md`
2. Update version in `Cargo.toml` (workspace)
3. Tag: `git tag v0.1.0`
4. Push: `git push origin v0.1.0`
5. GitHub Actions builds binaries + publishes
6. Create GitHub Release with artifacts

---

## Useful Commands

```bash
# Clean build artifacts
cargo clean

# Check for unused deps
cargo machete

# Generate docs
cargo doc --workspace --no-deps --open

# Update dependencies
cargo update

# Python: upgrade deps
cd python/ingestion && uv lock --upgrade

# Database: create migration
sqlx migrate add -r description_here

# Database: run migrations
sqlx migrate run
```