# EPA Knowledge Graph / AI Lab Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/Rust-1.80+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-blueviolet.svg)](https://tauri.app/)

> **An open-source knowledge graph and AI assistant for environmental laboratories to dynamically reference EPA methods, SOPs, QAPs, and regulatory standards.**

## Vision

Environmental labs juggle hundreds of EPA methods (SW-846, 40 CFR, etc.), each cross-referencing others, with matrix-specific exceptions, analyte lists, and revision histories. Bench chemists need answers *now* — not after digging through PDFs.

This project builds:
1. **A semantic vector store** of EPA methods with rich metadata (method #, section, matrix, analytes, revision, supersession chain)
2. **A citation graph** linking methods → sections → referenced methods
3. **A natural-language query interface** (CLI + Tauri desktop/mobile app) that answers with source citations
4. **Lab document ingestion** (SOPs, QAPs) for tenant-isolated hybrid search (EPA + internal)

**Commercial tier (separate repo):** `epa-audit-suite` — structured audit workflows, gap analysis, EPA-format report generation for accreditation bodies.

---

## Quickstart (Coming Phase 1)

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Python 3.12+ and uv
pip install uv

# Clone and build
git clone https://github.com/AlexJ-StL/epa-knowledge-graph
cd epa-knowledge-graph

# Set up environment
cp .env.example .env
# Edit .env with your paths / API keys

# Start Python ingestion service (in separate terminal)
cd python/ingestion && uv run python -m main

# Ingest your EPA method PDFs
cargo run --bin epa-kg -- ingest --pdf-dir ./epa-methods

# Query from CLI
cargo run --bin epa-kg -- query "How do I prepare soil samples for 8270E?"

# Run the Tauri app (desktop + mobile)
cargo tauri dev
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  EPA PDFs       │────▶│  Python Ingestion│────▶│  ChromaDB       │
│  (local dir)    │     │  Service         │     │  (embedded)     │
└─────────────────┘     │  - pdfium parse  │     │  - vectors      │
                        │  - TOC-aware     │     │  - metadata     │
                        │  - fastembed     │     └────────┬────────┘
                        │    (BGE-small)   │              │
                        └────────┬─────────┘              │
                                 │                        │
                                 ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Lab SOPs/QAPs  │────▶│  Rust Core       │◀───▶│  PostgreSQL     │
│  (tenant upload)│     │  (Axum API)      │     │  (tenants,      │
└─────────────────┘     │  - query API     │     │   users, audit) │
                        │  - graph engine  │     └─────────────────┘
                        └────────┬─────────┘
                                 │
                         ┌────────▼─────────┐
                         │  Tauri v2 App    │
                         │  (React + TS)    │
                         │  Desktop + iOS   │
                         │  + Android       │
                         └──────────────────┘
```

**Tech Stack:**
- **Core API/CLI:** Rust (Axum, Tokio, Serde, Clap)
- **Ingestion/ML:** Python 3.12 (FastAPI, pdfium, pdfplumber, fastembed)
- **Vector DB:** ChromaDB (embedded, zero-config)
- **Relational DB:** PostgreSQL (tenants, users, audit logs)
- **Graph Layer:** SQLite adjacency (Phase 1) → Neo4j (Phase 2+)
- **Frontend:** Tauri v2 + React 18 + TypeScript + Tailwind + shadcn/ui (planned)
- **Local LLM:** Ollama / LM Studio (metadata extraction, optional)

---

## Project Structure

```
epa-knowledge-graph/
├── Cargo.toml                    # Rust workspace
├── crates/
│   ├── epa-kg-core/              # Shared types, config, errors
│   ├── epa-kg-ingest/            # CLI + Python bridge
│   ├── epa-kg-api/               # Axum HTTP API
│   ├── epa-kg-graph/             # Citation graph engine
│   └── epa-kg-tauri/             # Tauri entry point
├── python/
│   └── ingestion/                # FastAPI service
│       ├── main.py
│       ├── chunking.py           # TOC-aware recursive splitter
│       ├── embeddings.py         # fastembed / OpenRouter / Ollama
│       ├── metadata.py           # LLM-assisted extraction
│       ├── chroma_client.py
│       ├── config.py
│       └── tests/
├── docs/                         # Documentation
│   ├── architecture.md
│   ├── api.md
│   ├── contributing.md
│   ├── development.md
│   ├── ingestion-guide.md
│   └── phase-1-ingestion.md
├── docker/                       # Docker config (planned)
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/workflows/            # CI/CD (planned)
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── DEVELOPMENT.md
└── .env.example
```

---

## Phase Roadmap

| Phase | Focus | Timeline | Deliverable |
|-------|-------|----------|-------------|
| **1** | Document Ingestion Pipeline | Weeks 1-3 | CLI: `ingest` + `query`; Chroma persistence; unit tests |
| **2** Citation Graph | Weeks 4-5 | Cross-reference extraction; `graph` CLI; metadata enrichment |
| **3** Tauri Lab Assistant | Weeks 6-9 | Dark-mode chat UI; source citations; method browser; mobile build |
| **4** Lab Document Ingestion | Weeks 10-12 | Multi-tenant API; SOP/QAP upload; hybrid EPA+lab query |
| **5** Audit Suite (commercial) | Separate repo | Checklists, gap analysis, EPA-format reports |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style (rustfmt, clippy, black, ruff)
- Commit convention (Conventional Commits)
- PR process (DCO sign-off required)

---

## License

MIT — see [LICENSE](LICENSE).

**Commercial module (`epa-audit-suite`)** is proprietary. Contact for licensing.

---

## Contact

- **Author:** Alex Johnson
- **GitHub:** [@AlexJ-StL](https://github.com/AlexJ-StL)
- **Issues:** [GitHub Issues](https://github.com/AlexJ-StL/epa-knowledge-graph/issues)

---

*Built for the chemists who keep our water clean.*