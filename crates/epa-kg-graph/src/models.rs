//! Graph data models

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum EdgeType {
    Supersedes,
    References,
    CitesSection,
    SharesAnalyte,
    SameMatrix,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CitationEdge {
    pub source_id: String,
    pub target_id: String,
    pub edge_type: EdgeType,
    pub confidence: f32,
    pub context: Option<String>,
}