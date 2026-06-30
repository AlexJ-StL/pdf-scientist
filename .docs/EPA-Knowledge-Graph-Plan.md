# EPA Knowledge Graph / AI Lab Assistant — Formal Plan

**Version:** 1.0
**Date:** 2026-06-30
**Status:** Draft for Review
**Repo:** `pdf-scientist` (will rename to `epa-knowledge-graph` for OSS release)

---

## 1. Vision & Scope

### 1.1 North Star
Build an **open-source knowledge graph + AI lab assistant** for environmental laboratories to dynamically reference EPA methods, internal SOPs, QAPs, and regulatory standards. Designed for bench chemists who need answers on their phones in real time.

### 1.2 Commercial Upsell (Separate Repo)
`epa-audit-suite` (proprietary): Compliance audit workflows, gap analysis reports, EPA-format output for accreditation bodies. Built on top of the OSS knowledge graph.

### 1.3 Target Users
| Primary (OSS) | Secondary (Commercial) |
|---|---|
| Bench chemists / lab techs | EPA auditors (Cincinnati) |
| Lab QA/QC managers | Accreditation bodies (NELAC, A2LA, etc.) |
| Environmental consultants | Commercial lab chains |

---

## 2. Architecture Decisions (Locked)

| Layer | Choice | Rationale |
|---|---|---|
| **Core Language** | **Rust** (Axum) | Security, speed, your preference. Single binary deployment. |
| **ML/Ingestion Pipeline** | **Python** (FastAPI microservice) | PDF parsing, LangChain, embeddings ecosystem is Python-native. |
| **Vector Store** | **ChromaDB** (embedded) | Zero-config, OSS, local-first, ships in Tauri bundle. |
| **Graph Layer (Phase 2+)** | **SQLite + custom adjacency** → upgrade to **Neo4j** if needed | Keep Phase 1 dependency-free. Cross-refs as metadata first. |
| **Frontend / Mobile** | **Tauri v2** (React/TypeScript) | Single codebase → desktop (Win/Mac/Linux) + iOS + Android. Solves your frontend weakness. |
| **CLI** | Rust binary (same Axum core) | For headless lab servers / CI integration. |
| **Database (Relational)** | **PostgreSQL** (local) | You have it installed. For users, tenants, audit logs, metadata. |
| **Auth** | **OAuth2/OIDC** (Keycloak or Ory Kratos) | Lab-grade, supports SSO for commercial tier. |
| **Embeddings** | **fastembed** (BGE-small) default; **OpenAI** optional | Local-first, no API key required. Swappable provider interface. |
| **PDF Parsing** | **pdfium** (via `pdfium-render` or `lopdf`) + **PyMuPDF** (Python) | Better than PyPDF2 for tables/structure. |

---

## 3. Data Model (Phase 1)

### 3.1 Chroma Collection: `epa_methods`
```python
{
    "id": "METHOD_8270E_4.2.1",          # deterministic: METHOD_{num}_{section}
    "document": "Section 4.2.1: ...",    # chunk text
    "metadata": {
        "method_number": "8270E",
        "method_title": "Semivolatile Organic Compounds by GC/MS",
        "section": "4.2.1",
        "section_title": "Sample Preparation",
        "matrix": ["solid", "water", "waste"],
        "analytes": ["PAHs", "phenols", "phthalates"],
        "revision_date": "2018-02-01",
        "supersedes": "8270D",
        "references": ["3500C", "3600C", "8000D"],
        "chunk_index": 42,
        "token_count": 312,
        "source_pdf": "epa-8270e.pdf",
        "source_url": "https://www.epa.gov/.../8270e.pdf"
    },
    "embedding": [0.023, -0.041, ...]    # 384-dim BGE-small
}
```

