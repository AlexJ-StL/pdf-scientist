//! Graph engine for citation traversal

use epa_kg_core::{Error, Result};
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

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

pub struct GraphEngine {
    graph: DiGraph<String, EdgeType>,
    node_map: HashMap<String, NodeIndex>,
}

impl GraphEngine {
    pub fn new() -> Self {
        Self {
            graph: DiGraph::new(),
            node_map: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, method_id: String) -> NodeIndex {
        if let Some(&idx) = self.node_map.get(&method_id) {
            idx
        } else {
            let idx = self.graph.add_node(method_id.clone());
            self.node_map.insert(method_id, idx);
            idx
        }
    }

    pub fn add_edge(&mut self, edge: CitationEdge) {
        let source_idx = self.add_node(edge.source_id);
        let target_idx = self.add_node(edge.target_id);
        self.graph.add_edge(source_idx, target_idx, edge.edge_type);
    }

    pub fn get_neighbors(&self, method_id: &str, depth: usize) -> Vec<String> {
        let Some(&start) = self.node_map.get(method_id) else {
            return vec![];
        };

        let mut visited = std::collections::HashSet::new();
        let mut current = vec![start];
        let mut result = Vec::new();

        for _ in 0..depth {
            let mut next = Vec::new();
            for &node in &current {
                if visited.insert(node) {
                    if let Some(name) = self.graph.node_weight(node) {
                        result.push(name.clone());
                    }
                    for edge in self.graph.edges(node) {
                        next.push(edge.target());
                    }
                }
            }
            current = next;
            if current.is_empty() {
                break;
            }
        }

        result
    }
}

impl Default for GraphEngine {
    fn default() -> Self {
        Self::new()
    }
}