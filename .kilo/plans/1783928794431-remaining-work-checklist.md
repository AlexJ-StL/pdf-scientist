# EPA Knowledge Graph — Remaining Work Checklist

**Generated:** 2026-07-14  
**Source Documents:** `.archive/EPA-Knowledge-Graph-Plan.md`, `.archive/product.md`, `.archive/tech.md`, `.archive/structure.md`  
**Current Status:** Phase 1 ~90% complete; Phases 2-5 not started

---

## Legend
- ✅ **Done** — Implemented, tested, passing
- 🔄 **In Progress** — Partially implemented
- ⬜ **Not Started** — No code yet
- ⚠️ **Gap** — Plan mentions it but no code exists
- 📋 **Missing** — Not in plans but needed

---

## Phase 1: Document Ingestion Pipeline (Weeks 1-3)

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 1.1 | `epa-kg ingest` CLI command | ✅ | `epa-kg-ingest/src/main.rs` implements `ingest` subcommand |
| 1.2 | PDF → structured chunks | ✅ | `chunking.py` implements TOC-aware + regex fallback + recursive split |
| 1.3 | Embedding generation | ✅ | `embeddings.py` has FastEmbed, OpenRouter, Ollama providers |
| 1.4 | ChromaDB persistence | ✅ | `chroma_client.py` embedded mode working; survives restarts |
| 1.5 | `epa-kg query` CLI command | ✅ | `epa-kg-ingest/src/main.rs` implements `query` subcommand |
| 1.6 | Unit tests ≥ 80% coverage | ✅ | Python 96%, Rust 78% (core crates >92%) |
| 1.7 | Dockerfile | ⚠️ | Plan mentions multi-stage; no `Dockerfile` or `docker-compose.yml` exists |
| 1.8 | `.env.example` with all vars | ✅ | Exists at root |
| 1.9 | Idempotent re-ingest (hash-based) | ⚠️ | Code checks existing chunk IDs but no file-hash tracking yet |
| 1.10 | Table extraction (pdfplumber) | ❌ | `extract_tables` config exists but no implementation in `chunking.py` |
| 1.11 | Figure/caption extraction | ❌ | Not implemented |
| 1.12 | File-hash change detection | ❌ | No MD5/SHA tracking of PDFs for incremental updates |
| 1.13 | Max file size enforcement | ✅ | `max_file_size_mb` enforced in `main.py` |

### Phase 1 Gaps Summary
| Missing | Priority |
|---------|----------|
| Dockerfile / docker-compose.yml | High |
| Table extraction (pdfplumber) | Medium |
| File-hash based change detection | Medium |
| Figure/caption extraction | Low |

---

## Phase 2: Reference & Cross-Link Engine (Weeks 4-5) — ⬜ NOT STARTED

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 2.1 | Reference extractor (regex + LLM) | ⬜ | Plan: find "Method 3500C", "Section 4.2 of 8270E" |
| 2.2 | Graph store (SQLite edges table) | ⬜ | Schema: `(source_chunk_id, target_method, target_section, relation_type)` |
| 2.3 | `graph` CLI command | ⬜ | `epa-kg graph --method 8270E --depth 2` → ASCII tree |
| 2.4 | Metadata enrichment from cross-refs | ⬜ | Auto-populate `supersedes`, `references`, `matrix`, `analytes` |
| 2.5 | Golden-file tests for cross-refs | ⬜ | Test known method cross-references |
| 2.6 | Relation types enum | ⬜ | `SUPERSEDES`, `REFERENCES`, `CITES_SECTION`, `SHARES_ANALYTE`, `SAME_MATRIX` |

### Phase 2 Gaps
- **No code exists** for any Phase 2 deliverable
- Graph engine (`epa-kg-graph`) exists but only has basic `GraphEngine` with `add_node`/`add_edge` — no reference extraction or cross-ref logic
- SQLite persistence for edges not implemented
- CLI `graph` subcommand not added to `epa-kg-ingest`

---

