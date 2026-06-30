# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and documentation
- Formal project plan: `EPA-Knowledge-Graph-Plan.md`
- MIT License
- Contributing guidelines
- `.gitignore` for Rust, Python, Tauri, Node, data files
- `.env.example` template
- README with architecture overview and roadmap

### Preserved
- Historical Kiro steering docs in `.docs/.kiro/steering/`
- Original planning documents in `.docs/`
- Legacy `process_pdf.py` and `requirements.txt` for reference

---

## [0.1.0] - TBD (Phase 1 Release)

### Added
- Rust workspace with crates: `epa-kg-core`, `epa-kg-ingest`, `epa-kg-api`, `epa-kg-graph`, `epa-kg-tauri`
- Python ingestion service (FastAPI) with TOC-aware PDF chunking
- ChromaDB embedded vector store integration
- CLI commands: `ingest`, `query`
- Unit test suite (≥80% coverage)
- Dockerfile and docker-compose.yml

### Changed
- N/A (initial release)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

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