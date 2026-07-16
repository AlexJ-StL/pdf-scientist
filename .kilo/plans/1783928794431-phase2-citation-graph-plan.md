# Phase 2: Citation Graph Engine — Implementation Plan

**Status:** Ready for implementation  
**Prereqs:** Phase 1 ingestion pipeline complete (Python service, tests, CI)

---

## 1. Goal

Build the reference & cross-link engine that:
1. Extracts citations from ingested EPA method chunks (regex + LLM)
2. Persists citation edges to SQLite
3. Exposes graph traversal via `epa-kg graph` CLI
4. Enriches chunk metadata with `supersedes`, `references`, `matrix`, `analytes`

---

## 2. Current State

| Component | Status |
|-----------|--------|
| `epa-kg-graph` crate | Exists, in-memory `GraphEngine` with petgraph |
| `CitationEdge` / `EdgeType` models | Defined in `models.rs` |
| Rust CLI `graph` command | Stub — prints "not yet implemented" |
| SQLite persistence | Not implemented |
| Reference extractor | Not implemented |
| Metadata enrichment | Not implemented |

---

## 3. Key Decisions

### 3.1 Persistence: SQLite vs keep in-memory

**Recommended: SQLite with `rusqlite` or `sqlx` (SQLite feature)**

Rationale:
- The plan explicitly calls for SQLite adjacency in Phase 1/2
- In-memory graph is lost between CLI invocations
- SQLite is zero-config, embedded, matches the "dependency-free" Phase 1 goal
- `sqlx` is already a workspace dependency (with Postgres feature); add `sqlx` runtime + `sqlite` feature

### 3.2 Reference extraction location

**Recommended: Rust crate (`epa-kg-graph`), callable from Python ingestion pipeline**

Rationale:
- Keeps graph logic centralized in Rust where it belongs
- Python service calls a `/graph/extract` endpoint or Rust CLI post-processes
- Regex extraction is fast and deterministic — Rust is appropriate

### 3.3 Extraction order: Regex first, LLM second

**Recommended: Two-pass approach**

Pass 1 (Rust, always): Regex patterns for:
- `Method \d+[A-Z]?` / `EPA \d+[A-Z]?`
- `Section \d+(\.\d+)?`
- `SW-846 \d+[A-Z]?`
- Supersession phrases ("supersedes", "replaces", "formerly")

Pass 2 (Python, optional): LLM-assisted extraction for ambiguous cases using existing `MetadataExtractor` infrastructure.

### 3.4 Graph API surface

**Recommended: Rust-only for graph traversal; Python for ingestion-time extraction**

- `epa-kg graph --method 8270E --depth 2` — loads from SQLite, traverses, prints ASCII tree
- Python service exposes `/graph/ingest` endpoint that Rust CLI calls during ingestion
- No need to expose graph queries via Python HTTP API in Phase 2

### 3.5 Golden-file format

**Recommended: JSON files in `crates/epa-kg-graph/tests/golden/`**

- One JSON per EPA method with expected `edges` array
- Easy to diff, version-control, and validate in Rust tests

---

## 4. Implementation Tasks

### Task 1: Add SQLite persistence to `epa-kg-graph`

**Files to modify:**
- `crates/epa-kg-graph/Cargo.toml` — add `rusqlite` or enable `sqlx` sqlite runtime
- `crates/epa-kg-graph/src/engine.rs` — add `persist_edge()`, `load_graph()`, `init_schema()`
- `crates/epa-kg-graph/src/models.rs` — add `CitationEdgeRow` for DB serialization

**Steps:**
1. Add `rusqlite = "0.31"` (or use `sqlx` with sqlite feature) to graph crate
2. Create `GraphStore` struct that wraps `GraphEngine` + SQLite connection
3. Implement `init_schema()` — CREATE TABLE IF NOT EXISTS citation_edges
4. Implement `upsert_edge()` — INSERT OR REPLACE
5. Implement `load_into_graph()` — read all edges, populate `GraphEngine`

### Task 2: Implement reference extractor

**Files to create:**
- `crates/epa-kg-graph/src/extractor.rs`