## Phase 3: Lab Assistant UI — Tauri v2 (Weeks 6-9) — ⬜ NOT STARTED

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 3.1 | Tauri project scaffold | ⬜ | `cargo tauri init`; builds for Linux, Windows, macOS, iOS, Android |
| 3.2 | Chat interface | ⬜ | Streaming responses, markdown rendering, copy-to-clipboard |
| 3.3 | Source citations in answers | ⬜ | Every answer shows chunk references with method/section links |
| 3.4 | Method browser | ⬜ | Tree view: Method → Sections → Chunks |
| 3.4 | Offline-first | ⬜ | Chroma bundled; works without network (except LLM calls) |
| 3.5 | Settings panel | ⬜ | Embedding provider, LLM endpoint, theme |
| 3.6 | Mobile responsive | ⬜ | Tested on iOS Safari + Android Chrome |
| 3.7 | E2E tests | ⬜ | Playwright for web; Tauri mobile test harness |

### Phase 3 Gaps
- **Tauri crate exists** (`epa-kg-tauri`) but only has boilerplate `main.rs`
- **No UI code at all** — no React, no TypeScript, no Tailwind, no shadcn/ui
- **No Tauri commands** defined in Rust backend
- **No frontend scaffold** at all

---

## Phase 4: Lab Document Ingestion (Weeks 10-12) — ⬜ NOT STARTED

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 4.1 | Multi-tenant API | ⬜ | `/tenants/{id}/documents` CRUD; JWT auth |
| 4.2 | SOP/QAP upload & isolation | ⬜ | Separate Chroma collections per tenant |
| 4.3 | Hybrid query (EPA + lab docs) | ⬜ | Single query searches both collections |
| 4.4 | User/role management | ⬜ | Admin, chemist, viewer roles |
| 4.5 | PostgreSQL tenant/users tables | ⬜ | Schema exists in plan, not implemented |

### Phase 4 Gaps
- **No auth implementation** — no JWT, no OAuth2/OIDC, no Keycloak/Ory integration
- **No multi-tenant infrastructure** — single Chroma collection only
- **No document upload endpoints** in Python API or Rust CLI

---

## Phase 5: Commercial Audit Suite (Separate Repo) — ⬜ OUT OF SCOPE

| # | Deliverable | Status |
|---|-------------|--------|
| 5.1 | Compliance audit workflows | ⬜ |
| 5.2 | Gap analysis reports | ⬜ |
| 5.3 | EPA-format output generation | ⬜ |

---

## Cross-Cutting / Infrastructure — 🔄 PARTIAL

| Area | Item | Status | Notes |
|------|------|--------|-------|
| **CI/CD** | GitHub Actions workflow | ✅ | `.github/workflows/ci.yml` exists |
| **CI/CD** | Codecov integration | ⚠️ | Workflow has upload step but no `CODECOV_TOKEN` secret configured |
| **Linting** | Ruff (Python) | ✅ | All checks pass |
| **Linting** | Clippy (Rust) | ✅ | All clean |
| **Formatting** | ruff format / cargo fmt | ✅ | |
| **Type checking** | mypy (Python) | ⚠️ | Configured but not run in CI |
| **Pre-commit hooks** | cargo-husky / pre-commit | ❌ | Not installed |
| **Security audit** | cargo audit | ❌ | Not in CI |
| **Dependency updates** | Dependabot / renovate | ❌ | Not configured |
| **Changelog** | CHANGELOG.md | ✅ | Exists at root |
| **Docker** | Multi-stage Dockerfile | ❌ | **Missing entirely** |
| **Docker** | docker-compose.yml | ❌ | **Missing entirely** |
| **Security** | SECURITY.md | ✅ | Exists |
| **License** | MIT | ✅ | LICENSE file exists |
| **Contributing** | CONTRIBUTING.md | ✅ | Root + docs/ both have it |

---

## Documentation — ✅ MOSTLY COMPLETE

| Doc | Status | Notes |
|-----|--------|-------|
| README.md | ✅ | Comprehensive |
| CONTRIBUTING.md | ✅ | Root + docs/ |
| SECURITY.md | ✅ | |
| CHANGELOG.md | ✅ | |
| docs/architecture.md | ✅ | |
| docs/api.md | ✅ | |
| docs/ingestion-guide.md | ✅ | |
| docs/development.md | ✅ | |
| docs/contributing.md | ✅ | |
| docs/phase-1-ingestion.md | ✅ | |
| CONTRIBUTING.md (root) | ✅ | Created in Step 4 |
| Makefile | ✅ | Has test shortcuts |