### 3.2 PostgreSQL Tables (Phase 1+)
```sql
-- Tenants = labs (Phase 4+)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Users (Phase 3+)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    email TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('admin', 'chemist', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Lab documents (SOPs, QAPs) — Phase 4
CREATE TABLE lab_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    title TEXT NOT NULL,
    doc_type TEXT CHECK (doc_type IN ('SOP', 'QAP', 'QAPP', 'WORK_PLAN', 'OTHER')),
    file_path TEXT,
    status TEXT CHECK (status IN ('pending', 'processing', 'indexed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit sessions (Phase 5, commercial)
CREATE TABLE audit_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    auditor_id UUID REFERENCES users(id),
    standard TEXT,  -- 'EPA', 'NELAC', 'ISO17025'
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. Phase Breakdown

### Phase 1: Document Ingestion Pipeline (Weeks 1-3)
**Goal:** CLI tool that ingests EPA method PDFs → Chroma vector store, queryable via CLI.

| Deliverable | Done Criteria |
|---|---|
| `ingest` CLI command | `epa-kg ingest --pdf-dir ./epa-methods --collection epa_methods` |
| PDF → structured chunks | Preserves section hierarchy (TOC-aware); handles tables |
| Embedding generation | fastembed (local) default; `--provider openai` flag |
| Chroma persistence | `./data/chroma/` auto-created; survives restarts |
| CLI query | `epa-kg query "How do I prepare soil samples for 8270E?"` → top-5 chunks with citations |
| Unit tests | `cargo test` + `pytest` ≥ 80% coverage on ingestion logic |
| Dockerfile | Single image runs API + CLI |

**Tech details:**
- Python FastAPI service (`/ingest`, `/query`) called by Rust CLI
- Chunking: **TOC-aware recursive splitter** (fallback: heading-regex + 500/100)
- Metadata extraction: LLM-assisted (local Llama 3.2 3B via Ollama) for method_number, matrix, analytes
- Idempotent: re-ingesting same PDF updates existing chunks (hash-based)

---

### Phase 2: Reference & Cross-Link Engine (Weeks 4-5)
**Goal:** Build the citation graph between methods; enrich metadata.

| Deliverable | Done Criteria |
|---|---|
| Reference extractor | Regex + LLM pass finds "Method 3500C", "Section 4.2 of 8270E", "SW-846 8000D" |
| Graph store | SQLite `edges` table: `(source_chunk_id, target_method, target_section, relation_type)` |
| `graph` CLI command | `epa-kg graph --method 8270E --depth 2` → ASCII tree of dependencies |
| Metadata enrichment | Auto-populate `supersedes`, `references`, `matrix`, `analytes` from cross-refs |
| Tests | Golden-file tests on known method cross-references |

**Relation types:** `SUPERSEDES`, `REFERENCES`, `CITES_SECTION`, `SHARES_ANALYTE`, `SAME_MATRIX`

---

### Phase 3: Lab Assistant UI (Tauri) (Weeks 6-9)
**Goal:** Dark-mode web UI wrapped in Tauri for desktop + mobile.

| Deliverable | Done Criteria |
|---|---|
| Tauri project scaffold | `cargo tauri init`; builds for Linux, Windows, macOS, iOS, Android |
| Chat interface | Streaming responses, markdown rendering, copy-to-clipboard |
| Source citations | Every answer shows chunk references with method/section links |
| Method browser | Tree view: Method → Sections → Chunks |
| Offline-first | Chroma bundled; works without network (except LLM calls) |
| Settings | Embedding provider (local/OpenAI), LLM endpoint, theme |
| Mobile responsive | Tested on iOS Safari + Android Chrome; touch-friendly |
| E2E tests | Playwright for web; Tauri mobile test harness |

**UI Stack:** React 18 + TypeScript + Tailwind CSS + shadcn/ui (accessible components)
**LLM Integration:** Local (Ollama/LMStudio) or cloud (OpenRouter, Anthropic) — user chooses in Settings.

---

### Phase 4: Lab Document Ingestion (Weeks 10-12)
**Goal:** Let labs upload their SOPs/QAPs; tenant-isolated; merged into query context.

| Deliverable | Done Criteria |
|---|---|
| Multi-tenant API | `/tenants/{id}/documents` CRUD; JWT auth |
| Upload UI | Drag-drop PDFs; shows processing status |
| Tenant isolation | Chroma collections per tenant: `tenant_{id}_sops` |
| Hybrid query | Single query searches EPA + tenant SOPs; labels source |
| Admin panel | Manage users, view usage, re-index |
| Tests | Multi-tenant isolation verification |

---

### Phase 5: Audit Suite (Commercial Repo) (Separate Timeline)
**Goal:** Structured audit workflows for accreditation bodies and labs.

| Module | Description |
|---|---|
| **Checklist Engine** | EPA/NELAC/ISO17025 checklists as code; versioned |
| **Gap Analysis** | Compare lab SOPs vs. required method sections |
| **Report Generator** | EPA-format PDF audit reports; evidence linking |
| **Scheduler** | Recurring audit calendar; notifications |
| **Admin Dashboard** | Multi-lab oversight for accreditation bodies |

---

## 5. Project Structure (Monorepo)

```
epa-knowledge-graph/
├── Cargo.toml                    # Rust workspace
├── crates/
│   ├── epa-kg-core/              # Shared types, config, errors
│   ├── epa-kg-ingest/            # Rust CLI + Python service bridge
│   ├── epa-kg-api/               # Axum HTTP API (query, admin)
│   ├── epa-kg-graph/             # Citation graph logic
│   └── epa-kg-tauri/             # Tauri app entry point
├── python/
│   ├── ingestion/                # FastAPI service
│   │   ├── main.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── metadata_extraction.py
│   │   └── tests/
│   └── requirements.txt
├── ui/                           # React frontend (Tauri)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── contributing.md
├── README.md
├── LICENSE (MIT)
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## 6. Open Source Release Checklist

