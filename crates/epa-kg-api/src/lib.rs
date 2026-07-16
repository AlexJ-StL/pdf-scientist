//! Axum HTTP API for EPA Knowledge Graph

pub mod error;
pub mod handlers;
pub mod routes;
pub mod state;

pub use state::AppState;