---

## Identified Plan Gaps (Not in Any Plan but Needed)

| # | Missing Item | Why It Matters |
|---|--------------|----------------|
| G1 | **File-hash based incremental ingestion** | Without MD5/SHA tracking, re-ingesting large PDF sets re-processes everything |
| G2 | **Table extraction** | EPA methods have critical tables (analyte lists, QC limits) — pdfplumber ready but unused |
| G3 | **Figure/caption extraction** | Methods reference figures; captions contain critical context |
| G4 | **Authentication/Authorization** | Zero auth currently; required for Phase 4 multi-tenancy |
| G5 | **Rate limiting** | API has no protection; needed before any public exposure |
| G6 | **Request/response logging** | No structured logging middleware for audit trail |
| G7 | **Health check endpoint details** | `/health` returns basic status but no dependency checks (DB, Chroma, LLM) |
| G8 | **OpenAPI schema export** | FastAPI auto-generates but not exported/versioned |
| G9 | **Configuration validation at startup** | Settings loaded but no validation of required keys (API keys, paths) |
| G10 | **Graceful shutdown handling** | Lifespan exists but no SIGTERM handling for in-flight requests |
| G11 | **Metrics / Prometheus endpoint** | No `/metrics` for observability |
| G12 | **CLI `--config` file support** | Plan mentions `--config .env.production` but not implemented |
| G13 | **Graph CLI subcommand** | Phase 2 deliverable but no skeleton command in `epa-kg-ingest` |
| G14 | **SQLite migrations** | No `sqlx` migration setup for PostgreSQL or SQLite |
| G15 | **Tauri v2 mobile build config** | `tauri.conf.json` not present; mobile targets unconfigured |
| G15 | **E2E test infrastructure** | No Playwright, no mobile test harness |

---

## Recommended Next Steps (Priority Order)

### Immediate (This Week)
1. **Add Dockerfile + docker-compose.yml** — Blocked on Phase 1 complete
2. **Implement file-hash change detection** — Simple MD5 tracking in SQLite/JSON
3. **Add table extraction to `chunking.py`** — Use pdfplumber (already in deps)
4. **Add `graph` CLI subcommand skeleton** — Wire into `epa-kg-ingest`
5. **Configure Codecov token** in GitHub secrets

### Short Term (Next 2 Weeks)
6. **Implement reference extractor** (Phase 2.1) — Regex first, LLM fallback
7. **Add SQLite edges table + persistence** in `epa-kg-graph`
8. **Add `graph` CLI command** with ASCII tree output
9. **Add SQLx migration setup** for PostgreSQL
10. **Add structured logging + request ID middleware**

### Medium Term (Phase 2 Complete)
11. **Implement cross-ref metadata enrichment**
12. **Golden-file tests for known cross-refs**
13. **Add Tauri v2 scaffold + React/TypeScript/Tailwind setup**
14. **Implement Tauri commands for query/ingest**

---

## Validation Commands

```bash
# Run all tests
make test

# Python only
cd python/ingestion && uv run pytest -v --cov=ingestion --cov-report=term-missing

# Rust only
cargo test --workspace --verbose

# Linting
cargo clippy --workspace -- -D warnings
cd python/ingestion && uv run ruff check .

# Coverage
cargo llvm-cov --workspace --html  # if installed
```

---

## Summary

| Phase | % Complete | Blockers |
|-------|------------|----------|
| Phase 1: Ingestion | ~90% | Dockerfile, table extraction, file-hash tracking |
| Phase 2: Cross-refs | 0% | No code started |
| Phase 3: Tauri UI | 0% | No scaffold |
| Phase 4: Multi-tenant | 0% | No auth, no multi-tenant infra |
| Phase 5: Commercial | N/A | Separate repo |

**Overall:** Strong Phase 1 foundation. Ready to start Phase 2 once Docker/incremental ingestion gaps closed.