# Ingestion Guide

## Overview

The ingestion pipeline processes EPA method PDFs into structured, searchable vector chunks with rich metadata.

```
PDF → Text/TOC Extraction → Section-Aware Chunking → Metadata Extraction → Embedding → ChromaDB
```

---

## Quick Start

```bash
# 1. Place EPA method PDFs in a directory
mkdir -p ./epa-methods
cp ~/Downloads/epa-*.pdf ./epa-methods/

# 2. Start Python ingestion service
cd python/ingestion
uv run python -m main

# 3. Ingest via CLI (in another terminal)
cargo run --bin epa-kg -- ingest --pdf-dir ./epa-methods

# 4. Query
cargo run --bin epa-kg -- query "How do I prepare soil samples for 8270E?"
```

---

## Configuration

All settings via `.env` (or environment variables with `EPA_KG__` prefix):

```bash
# Ingestion
EPA_KG__INGESTION__PDF_DIR=./epa-methods
EPA_KG__INGESTION__CHUNK_SIZE=512
EPA_KG__INGESTION__CHUNK_OVERLAP=64
EPA_KG__INGESTION__TOC_AWARE=true
EPA_KG__INGESTION__EXTRACT_TABLES=true
EPA_KG__INGESTION__MAX_FILE_SIZE_MB=100

# Embeddings (choose one)
EPA_KG__EMBEDDING__PROVIDER=fastembed        # Local, default
# EPA_KG__EMBEDDING__PROVIDER=ollama         # Local, needs Ollama
# EPA_KG__EMBEDDING__PROVIDER=openrouter     # Remote, needs API key

# LLM for metadata extraction (optional)
EPA_KG__LLM__PROVIDER=none                   # Disabled (regex fallback)
# EPA_KG__LLM__PROVIDER=ollama               # Local
# EPA_KG__LLM__PROVIDER=openrouter           # Remote
```

---

## Chunking Strategy

### TOC-Aware (Default)

Uses PDF's embedded Table of Contents:

```
Method 8270E
├── 1.0 Scope and Application
├── 2.0 Summary of Method
├── 3.0 Definitions
├── 4.0 Interferences
├── 5.0 Safety
├── 6.0 Equipment and Supplies
├── 7.0 Reagents and Standards
├── 8.0 Sample Collection, Preservation, Storage
├── 9.0 Quality Control
├── 10.0 Calibration and Standardization
├── 11.0 Procedure
│   ├── 11.1 Sample Preparation
│   ├── 11.2 Extraction
│   └── 11.3 Analysis
└── ...
```

Each TOC entry → section → chunks respecting `chunk_size`/`overlap`.

### Regex Fallback (No TOC)

Detects EPA-style section headers:

```
1.0 Scope and Application
1.1 Subsection
2.0 Summary of Method
11.2.1 Extraction Procedure A
```

Pattern: `^\s*(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*|[IVX]+\.\d+)\s+(.+?)\s*$`

### Recursive Splitting

Sections exceeding `chunk_size` split at sentence boundaries with overlap:

```
[Chunk 1: tokens 0-512] ────┐
[Chunk 2: tokens 448-960] ← Overlap (64 tokens)
[Chunk 3: tokens 896-1408] ┘
```

---

## Metadata Extraction

### LLM-Assisted (Recommended)

Uses configured LLM provider to extract structured metadata from first ~8000 chars:

```json
{
  "method_number": "8270E",
  "method_title": "Semivolatile Organic Compounds by GC/MS",
  "revision": "E",
  "revision_date": "2018-02-01",
  "supersedes": "8270D",
  "status": "Active",
  "matrix": ["solid", "water", "waste"],
  "analytes": ["PAHs", "phenols", "phthalates", "nitroaromatics"],
  "references": ["3500C", "3600C", "8000D", "3545A"],
  "section_count": 17
}
```

**Providers:**
- OpenRouter: `anthropic/claude-3.5-sonnet` (best quality)
- Ollama: `llama3.2:3b` (local, no API key)

### Regex Fallback (No LLM)

Extracts from filename + text patterns:
- Method number: `(\d{4}[A-Z]?)` from filename or "METHOD XXXX"
- Revision: `REVISION ([A-Z])`
- Date: `(\d{4}[-/]\d{2}[-/]\d{2})`
- Supersedes: `SUPERSEDES (METHOD )?(\d{4}[A-Z]?)`
- Matrix: Keyword search (water, soil, waste, air, tissue, sludge)

---

## Embedding Providers

