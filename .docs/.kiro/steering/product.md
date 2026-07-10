# Product Overview

**EPA Knowledge Graph / AI Lab Assistant** — An open-source knowledge graph and AI assistant for environmental laboratories to dynamically reference EPA methods, SOPs, QAPs, and regulatory standards.

---

## Vision

Environmental labs juggle hundreds of EPA methods (SW-846, 40 CFR, etc.), each cross-referencing others, with matrix-specific exceptions, analyte lists, and revision histories. Bench chemists need answers **now** — not after digging through PDFs.

This project builds:

1. **Semantic Vector Store** of EPA methods with rich metadata (method #, section, matrix, analytes, revision, supersession chain)
2. **Citation Graph** linking methods → sections → referenced methods
3. **Natural-Language Query Interface** (CLI + Tauri desktop/mobile app) answering with source citations
4. **Lab Document Ingestion** (SOPs, QAPs) for tenant-isolated hybrid search (EPA + internal)

**Commercial tier (separate repo):** `epa-audit-suite` — structured audit workflows, gap analysis, EPA-format report generation for accreditation bodies.

---

## Target Users

| Primary (OSS) | Secondary (Commercial) |
|---------------|------------------------|
| Bench chemists / lab techs | EPA auditors (Cincinnati) |
| Lab QA/QC managers | Accreditation bodies (NELAC, A2LA) |
| Environmental consultants | Commercial lab chains |

---

## Key Features (Phase 1+)

| Feature | Phase | Description |
|---------|-------|-------------|
| PDF Ingestion | 1 | TOC-aware chunking, table extraction, metadata enrichment |
| Semantic Search | 1 | Natural language → top-K chunks with citations |
| CLI Interface | 1 | `epa-kg ingest`, `epa-kg query`, `epa-kg serve` |
| Multi-provider Embeddings | 1 | FastEmbed (local), Ollama (local), OpenRouter (cloud) |
| LLM Metadata Extraction | 1 | OpenRouter (Claude), Ollama (Llama), Regex fallback |
| ChromaDB Persistence | 1 | Embedded, server, or cloud |
| Citation Graph | 2 | Cross-reference extraction, graph traversal |
| Tauri Desktop App | 3 | Dark-mode chat UI, method browser, mobile |
| Multi-tenant Lab Docs | 4 | SOP/QAP upload, tenant isolation, hybrid EPA+lab search |
| Audit Suite | 5 (commercial) | Checklists, gap analysis, EPA-format reports |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Ingestion speed | 50 EPA methods < 2 min |
| Query latency (local) | < 500ms p95 |
| Retrieval relevance | > 0.85 nDCG@5 |
| Test coverage | ≥ 80% |
| Binary size (Tauri) | < 50 MB |