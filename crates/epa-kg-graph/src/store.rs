//! SQLite persistence for citation graph

use crate::engine::GraphEngine;
use crate::models::{CitationEdge, EdgeType};
use anyhow::Result;
use rusqlite::{params, Connection};
use std::collections::HashMap;
use std::path::Path;
use tracing::info;

/// SQLite-backed graph store
pub struct GraphStore {
    conn: Connection,
    engine: GraphEngine,
}

impl GraphStore {
    /// Open or create a graph database at the given path
    pub fn new<P: AsRef<Path>>(path: P) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "PRAGMA foreign_keys = ON;
             PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;",
        )?;

        let mut store = Self {
            conn,
            engine: GraphEngine::new(),
        };
        store.init_schema()?;
        store.load_into_engine()?;
        info!(
            "GraphStore initialized with {} nodes",
            store.engine.node_count()
        );
        Ok(store)
    }

    /// Initialize the database schema
    fn init_schema(&mut self) -> Result<()> {
        self.conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS citation_edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                context TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_id, target_id, edge_type)
            );

            CREATE INDEX IF NOT EXISTS idx_citation_edges_source ON citation_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_citation_edges_target ON citation_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_citation_edges_type ON citation_edges(edge_type);
            "#,
        )?;
        Ok(())
    }

    /// Load all edges from SQLite into the in-memory GraphEngine
    fn load_into_engine(&mut self) -> Result<()> {
        let mut stmt = self.conn.prepare(
            "SELECT source_id, target_id, edge_type, confidence, context FROM citation_edges",
        )?;

        let edges = stmt.query_map([], |row| {
            Ok(CitationEdge {
                source_id: row.get(0)?,
                target_id: row.get(1)?,
                edge_type: row
                    .get::<_, String>(2)?
                    .parse()
                    .unwrap_or(EdgeType::References),
                confidence: row.get(3)?,
                context: row.get(4)?,
            })
        })?;

        for edge in edges {
            self.engine.add_edge(edge?);
        }

        Ok(())
    }

    /// Persist a citation edge to the database
    pub fn upsert_edge(&mut self, edge: &CitationEdge) -> Result<()> {
        self.conn.execute(
            r#"
            INSERT INTO citation_edges (source_id, target_id, edge_type, confidence, context)
            VALUES (?1, ?2, ?3, ?4, ?5)
            ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                confidence = excluded.confidence,
                context = excluded.context
            "#,
            params![
                edge.source_id,
                edge.target_id,
                edge.edge_type.to_string(),
                edge.confidence,
                edge.context,
            ],
        )?;

        // Also add to in-memory engine
        self.engine.add_edge(edge.clone());
        Ok(())
    }

    /// Persist multiple edges in a transaction
    pub fn upsert_edges(&mut self, edges: &[CitationEdge]) -> Result<()> {
        let tx = self.conn.transaction()?;
        for edge in edges {
            tx.execute(
                r#"
                INSERT INTO citation_edges (source_id, target_id, edge_type, confidence, context)
                VALUES (?1, ?2, ?3, ?4, ?5)
                ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                    confidence = excluded.confidence,
                    context = excluded.context
                "#,
                params![
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type.to_string(),
                    edge.confidence,
                    edge.context,
                ],
            )?;
            self.engine.add_edge(edge.clone());
        }
        tx.commit()?;
        Ok(())
    }

    /// Get all edges from the database
    pub fn get_all_edges(&self) -> Result<Vec<CitationEdge>> {
        let mut stmt = self.conn.prepare(
            "SELECT source_id, target_id, edge_type, confidence, context FROM citation_edges",
        )?;

        let edges = stmt.query_map([], |row| {
            Ok(CitationEdge {
                source_id: row.get(0)?,
                target_id: row.get(1)?,
                edge_type: row
                    .get::<_, String>(2)?
                    .parse()
                    .unwrap_or(EdgeType::References),
                confidence: row.get(3)?,
                context: row.get(4)?,
            })
        })?;

        let mut result = Vec::new();
        for edge in edges {
            result.push(edge?);
        }
        Ok(result)
    }

    /// Get edges by source method
    pub fn get_edges_from_method(&self, method: &str) -> Result<Vec<CitationEdge>> {
        let pattern = format!("METHOD_{}_%", method.to_uppercase());
        let mut stmt = self.conn.prepare(
            "SELECT source_id, target_id, edge_type, confidence, context FROM citation_edges WHERE source_id LIKE ?1"
        )?;

        let edges = stmt.query_map([pattern], |row| {
            Ok(CitationEdge {
                source_id: row.get(0)?,
                target_id: row.get(1)?,
                edge_type: row
                    .get::<_, String>(2)?
                    .parse()
                    .unwrap_or(EdgeType::References),
                confidence: row.get(3)?,
                context: row.get(4)?,
            })
        })?;

        let mut result = Vec::new();
        for edge in edges {
            result.push(edge?);
        }
        Ok(result)
    }

    /// Get edges by target method
    pub fn get_edges_to_method(&self, method: &str) -> Result<Vec<CitationEdge>> {
        let target_id = format!("METHOD_{}", method.to_uppercase());
        let mut stmt = self.conn.prepare(
            "SELECT source_id, target_id, edge_type, confidence, context FROM citation_edges WHERE target_id = ?1"
        )?;

        let edges = stmt.query_map([target_id], |row| {
            Ok(CitationEdge {
                source_id: row.get(0)?,
                target_id: row.get(1)?,
                edge_type: row
                    .get::<_, String>(2)?
                    .parse()
                    .unwrap_or(EdgeType::References),
                confidence: row.get(3)?,
                context: row.get(4)?,
            })
        })?;

        let mut result = Vec::new();
        for edge in edges {
            result.push(edge?);
        }
        Ok(result)
    }

    /// Get the in-memory GraphEngine for traversal
    pub fn engine(&self) -> &GraphEngine {
        &self.engine
    }

    /// Get a mutable reference to the engine for adding nodes
    pub fn engine_mut(&mut self) -> &mut GraphEngine {
        &mut self.engine
    }

    /// Build a GraphEngine from current database state (fresh load)
    pub fn build_engine(&self) -> GraphEngine {
        let mut engine = GraphEngine::new();
        if let Ok(edges) = self.get_all_edges() {
            for edge in edges {
                engine.add_edge(edge);
            }
        }
        engine
    }

    /// Print ASCII tree for a method
    pub fn print_graph_tree(&self, method: &str, depth: usize) {
        let engine = self.build_engine();
        let neighbors = engine.get_neighbors(method, depth);

        println!("Citation graph for {} (depth {}):", method, depth);
        if neighbors.is_empty() {
            println!("  (no connections found)");
            return;
        }

        // Get all edges to show relationship types
        let all_edges = self.get_all_edges().unwrap_or_default();
        let mut edge_map: HashMap<(String, String), Vec<EdgeType>> = HashMap::new();
        for edge in &all_edges {
            edge_map
                .entry((edge.source_id.clone(), edge.target_id.clone()))
                .or_default()
                .push(edge.edge_type.clone());
        }

        for (i, node) in neighbors.iter().enumerate() {
            let indent = if i == 0 { "" } else { "  " };
            let prefix = if i == 0 { "├─ " } else { "│  ├─ " };

            // Find relationship to previous node
            let rel_str = if i > 0 {
                let prev = &neighbors[i - 1];
                if let Some(types) = edge_map.get(&(prev.clone(), node.clone())) {
                    format!(
                        " [{}]",
                        types
                            .iter()
                            .map(|t| t.to_string())
                            .collect::<Vec<_>>()
                            .join(", ")
                    )
                } else if let Some(types) = edge_map.get(&(node.clone(), prev.clone())) {
                    format!(
                        " [{}]",
                        types
                            .iter()
                            .map(|t| t.to_string())
                            .collect::<Vec<_>>()
                            .join(", ")
                    )
                } else {
                    String::new()
                }
            } else {
                String::new()
            };

            println!("{}{}{}{}", indent, prefix, node, rel_str);
        }
    }
}