| Provider | Model | Dimensions | Speed | Quality | Offline |
|----------|-------|------------|-------|---------|---------|
| **FastEmbed** | BAAI/bge-small-en-v1.5 | 384 | ⚡⚡⚡ | Good | ✅ |
| **Ollama** | nomic-embed-text | 768 | ⚡⚡ | Good | ✅ |
| **OpenRouter** | openai/text-embedding-3-small | 1536 | ⚡ | Best | ❌ |

**Default:** FastEmbed (zero-config, fast, decent quality)

**Switching:**
```bash
# In .env
EPA_KG__EMBEDDING__PROVIDER=ollama
EPA_KG__EMBEDDING__OLLAMA__MODEL=nomic-embed-text
```

---

## ChromaDB Collections

| Collection | Purpose | Created By |
|------------|---------|------------|
| `epa_methods` | EPA method chunks (default) | CLI ingest |
| `tenant_{id}_sops` | Lab SOPs/QAPs (Phase 4) | Multi-tenant API |
| `tenant_{id}_qaps` | Lab QAPs (Phase 4) | Multi-tenant API |

**Naming:** Deterministic IDs: `METHOD_{method}_{section}_{chunk_index}`

Example: `METHOD_8270E_11.2.1_3`

---

## Idempotency & Re-indexing

### Skip Existing (Default)

```bash
# Only processes new/changed files
epa-kg ingest --pdf-dir ./epa-methods
```

ChromaDB `get()` checks existing IDs before embedding.

### Force Re-index

```bash
# Re-processes all files, overwrites chunks
epa-kg ingest --pdf-dir ./epa-methods --force-reindex
```

### Change Detection

Future: File hash comparison (MD5) to detect modified PDFs.

---

## Troubleshooting

### "No PDF files found"
```bash
# Check directory exists and has .pdf files
ls -la ./epa-methods/*.pdf
```

### "ChromaDB connection failed"
```bash
# Check Python service is running
curl http://127.0.0.1:8001/health

# Check ChromaDB port
nc -zv 127.0.0.1 8000
```

### "Embedding provider failed"
```bash
# FastEmbed: First run downloads model (~100MB)
# Ollama: Ensure service running
ollama serve
ollama pull nomic-embed-text

# OpenRouter: Check API key
echo $OPENROUTER_API_KEY
```

### "Metadata extraction failed"
- Falls back to regex automatically
- Check LLM provider config
- Check logs: `RUST_LOG=debug cargo run ...`

### Large PDFs timeout
```bash
# Increase timeout in .env or chunk smaller
EPA_KG__INGESTION__MAX_FILE_SIZE_MB=200
EPA_KG__INGESTION__CHUNK_SIZE=256
```

---

## Performance Tuning

| Parameter | Default | Recommendation |
|-----------|---------|----------------|
| `chunk_size` | 512 | 256 for precise citations, 1024 for context |
| `chunk_overlap` | 64 | 10-20% of chunk_size |
| `batch_size` (embeddings) | 32 | 64-128 for GPU, 16-32 for CPU |
| `toc_aware` | true | Keep true for EPA methods |

### Benchmarks (Approximate)

| PDF Pages | Chunks | Time (FastEmbed CPU) | Time (Ollama GPU) |
|-----------|--------|---------------------|-------------------|
| 50 | ~200 | 30s | 15s |
| 100 | ~400 | 60s | 30s |
| 200 | ~800 | 120s | 60s |

---

## Advanced: Custom Ingestion

### Via Python API

```python
from main import process_pdf
from config import settings

result = await process_pdf(
    pdf_file=Path("epa-8270e.pdf"),
    collection="epa_methods",
    chunker=EPAMethodChunker(chunk_size=512, chunk_overlap=64),
    embedding_provider=get_embedding_provider(settings),
    metadata_extractor=get_metadata_extractor(settings),
    chroma_manager=chroma_manager,
    force_reindex=False,
)
print(result)  # {"chunks_created": 42}
```

### Custom Chunker

```python
from chunking import EPAMethodChunker

class CustomChunker(EPAMethodChunker):
    def extract_sections_from_text(self, text):
        # Custom section detection
        pass
```

---

## Phase 1 Checklist

- [ ] PDF directory configured
- [ ] Python service starts (`/health` returns OK)
- [ ] CLI ingest completes without errors
- [ ] ChromaDB has documents (`epa-kg query "test"` returns results)
- [ ] Citations include method/section/chunk
- [ ] Re-ingest is idempotent (no duplicate chunks)
- [ ] Unit tests pass (`cargo test` + `pytest`)

---

## Next Steps (Phase 2+)

- Cross-reference extraction (Method 8270E → 3500C, 3600C)
- Graph CLI: `epa-kg graph --method 8270E --depth 2`
- Table extraction (pdfplumber)
- Figure/caption extraction
- Multi-language support (EPA methods in Spanish)