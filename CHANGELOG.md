# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Phase 1 In Progress

### Added
- Rust workspace with 5 crates: `epa-kg-core`, `epa-kg-ingest`, `epa-kg-api`, `epa-kg-graph`, `epa-kg-tauri`
- Shared configuration system (`epa-kg-core`) with file + env precedence via `config-rs`
- Unified error types with `thiserror` and `anyhow` integration
- CLI binary (`epa-kg`) with commands: `ingest`, `query`, `graph`, `serve`
- Python FastAPI ingestion service (`python/ingestion/`) with:
  - TOC-aware recursive PDF chunking (`EPAMethodChunker`)
  - Multi-provider embedding abstraction (FastEmbed, OpenRouter, Ollama)
  - LLM-assisted metadata extraction (OpenRouter, Ollama) with regex fallback
  - ChromaDB manager supporting embedded, server, and cloud modes
  - REST endpoints: `/health`, `/ingest`, `/query`
- Citation graph engine (`epa-kg-graph`) using `petgraph` with 5 edge types
- Tauri v2 entry point (`epa-kg-tauri`) with placeholder commands
- Comprehensive documentation in `docs/`:
  - `architecture.md` — System architecture, data flow, component details
  - `api.md` — REST API reference, CLI commands, Tauri commands
  - `phase-1-ingestion.md` — Detailed Phase 1 specification
  - `development.md` — Development setup, testing, debugging guide
  - `ingestion-guide.md` — Ingestion pipeline deep dive
- `SECURITY.md` — Security policy, vulnerability reporting, threat model
- `.env.example` with all configuration options documented
- MIT License

### Changed
- Migrated from legacy MongoDB + OpenAI + PyPDF2 stack to ChromaDB + FastEmbed/Ollama/OpenRouter + PyMuPDF/pdfplumber
- Renamed project from `pdf-scientist` → `epa-knowledge-graph`
- Moved legacy planning docs to `.docs/` for historical preservation
- Moved `.docs/.kiro/steering` to `.archive/steering`
- Deleted `.docs/.kiro` (empty folder after moving `.docs/.kiro/steering`
- Renamed `.docs` to `.archive` for better distinction between `.docs` and `docs`
- Copied the new Project Structure into the `## Project Structure` section in the `README.md`
- Legacy Project Structure labeled `old-project-structure_07092026.txt` added to `.archive`

### Preserved
- Historical Kiro steering docs in `.docs/.kiro/steering/`
- Original planning documents in `.docs/` (`EPA-Knowledge-Graph-Plan.md`, etc.)
- Legacy `process_pdf.py` and `requirements.txt` for reference

### Infrastructure
- `.gitignore` covering Rust, Python, Tauri, Node, data, env, IDE, OS artifacts
- Cargo workspace with shared dependencies and optimized release profile (LTO, strip)
- Python `uv` lockfile for reproducible dependencies

---

## [0.1.0] - TBD (Phase 1 Release)

### Target: Phase 1 Complete

**Planned Additions:**
- Full test coverage (≥80%): `cargo test --workspace` + `pytest python/ingestion/tests/`
- Dockerfile + `docker-compose.yml` (PostgreSQL, ChromaDB, API, Ingestion)
- GitHub Actions CI: fmt, clippy, audit, test, trivy scan
- `epa-kg query` returns synthesized answers with citations
- Idempotent ingestion with file-hash change detection
- Configuration validation on startup

**Planned Fixes:**
- Complete `epa-kg graph` CLI implementation
- Complete `epa-kg serve` Axum server implementation
- ChromaDB collection management (list, delete, backup)

---

## Template for Future Releases

## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature descriptions

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be-removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security patches