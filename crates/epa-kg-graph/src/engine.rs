//! Graph engine for citation traversal

use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use std::collections::HashMap;

use crate::models::{CitationEdge, EdgeType};

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_engine_is_empty() {
        let engine = GraphEngine::new();
        assert!(engine.get_neighbors("nonexistent", 1).is_empty());
    }

    #[test]
    fn add_node_returns_same_index_on_duplicate() {
        let mut engine = GraphEngine::new();
        let idx1 = engine.add_node("method-1".into());
        let idx2 = engine.add_node("method-1".into());
        assert_eq!(idx1, idx2);
    }

    #[test]
    fn add_node_creates_unique_indices() {
        let mut engine = GraphEngine::new();
        let idx1 = engine.add_node("method-1".into());
        let idx2 = engine.add_node("method-2".into());
        assert_ne!(idx1, idx2);
    }

    #[test]
    fn add_edge_creates_nodes_and_edge() {
        let mut engine = GraphEngine::new();
        engine.add_edge(CitationEdge {
            source_id: "8270D".into(),
            target_id: "8270E".into(),
            edge_type: EdgeType::Supersedes,
            confidence: 0.95,
            context: Some("Updated method".into()),
        });
        assert_eq!(engine.get_neighbors("8270D", 1), vec!["8270D"]);
        assert_eq!(engine.get_neighbors("8270D", 2), vec!["8270D", "8270E"]);
    }

    #[test]
    fn get_neighbors_returns_empty_for_unknown_node() {
        let engine = GraphEngine::new();
        assert!(engine.get_neighbors("unknown", 1).is_empty());
    }

    #[test]
    fn get_neighbors_respects_depth() {
        let mut engine = GraphEngine::new();
        engine.add_edge(CitationEdge {
            source_id: "A".into(),
            target_id: "B".into(),
            edge_type: EdgeType::References,
            confidence: 1.0,
            context: None,
        });
        engine.add_edge(CitationEdge {
            source_id: "B".into(),
            target_id: "C".into(),
            edge_type: EdgeType::References,
            confidence: 1.0,
            context: None,
        });

        assert_eq!(engine.get_neighbors("A", 1), vec!["A"]);
        assert_eq!(engine.get_neighbors("A", 2), vec!["A", "B"]);
        assert_eq!(engine.get_neighbors("A", 5), vec!["A", "B", "C"]);
    }

    #[test]
    fn get_neighbors_avoids_duplicates() {
        let mut engine = GraphEngine::new();
        engine.add_edge(CitationEdge {
            source_id: "A".into(),
            target_id: "B".into(),
            edge_type: EdgeType::References,
            confidence: 1.0,
            context: None,
        });
        engine.add_edge(CitationEdge {
            source_id: "A".into(),
            target_id: "B".into(),
            edge_type: EdgeType::SharesAnalyte,
            confidence: 0.8,
            context: None,
        });

        let neighbors = engine.get_neighbors("A", 2);
        assert_eq!(neighbors.len(), 2);
        assert_eq!(neighbors[0], "A");
        assert_eq!(neighbors[1], "B");
    }

    #[test]
    fn get_neighbors_depth_zero_returns_empty() {
        let mut engine = GraphEngine::new();
        engine.add_edge(CitationEdge {
            source_id: "A".into(),
            target_id: "B".into(),
            edge_type: EdgeType::References,
            confidence: 1.0,
            context: None,
        });
        assert!(engine.get_neighbors("A", 0).is_empty());
    }

    #[test]
    fn graph_engine_default_works() {
        let engine = GraphEngine::default();
        assert!(engine.get_neighbors("anything", 1).is_empty());
    }

    #[test]
    fn citation_edge_serialization() {
        let edge = CitationEdge {
            source_id: "src".into(),
            target_id: "tgt".into(),
            edge_type: EdgeType::CitesSection,
            confidence: 0.9,
            context: Some("section 1.2".into()),
        };
        let json = serde_json::to_string(&edge).unwrap();
        let parsed: CitationEdge = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.source_id, "src");
        assert_eq!(parsed.target_id, "tgt");
        assert!(matches!(parsed.edge_type, EdgeType::CitesSection));
        assert_eq!(parsed.confidence, 0.9);
    }
}
