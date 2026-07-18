# API Reference

## Base URL

| Environment | URL |
|-------------|-----|
| Local Development | `http://127.0.0.1:8001` |
| Production | Configurable via `EPA_KG__APP__HOST` / `EPA_KG__APP__PORT` |

## Authentication

Currently no authentication required for local development. Phase 4+ will add JWT/OIDC.

## Endpoints

### Health Check

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "chroma_connected": true,
  "embedding_provider": "fastembed",
  "llm_provider": "none"
}
```

---

### Ingest Documents

```http
POST /ingest
Content-Type: application/json
```

**Request Body:**
```json
{
  "pdf_dir": "./epa-methods",
  "collection": "epa_methods",
  "force_reindex": false,
  "chunk_size": 512,
  "chunk_overlap": 64,
  "toc_aware": true,
  "max_files": 50
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pdf_dir` | string | No | Config value | Directory containing PDF files |
| `collection` | string | No | `epa_methods` | ChromaDB collection name |
| `force_reindex` | boolean | No | `false` | Re-process already indexed files |
| `chunk_size` | integer | No | Config value | Target tokens per chunk |
| `chunk_overlap` | integer | No | Config value | Token overlap between chunks |
| `toc_aware` | boolean | No | Config value | Use TOC-aware chunking |
| `max_files` | integer | No | `0` (all) | Limit number of PDFs to process (0 = all) |

**Response (200 OK):**
```json
{
  "status": "completed",
  "documents_processed": 42,
  "chunks_created": 1247,
  "time_ms": 45230,
  "errors": []
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "PDF directory does not exist: ./epa-methods"
}
```

---

### Query Knowledge Graph

```http
POST /query
Content-Type: application/json
```

**Request Body:**
```json
{
  "question": "How do I prepare soil samples for 8270E?",
  "top_k": 5,
  "collection": "epa_methods",
  "embedding_provider": null,
  "embedding_model": null
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | string | Yes | — | Natural language query |
| `top_k` | integer | No | `5` | Number of results to return |
| `collection` | string | No | `epa_methods` | ChromaDB collection name |
| `embedding_provider` | string | No | Config value | Override embedding provider |
| `embedding_model` | string | No | Config value | Override embedding model |

**Response (200 OK):**
```json
{
  "answer": "Found 5 relevant sections for your query:\n\n**8270E §4.2.1** (score: 0.892)\nSample preparation for solid matrices involves...\n\n**8270E §4.1** (score: 0.847)\nScope and application covers...\n\n...",
  "sources": [
    {
      "method": "8270E",
      "section": "4.2.1",
      "chunk_index": 12,
      "text": "Sample preparation for solid matrices involves...",
      "score": 0.892,
      "metadata": {
        "method_number": "8270E",
        "method_title": "Semivolatile Organic Compounds by GC/MS",
        "section": "4.2.1",
        "section_title": "Sample Preparation",
        "matrix": ["solid", "water", "waste"],
        "analytes": ["PAHs", "phenols", "phthalates"],
        "chunk_index": 12,
        "token_count": 487,
        "source_pdf": "epa-8270e.pdf"
      }
    }
  ],
  "query_time_ms": 234
}
```

---

## CLI Commands

The Rust CLI (`epa-kg`) communicates with the Python service via HTTP.

### Ingest

```bash
# Basic ingestion
epa-kg ingest --pdf-dir ./epa-methods

# With options
epa-kg ingest \
  --pdf-dir ./epa-methods \
  --collection epa_methods \
  --force-reindex \
  --max-files 50 \
  --config .env.production
```

### Query

```bash
# Natural language query
epa-kg query "How do I prepare soil samples for 8270E?" --top-k 5

# Specify collection
epa-kg query "What are the holding times for 6020B?" --collection epa_methods
```

### Graph (Phase 2+)

```bash
# Show citation graph
epa-kg graph --method 8270E --depth 2
```

### Serve (API Server)

```bash
# Start Axum API server
epa-kg serve --port 8080
```

---

## Tauri Commands (Frontend → Rust)

Available via `window.__TAURI__.invoke()`:

### `greet(name: string): Promise<string>`
Simple test command.

### `query_knowledge_graph(question: string, top_k: number): Promise<string>`
Query the knowledge graph from the UI.

### `ingest_documents(pdf_dir: string, collection: string): Promise<string>`
Trigger ingestion from the UI.

---

## Error Responses

All endpoints return consistent error format:

```json
{
  "detail": "Error description"
}
```

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Not found |
| 500 | Internal server error |
| 503 | Service unavailable (not initialized) |

---

## Configuration via Environment

The Python service reads from the same `.env` as Rust (via `pydantic-settings`):

```bash
# Server
EPA_KG__APP__HOST=127.0.0.1
EPA_KG__APP__PORT=8001
EPA_KG__APP__LOG_LEVEL=info
EPA_KG__APP__RELOAD=false
EPA_KG__APP__DATA_DIR=./data

# ChromaDB
EPA_KG__CHROMA__HOST=127.0.0.1
EPA_KG__CHROMA__PORT=8000
EPA_KG__CHROMA__COLLECTION_NAME=epa_methods
EPA_KG__CHROMA__PERSIST_DIR=./data/chroma

# Ingestion
EPA_KG__INGESTION__PDF_DIR=./epa-methods
EPA_KG__INGESTION__CHUNK_SIZE=512
EPA_KG__INGESTION__CHUNK_OVERLAP=64
EPA_KG__INGESTION__TOC_AWARE=true
EPA_KG__INGESTION__EXTRACT_TABLES=true
EPA_KG__INGESTION__MAX_FILE_SIZE_MB=100
EPA_KG__INGESTION__MAX_FILES=0

# Embeddings
EPA_KG__EMBEDDING__PROVIDER=fastembed  # or openrouter, ollama
# OpenRouter
EPA_KG__EMBEDDING__OPENROUTER__API_KEY=sk-or-...
EPA_KG__EMBEDDING__OPENROUTER__MODEL=openai/text-embedding-3-small
# Ollama
EPA_KG__EMBEDDING__OLLAMA__HOST=http://localhost:11434
EPA_KG__EMBEDDING__OLLAMA__MODEL=nomic-embed-text

# LLM (Metadata)
EPA_KG__LLM__PROVIDER=none  # or openrouter, ollama
EPA_KG__LLM__OPENROUTER__API_KEY=sk-or-...
EPA_KG__LLM__OPENROUTER__MODEL=anthropic/claude-3.5-sonnet
EPA_KG__LLM__OLLAMA__HOST=http://localhost:11434
EPA_KG__LLM__OLLAMA__MODEL=llama3.2:3b
```

---

## Rate Limits

Not yet implemented. Planned for Phase 4 (multi-tenant API).

---

## OpenAPI / Swagger

Available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the Python service.