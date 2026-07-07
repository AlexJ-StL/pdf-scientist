//! API route definitions

use axum::{
    routing::{get, post},
    Router,
};
use crate::handlers::{health_handler, ingest_handler, query_handler};
use crate::state::AppState;
use std::sync::Arc;

/// Build the application router with all API routes mounted.
pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/health", get(health_handler))
        .route("/query", post(query_handler))
        .route("/ingest", post(ingest_handler))
        .with_state(state)
}