**Steps:**
1. Define `ReferenceExtractor` struct with compiled regexes
2. Implement `extract_from_text(text: &str, source_id: &str) -> Vec<CitationEdge>`
3. Regex patterns:
   - Method refs: `r"(?:Method|EPA)\s+(\d+[A-Z]?)"i`
   - Section refs: `r"Section\s+(\d+(?:\.\d+)?)"i`
   - SW-846 refs: `r"SW-846\s+(\d+[A-Z]?)"i`
   - Supersession: `r"(?:supersedes|replaces|formerly)\s+(?:Method\s+)?(\d+[A-Z]?)"i`
4. Return `CitationEdge` with `confidence` scores (regex = 0.9, LLM = 0.7)

### Task 3: Wire up `run_graph` CLI command

**Files to modify:**
- `crates/epa-kg-ingest/src/main.rs`

**Steps:**
1. In `run_graph()`:
   - Open SQLite DB at `settings.data_dir/graph.db`
   - Load `GraphEngine` from DB
   - Call `engine.get_neighbors(method, depth)`
   - Print ASCII tree (method → neighbors → depth)
2. Handle missing method gracefully

### Task 4: Add ingestion-time graph enrichment

**Files to modify:**
- `python/ingestion/main.py` — add `/graph/extract` endpoint
- `crates/epa-kg-ingest/src/main.rs` — call `/graph/extract` after `/ingest`

**Steps:**
1. Add `/graph/extract` POST endpoint to Python service:
   - Accepts `collection` name
   - Queries all chunks from ChromaDB
   - Runs reference extractor (Python regex pass for now)
   - Returns `Vec<CitationEdge>`
2. After successful `/ingest` in Rust CLI, call `/graph/extract`
3. Persist returned edges to SQLite via `GraphStore`

### Task 5: Metadata enrichment

**Files to modify:**
- `python/ingestion/metadata.py` — add graph-based enrichment

**Steps:**
1. After LLM extraction, augment with graph data:
   - `supersedes`: from `EdgeType::Supersedes` edges where source == current method
   - `references`: from `EdgeType::References` edges
   - `matrix` / `analytes`: from co-occurrence in `SHARES_ANALYTE` / `SAME_MATRIX` edges
2. Store enriched metadata in ChromaDB chunk metadata

### Task 6: Golden-file tests

**Files to create:**
- `crates/epa-kg-graph/tests/golden/8270E.json`
- `crates/epa-kg-graph/tests/golden/3500C.json`

**Files to modify:**
- `crates/epa-kg-graph/src/extractor.rs` — add `#[cfg(test)]` module

**Steps:**
1. Create golden JSON files with known EPA method cross-references
2. Write test that loads golden file, runs extractor on sample text, asserts edges match
3. Use EPA method PDFs already in `python/test_pdf/` or create synthetic test text

---

## 5. Validation Criteria

| Check | Command | Expected |
|-------|---------|----------|
| Rust tests pass | `cargo test --workspace` | All pass |
| Python tests pass | `pytest` | ≥155 passing |
| Graph CLI works | `cargo run --bin epa-kg -- graph --method 8270E --depth 2` | ASCII tree output |
| SQLite created | Check `./data/graph.db` | File exists with `citation_edges` table |
| Ingestion enriches metadata | Ingest a PDF, query chunk metadata | `supersedes`, `references` populated |
| Golden tests pass | `cargo test -p epa-kg-graph` | Edge cases match golden files |

---

## 6. Out of Scope (Phase 2)

- Neo4j migration (deferred to Phase 2+ per plan)
- Tauri UI graph visualization (Phase 3)
- Multi-tenant graph isolation (Phase 4)
- Audit suite (commercial repo)

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Regex extraction misses edge cases | LLM pass as fallback; golden-file tests catch regressions |
| SQLite schema migrations | Use simple schema for Phase 2; migrations deferred |
| Performance on large PDFs | Batch extraction; async Python endpoint |

---

## 8. Open Question

**Should reference extraction run during ingestion (synchronous, slows ingest) or as a separate CLI step (`epa-kg graph --extract`)?**

Recommended answer: **During ingestion, as an optional background step.** The Python service already supports `BackgroundTasks` in FastAPI. The Rust CLI calls `/ingest`, then `/graph/extract` as a follow-up request. This keeps the workflow single-command while not blocking the ingest response.
