//! API route definitions

use crate::handlers::{health_handler, ingest_handler, query_handler};
use crate::state::AppState;
use axum::{
    routing::{get, post},
    Router,
};
use std::sync::Arc;
use tower_http::cors::CorsLayer;

/// Build the application router with all API routes mounted.
pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/health", get(health_handler))
        .route("/query", post(query_handler))
        .route("/ingest", post(ingest_handler))
        .layer(CorsLayer::permissive())
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn router_can_be_constructed() {
        let state = AppState::new();
        let _ = router(state);
    }
}