/// Wrapper around GraphEngine that maintains a SQLite-backed store
impl GraphStore {
    /// Get the underlying database connection
    pub fn connection(&self) -> &Connection {
        &self.conn
    }

    /// Get statistics about the graph
    pub fn stats(&self) -> Result<GraphStats> {
        let mut stmt = self.conn.prepare(
            "SELECT COUNT(*) as edge_count, 
                    COUNT(DISTINCT source_id) as source_count,
                    COUNT(DISTINCT target_id) as target_count
             FROM citation_edges",
        )?;

        let stats = stmt.query_row([], |row| {
            Ok(GraphStats {
                edge_count: row.get(0)?,
                source_count: row.get(1)?,
                target_count: row.get(2)?,
                node_count: self.engine.node_count(),
            })
        })?;

        Ok(stats)
    }
}

#[derive(Debug)]
pub struct GraphStats {
    pub edge_count: usize,
    pub source_count: usize,
    pub target_count: usize,
    pub node_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{CitationEdge, EdgeType};
    use tempfile::NamedTempFile;

    #[test]
    fn test_graph_store_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let store = GraphStore::new(temp_file.path()).unwrap();
        let stats = store.stats().unwrap();
        assert_eq!(stats.edge_count, 0);
    }

    #[test]
    fn test_upsert_and_retrieve_edge() {
        let temp_file = NamedTempFile::new().unwrap();
        let mut store = GraphStore::new(temp_file.path()).unwrap();

        let edge = CitationEdge {
            source_id: "METHOD_8270E_4_2_1".to_string(),
            target_id: "METHOD_3500C".to_string(),
            edge_type: EdgeType::References,
            confidence: 0.9,
            context: Some("See Method 3500C".to_string()),
        };

        store.upsert_edge(&edge).unwrap();

        let edges = store.get_all_edges().unwrap();
        assert_eq!(edges.len(), 1);
        assert_eq!(edges[0].source_id, "METHOD_8270E_4_2_1");
        assert_eq!(edges[0].target_id, "METHOD_3500C");
        assert_eq!(edges[0].confidence, 0.9);
    }

    #[test]
    fn test_upsert_edges_batch() {
        let temp_file = NamedTempFile::new().unwrap();
        let mut store = GraphStore::new(temp_file.path()).unwrap();

        let edges = vec![
            CitationEdge {
                source_id: "METHOD_8270E_4_2_1".to_string(),
                target_id: "METHOD_3500C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.9,
                context: None,
            },
            CitationEdge {
                source_id: "METHOD_8270E_4_2_1".to_string(),
                target_id: "METHOD_3600C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.85,
                context: None,
            },
            CitationEdge {
                source_id: "METHOD_8270D".to_string(),
                target_id: "METHOD_8270E".to_string(),
                edge_type: EdgeType::Supersedes,
                confidence: 0.99,
                context: Some("Updated method".to_string()),
            },
        ];

        store.upsert_edges(&edges).unwrap();

        let all_edges = store.get_all_edges().unwrap();
        assert_eq!(all_edges.len(), 3);
    }

    #[test]
    fn test_get_edges_from_method() {
        let temp_file = NamedTempFile::new().unwrap();
        let mut store = GraphStore::new(temp_file.path()).unwrap();

        let edges = vec![
            CitationEdge {
                source_id: "METHOD_8270E_4_2_1".to_string(),
                target_id: "METHOD_3500C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.9,
                context: None,
            },
            CitationEdge {
                source_id: "METHOD_8270E_7_1".to_string(),
                target_id: "METHOD_8000D".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.8,
                context: None,
            },
        ];

        store.upsert_edges(&edges).unwrap();

        let from_8270_e = store.get_edges_from_method("8270E").unwrap();
        assert_eq!(from_8270_e.len(), 2);
    }

    #[test]
    fn test_get_edges_to_method() {
        let temp_file = NamedTempFile::new().unwrap();
        let mut store = GraphStore::new(temp_file.path()).unwrap();

        let edges = vec![
            CitationEdge {
                source_id: "METHOD_8270E_4_2_1".to_string(),
                target_id: "METHOD_3500C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.9,
                context: None,
            },
            CitationEdge {
                source_id: "METHOD_8260D_1_1".to_string(),
                target_id: "METHOD_3500C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.8,
                context: None,
            },
        ];

        store.upsert_edges(&edges).unwrap();

        let to_3500_c = store.get_edges_to_method("3500C").unwrap();
        assert_eq!(to_3500_c.len(), 2);
    }

    #[test]
    fn test_supersedes_edge() {
        let temp_file = NamedTempFile::new().unwrap();
        let mut store = GraphStore::new(temp_file.path()).unwrap();

        let edge = CitationEdge {
            source_id: "METHOD_8270E".to_string(),
            target_id: "METHOD_8270D".to_string(),
            edge_type: EdgeType::Supersedes,
            confidence: 0.99,
            context: Some("8270E supersedes 8270D".to_string()),
        };

        store.upsert_edge(&edge).unwrap();

        let all_edges = store.get_all_edges().unwrap();
        assert_eq!(all_edges.len(), 1);
        assert!(matches!(all_edges[0].edge_type, EdgeType::Supersedes));
    }

    #[test]
    fn test_engine_persistence() {
        let temp_file = NamedTempFile::new().unwrap();
        {
            let mut store = GraphStore::new(temp_file.path()).unwrap();
            let edge = CitationEdge {
                source_id: "METHOD_8270E_4_2_1".to_string(),
                target_id: "METHOD_3500C".to_string(),
                edge_type: EdgeType::References,
                confidence: 0.9,
                context: None,
            };
            store.upsert_edge(&edge).unwrap();
        }

        // Reopen and verify persistence
        let store = GraphStore::new(temp_file.path()).unwrap();
        let edges = store.get_all_edges().unwrap();
        assert_eq!(edges.len(), 1);
        assert_eq!(edges[0].target_id, "METHOD_3500C");
    }
}
