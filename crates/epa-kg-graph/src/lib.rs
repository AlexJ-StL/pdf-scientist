//! Citation graph engine for EPA methods

pub mod engine;
pub mod extractor;
pub mod models;
pub mod store;

pub use engine::GraphEngine;
pub use extractor::ReferenceExtractor;
pub use models::{CitationEdge, EdgeType};
pub use store::GraphStore;
