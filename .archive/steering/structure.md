# Project Structure

## Root Directory Layout

```
epa-knowledge-graph/
├── Cargo.toml                                 # Rust workspace root
├── crates/                                        # Rust crates (5)
│   ├── epa-kg-core/                         # Shared types, config, errors
│   ├── epa-kg-ingest/                      # CLI binary + Python bridge
│   ├── epa-kg-api/                           # Axum HTTP API
│   ├── epa-kg-graph/                      # Citation graph engine
│   └── epa-kg-tauri/                           # Tauri v2 entry point
├── python/
│   └── ingestion/                                # FastAPI ingestion service
│       ├── main.py
│       ├── chunking.py
│       ├── embeddings.py
│       ├── metadata.py
│       ├── chroma_client.py
│       ├── config.py
│       ├── pyproject.toml
│       └── tests/
├── docs/                                           # Documentation (new)
│   ├── architecture.md
│   ├── api.md
│   ├── phase-1-ingestion.md
│   ├── development.md
│   └── ingestion-guide.md
├── .docs/                                         # Historical/legacy docs
│   ├── steering/                               # Project steering configs
│   ├── EPA-Knowledge-Graph-Plan.md
│   └── *.txt                                         # Legacy planning docs
├── docker/                                     # Dockerfiles (planned)
├── .github/workflows/                 # CI/CD (planned)
├── .env.example                           # Environment template
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── DEVELOPMENT.md                # Symlink to docs/development.md
├── LICENSE
├── .gitignore
└── target/                                        # Rust build artifacts (gitignored)
```

---

## Key Files

### Rust Workspace

| File | Purpose |
|------|---------|
| `Cargo.toml` | Workspace config, shared deps, profiles |
| `crates/epa-kg-core/src/config.rs` | Unified Settings (env + files) |
| `crates/epa-kg-core/src/error.rs` | Typed Error enum + Result<T> |
| `crates/epa-kg-ingest/src/main.rs` | CLI: ingest, query, graph, serve |
| `crates/epa-kg-api/src/handlers.rs` | Axum request handlers |
| `crates/epa-kg-graph/src/engine.rs` | GraphEngine (petgraph) |
| `crates/epa-kg-tauri/src/main.rs` | Tauri commands |

### Python Service

| File | Purpose |
|------|---------|
| `python/ingestion/main.py` | FastAPI app, lifespan, endpoints |
| `python/ingestion/chunking.py` | EPAMethodChunker (TOC-aware) |
| `python/ingestion/embeddings.py` | Provider abstraction (FastEmbed/Ollama/OpenRouter) |
| `python/ingestion/metadata.py` | LLM metadata extraction |
| `python/ingestion/chroma_client.py` | ChromaManager (embedded/server/cloud) |
| `python/ingestion/config.py` | Pydantic Settings (env + .env) |

### Legacy (Preserved in `.docs/`)

| File | Note |
|------|------|
| `process_pdf.py` | Original MongoDB + OpenAI + LangChain |
| `requirements.txt` | Original deps |
| `.docs/PDF-Processor-MongoDB*.txt` | MongoDB connection examples |
| `.docs/Plan for Building a Local Semantic Vector Database App for PDF Files.txt` | 6-phase plan |
| `.docs/Reply to Questions and Vision on pdf-Scientist 06292026.txt` | Vision alignment |

---

## Documentation Structure

```
docs/
├── architecture.md                     # System architecture, data flow, tech choices
├── api.md                                      # REST API, CLI, Tauri commands reference
├── phase-1-ingestion.md           # Detailed Phase 1 spec + acceptance criteria
├── development.md                   # Dev setup, testing, debugging, code style
└── ingestion-guide.md                  # Ingestion Guide (this file)
```

---

## Development Conventions

- **Config:** Unified via `epa-kg-core::config::Settings` (Rust) + `python/ingestion/config.py` (Python)
- **Logging:** `tracing` (Rust) + `logging` (Python) — `RUST_LOG` / `LOG_LEVEL`
- **Errors:** `thiserror` (Rust) / Pydantic + custom exceptions (Python)
- **Testing:** `cargo test --workspace` + `pytest python/ingestion/tests/`
- **Formatting:** `cargo fmt --all` / `ruff format .`
- **Linting:** `cargo clippy --workspace -D warnings` / `ruff check .`
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
- **Sign-off:** `git commit -s` (DCO required)

---

## Ignored Files

Standard ignores in `.gitignore`:
- Rust: `target/`, `Cargo.lock` (workspace root only)
- Python: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`
- Node: `node_modules/`, `dist/`
- Tauri: `src-tauri/target/`, `src-tauri/gen/`
- Data: `data/`, `chroma/`, `*.sqlite`, `*.db`
- Env: `.env`, `.env.local`, `.env.*.local`
- IDE: `.vscode/`, `.idea/`, `*.swp`
- OS: `.DS_Store`, `Thumbs.db`
- Logs: `*.log`, `logs/`
- Coverage: `.coverage`, `htmlcov/`
- Docs build: `docs/_build/`, `site/`
- Temp: `*.tmp`, `.tmp/`, `temp/`