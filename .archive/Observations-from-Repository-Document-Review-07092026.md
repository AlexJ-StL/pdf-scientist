# Observations from Repository Document Review 07/09/2026

1. Duplicate Type Definitions (Graph Crate)
- `crates/epa-kg-graph/src/models.rs` and `engine.rs` both define identical `EdgeType enum` and `CitationEdge` struct. One should be removed and the other re-exported.

2. API Handlers Are Stubs
- `crates/epa-kg-api/src/handlers.rs` — `query_handler`, `ingest_handler`, and `health_handler` return placeholder responses. The actual ChromaDB/PostgreSQL integration is missing from the Axum layer.

3. State Is Empty
- `crates/epa-kg-api/src/state.rs` — AppState has no fields. You'll need to inject `ChromaManager`, `sqlx::PgPool`, and Settings here for the handlers to work.

4. No SQLx Migrations Yet
- PostgreSQL tables (`tenants`, `users`, `lab_documents`) are documented but no migration files exist in `crates/epa-kg-api/migrations/`.

5. Tauri Frontend Missing
- `crates/epa-kg-tauri/tauri.conf.json` points to `../dist` for `frontendDist` but no `ui/` directory exists. You'll need to scaffold React+Vite+TS there.

6. Docker Not Implemented
- docker/ directory doesn't exist but referenced in `README`. Need Dockerfile (multi-stage) and `docker-compose.yml` with postgres + chroma + api + ingestion services.

7. No CI/CD Pipeline
- `.github/workflows/` is empty. The `CONTRIBUTING.md` references GitHub Actions that don't exist yet.

8. CLI graph and serve Commands Are Stubs
- `crates/epa-kg-ingest/src/main.rs` — `run_graph()` prints "not yet implemented", `run_server()` prints "Server not yet implemented".

| Priority | Suggestions |
|--- |--- |
| Priority | Action |
| High | Implement AppState with Chroma/Postgres connections; wire up API handlers |
| High | Add SQLx migrations for Phase 1 tables |
| Medium | Remove duplicate types in epa-kg-graph |
| Medium | Scaffold Tauri frontend (ui/) |
| Medium | Create docker/ with Compose for local dev |
| Low | Clean up legacy root files |

## Concluding statement:

* **The core architecture is solid** — the Rust/Python boundary is clean, config is unified, and the ingestion pipeline is well-structured. 
* **The main gaps:** the API layer wiring to the data stores; adding the operational infrastructure (Docker, CI, migrations); and the UI needs to be created