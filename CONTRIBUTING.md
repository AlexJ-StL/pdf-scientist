# Contributing to EPA Knowledge Graph

Thank you for your interest in contributing! This project follows a standard open-source workflow with a few specific conventions.

## Development Setup

### Prerequisites
- **Rust 1.80+** (via `rustup`)
- **Python 3.12+** (with `uv` for dependency management)
- **Node.js 20+** (for Tauri frontend - planned)
- **PostgreSQL 16+** (local or Docker)
- **Ollama** (optional, for local LLM metadata extraction)

### Quick Start
```bash
# 1. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# 2. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Clone and enter
git clone https://github.com/AlexJ-StL/epa-knowledge-graph
cd epa-knowledge-graph

# 4. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 5. Install Python deps
cd python/ingestion && uv sync

# 6. Build Rust workspace
cargo build --workspace

# 7. Run tests
cargo test --workspace
cd python/ingestion && uv run pytest
```

## Code Style

### Rust
- **Format:** `cargo fmt --all` (rustfmt, edition 2021)
- **Lint:** `cargo clippy --workspace -- -D warnings`
- **Audit:** `cargo audit` (security vulnerabilities)
- **Error handling:** `thiserror` for error types, `anyhow` for application errors
- **Logging:** `tracing`

### Python
- **Format + Lint:** `ruff format .` + `ruff check . --fix` (replaces black/isort/flake8)
- **Type check:** `mypy --strict` (where applicable)
- **Validation:** `pydantic` v2 for settings/validation
- **Async throughout**

### TypeScript/React (UI - planned)
- **Format:** `prettier --write .`
- **Lint:** `eslint . --ext ts,tsx`
- **Type check:** `tsc --noEmit`

### Pre-commit Hook
```bash
# Install once
cargo install cargo-husky
cargo husky install

# Runs on every commit:
# - cargo fmt --check
# - cargo clippy
# - ruff check
# - prettier --check (when UI exists)
```

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[body]

[footer]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `style` — Formatting, no logic change
- `refactor` — Code restructure, no behavior change
- `perf` — Performance improvement
- `test` — Add or modify tests
- `chore` — Build, deps, tooling
- `ci` — CI/CD changes

**Scopes:** `core`, `ingest`, `api`, `graph`, `tauri`, `ui`, `python`, `docs`, `deps`

**Examples:**
```
feat(ingest): add TOC-aware PDF chunking strategy
fix(api): handle empty query results gracefully
docs(readme): update quickstart for Python service
test(graph): add golden-file tests for cross-ref extraction
refactor(core): extract Settings into separate module
```

**DCO Sign-off required:**
```bash
git commit -s -m "feat(ingest): add TOC-aware PDF chunking"
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `main`: `git checkout -b feat/my-feature`
3. **Make changes** with clear, atomic commits
4. **Run all checks locally:**
   ```bash
   cargo fmt --check && cargo clippy --workspace -D warnings
   cd python/ingestion && uv run ruff check . && uv run pytest
   ```
5. **Open PR** against `main` with:
   - Clear title (Conventional Commit format)
   - Description of changes and motivation
   - Link to any related issue
6. **DCO Sign-off** required on all commits
7. **CI must pass** (GitHub Actions: test, lint, audit, build)
8. **Review** — maintainers will review; address feedback
9. **Merge** — squash and merge (maintainers only)

## Issue Reporting

- **Bug reports:** Use the bug template; include reproduction steps, environment, logs
- **Feature requests:** Use the feature template; explain use case and acceptance criteria
- **Security issues:** Email privately (see SECURITY.md) — do not file public issues

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see LICENSE).

**Commercial module (`epa-audit-suite`)** is proprietary. Contact for licensing.

---

## Additional Resources

- [Development Guide](docs/development.md) — Detailed setup, testing, debugging
- [Architecture](docs/architecture.md) — System design, components, data flow
- [API Reference](docs/api.md) — REST endpoints, CLI commands, Tauri commands
- [Ingestion Guide](docs/ingestion-guide.md) — PDF processing, chunking, embeddings, metadata
- [Phase 1 Plan](docs/phase-1-ingestion.md) — Current phase deliverables and acceptance criteria
