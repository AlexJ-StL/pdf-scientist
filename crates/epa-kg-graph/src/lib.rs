//! Citation graph engine for EPA methods

pub mod engine;
pub mod models;

pub use engine::GraphEngine;
pub use models::{CitationEdge, EdgeType};