Before first `git push` to `AlexJ-StL/epa-knowledge-graph`:

- [ ] Rename repo from `pdf-scientist` → `epa-knowledge-graph`
- [ ] **Scrub all credentials** from history (`.env`, MongoDB URI in docs)
- [ ] Add proper `.gitignore` (`.venv`, `__pycache__`, `.env`, `data/`, `target/`, `node_modules/`)
- [ ] `LICENSE` (MIT)
- [ ] `README.md` with badges, quickstart, architecture diagram
- [ ] `CONTRIBUTING.md` with PR process, code style, DCO sign-off
- [ ] `CHANGELOG.md` (Keep a Changelog format)
- [ ] GitHub Actions: `cargo test`, `pytest`, `cargo clippy`, `cargo audit`, `trivy` scan
- [ ] Release workflow: tag → build binaries → GitHub Release
- [ ] Crates.io publish for `epa-kg-cli` (optional)
- [ ] Docs site: GitHub Pages + mdBook or VitePress

---

## 7. Immediate Next Steps (This Session)

1. **Clean git history** — remove `.venv`, `.env`, credential-containing docs from staging
2. **Create proper `.gitignore`**
3. **Write Phase 1 spec** as `docs/phase-1-ingestion.md` (detailed enough to start coding)
4. **Set up Rust workspace** + Python service scaffold
5. **Index EPA test PDFs** (you have them locally) to validate chunking strategy

---

## 8. Questions for You Before Phase 1 Code

| # | Question | Default If Silent |
|---|---|---|
| 1 | Where are your local EPA method PDFs? (Path for ingestion testing) | `~/Documents/EPA-Methods/` |
| 2 | Preferred local LLM for metadata extraction? | Ollama + Llama 3.2 3B |
| 3 | Embedding model? | `BAAI/bge-small-en-v1.5` (384-dim, fast, good retrieval) |
| 4 | Chunk size / overlap? | 512 tokens / 64 (tuned for method sections) |
| 5 | Target first CLI release date? | 3 weeks from Phase 1 start |
| 6 | Keep MongoDB references in codebase or purge entirely? | Purge — Chroma + Postgres only |

---

## 9. Appendix: Original Context Preserved

The following files in `.docs/` capture the project's evolution and should be retained for history:
- `.kiro/steering/product.md` — Original product vision
- `.kiro/steering/structure.md` — Original file layout
- `.kiro/steering/tech.md` — Original tech stack (MongoDB, OpenAI, Python)
- `pdf processor.txt` — Initial feature brainstorm
- `Plan for Building a Local Semantic Vector Database App for PDF Files.txt` — 6-phase plan
- `PDF-Processor-MongoDB*.txt` — MongoDB connection references (credentials redacted)
- `Reply to Questions and Vision on pdf-Scientist 06292026.txt` — This session's vision alignment

---

**End of Plan v1.0**