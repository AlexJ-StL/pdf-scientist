//! Shared application state

use std::sync::Arc;

/// Application-wide shared state, injected into handlers via Axum `State`.
#[derive(Debug, Default, Clone)]
pub struct AppState {
    // TODO: populate with ChromaDB client, sqlx pool, config, etc.
}

impl AppState {
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }
}
