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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_state_is_constructible() {
        let state = AppState::default();
        let _ = state;
    }

    #[test]
    fn new_returns_arc() {
        let state = AppState::new();
        assert!(Arc::strong_count(&state) >= 1);
    }

    #[test]
    fn state_is_cloneable() {
        let state = AppState::new();
        let cloned = Arc::clone(&state);
        assert!(Arc::ptr_eq(&state, &cloned));
    }
}
