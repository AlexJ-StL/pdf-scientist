# Contributing

## Development Setup

### Prerequisites

- **Rust** 1.80+ ([rustup](https://rustup.rs/))
- **Python** 3.12+ (project minimum; tested on 3.12.6)
- **uv** (Python package manager)
- **Node.js** 18+ (for Tauri frontend, Phase 3+)

### Clone and Install

```bash
git clone https://github.com/AlexJ-StL/epa-knowledge-graph
cd epa-knowledge-graph

# Install Rust dependencies
cargo fetch

# Install Python dependencies
cd python/ingestion
uv pip install -e ".[dev,test]"
cd ../..
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `OPENROUTER_API_KEY` — for metadata extraction (optional)
- `OLLAMA_HOST` — local LLM endpoint (default: `http://localhost:11434`)

## Running Tests

### Python

```bash
# Run all Python tests with coverage
make test-python

# Or directly with Python 3.12
\\\"C:\\Users\\AlexJ\\AppData\\Local\\Programs\\Python\\Python312\\python.exe\\\" -m pytest python/ingestion/tests/ --cov=python/ingestion -v
```

### Rust

```bash
# Run all Rust tests
make test-rust

# Run clippy lints
make test-rust-clippy

# Or directly
cargo test --workspace --verbose
cargo clippy --workspace -- -D warnings
```

### All Tests

```bash
make test
```

## Code Quality

### Python
- **Formatter:** `ruff format .`
- **Linter:** `ruff check .`
- **Type checking:** `mypy python/ingestion/`

### Rust
- **Formatter:** `cargo fmt --all -- --check`
- **Linter:** `cargo clippy --workspace -- -D warnings`
- **Tests:** `cargo test --workspace`

## CI/CD

GitHub Actions runs on every push and pull request:

1. **Python tests** with coverage reporting
2. **Rust tests** across all crates
3. **Rust clippy** with strict warnings-as-errors
4. **Coverage upload** to Codecov (optional, requires `CODECOV_TOKEN`)

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add graph traversal for citation chains
fix: handle missing TOC in PDF parsing
test: add unit tests for metadata fallback
docs: update README with Phase 2 roadmap
refactor: extract chunk_pdf into smaller functions
```

DCO sign-off is required for all commits:

```bash
git commit -s -m "feat: add graph traversal for citation chains"
```

## Project Structure

```
epa-knowledge-graph/
├── Cargo.toml                     # Rust workspace root
├── crates/
│   ├── epa-kg-core/               # Shared types, config, errors
│   ├── epa-kg-ingest/            # CLI binary + Python bridge
│   ├── epa-kg-api/                # Axum HTTP API
│   ├── epa-kg-graph/              # Citation graph engine
│   └── epa-kg-tauri/              # Tauri v2 entry point
├── python/
│   └── ingestion/                 # FastAPI ingestion service
│       ├── main.py
│       ├── chunking.py
│       ├── embeddings.py
│       ├── metadata.py
│       ├── chroma_client.py
│       ├── config.py
│       ├── pyproject.toml
│       └── tests/
│           ├── unit/
│           ├── integration/
│           └── test_ingestion.py
├── .github/workflows/ci.yml       # CI/CD pipeline
└── Makefile                       # Dev shortcuts
```

## Test Strategy

- **Python:** Target >95% coverage. Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- **Rust:** Target >90% coverage for core crates (`epa-kg-core`, `epa-kg-graph`, `epa-kg-api`). CLI integration code is excluded from coverage gates.
- **Tests must pass** before merging. CI enforces this automatically.

## Questions?

Open an issue at https://github.com/AlexJ-StL/epa-knowledge-graph/issues.
