//! Graph data models

use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum EdgeType {
    Supersedes,
    References,
    CitesSection,
    SharesAnalyte,
    SameMatrix,
    CfrReference,
}

impl std::fmt::Display for EdgeType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EdgeType::Supersedes => write!(f, "SUPERSEDES"),
            EdgeType::References => write!(f, "REFERENCES"),
            EdgeType::CitesSection => write!(f, "CITES_SECTION"),
            EdgeType::SharesAnalyte => write!(f, "SHARES_ANALYTE"),
            EdgeType::SameMatrix => write!(f, "SAME_MATRIX"),
            EdgeType::CfrReference => write!(f, "CFR_REFERENCE"),
        }
    }
}

impl FromStr for EdgeType {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_uppercase().as_str() {
            "SUPERSEDES" => Ok(EdgeType::Supersedes),
            "REFERENCES" => Ok(EdgeType::References),
            "CITES_SECTION" => Ok(EdgeType::CitesSection),
            "SHARES_ANALYTE" => Ok(EdgeType::SharesAnalyte),
            "SAME_MATRIX" => Ok(EdgeType::SameMatrix),
            "CFR_REFERENCE" => Ok(EdgeType::CfrReference),
            _ => Err(format!("Unknown edge type: {}", s)),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CitationEdge {
    pub source_id: String,
    pub target_id: String,
    pub edge_type: EdgeType,
    pub confidence: f32,
    pub context: Option<String>,
}
