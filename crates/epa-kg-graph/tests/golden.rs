//! Golden-file tests for reference extractor

use epa_kg_graph::extractor::ReferenceExtractor;
use epa_kg_graph::models::{CitationEdge, EdgeType};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct GoldenFile {
    method: String,
    sample_text: String,
    expected_edges: Vec<GoldenEdge>,
}

#[derive(Debug, Deserialize, PartialEq)]
struct GoldenEdge {
    source_id: String,
    target_id: String,
    edge_type: String,
    confidence: f32,
    context: Option<String>,
}

impl From<GoldenEdge> for CitationEdge {
    fn from(golden: GoldenEdge) -> Self {
        let edge_type = match golden.edge_type.as_str() {
            "REFERENCES" => EdgeType::References,
            "CITES_SECTION" => EdgeType::CitesSection,
            "SUPERSEDES" => EdgeType::Supersedes,
            "SHARES_ANALYTE" => EdgeType::SharesAnalyte,
            "SAME_MATRIX" => EdgeType::SameMatrix,
            "CFR_REFERENCE" => EdgeType::CfrReference,
            _ => EdgeType::References,
        };

        CitationEdge {
            source_id: golden.source_id,
            target_id: golden.target_id,
            edge_type,
            confidence: golden.confidence,
            context: golden.context,
        }
    }
}

fn load_golden_file(method: &str) -> GoldenFile {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let golden_path = PathBuf::from(manifest_dir)
        .join("tests")
        .join("golden")
        .join(format!("{}.json", method));

    let content = fs::read_to_string(&golden_path)
        .unwrap_or_else(|_| panic!("Golden file not found: {}", golden_path.display()));
    serde_json::from_str(&content).expect("Failed to parse golden file")
}

fn assert_extractor_matches_golden(method: &str) {
    let golden = load_golden_file(method);
    let extractor = ReferenceExtractor::new();
    let source_chunk_id = "chunk_1";
    let source_method = Some(golden.method.as_str());

    let edges = extractor.extract_references(source_chunk_id, &golden.sample_text, source_method);

    let expected: Vec<CitationEdge> = golden.expected_edges.into_iter().map(Into::into).collect();

    assert_eq!(
        edges.len(),
        expected.len(),
        "Edge count mismatch for method {}.\nGot: {:?}\nExpected: {:?}",
        method,
        edges,
        expected
    );

    for (i, (got, want)) in edges.iter().zip(expected.iter()).enumerate() {
        assert_eq!(
            got.source_id, want.source_id,
            "Edge {} source_id mismatch",
            i
        );
        assert_eq!(
            got.target_id, want.target_id,
            "Edge {} target_id mismatch",
            i
        );
        assert_eq!(
            got.edge_type, want.edge_type,
            "Edge {} edge_type mismatch",
            i
        );
        assert!(
            (got.confidence - want.confidence).abs() < 0.01,
            "Edge {} confidence mismatch: {} vs {}",
            i,
            got.confidence,
            want.confidence
        );
    }
}

#[test]
fn extractor_matches_golden_8270e() {
    assert_extractor_matches_golden("8270E");
}

#[test]
fn extractor_matches_golden_3500c() {
    assert_extractor_matches_golden("3500C");
}

#[test]
fn extractor_matches_golden_empty_text() {
    let golden = GoldenFile {
        method: "0000A".to_string(),
        sample_text: String::new(),
        expected_edges: vec![],
    };

    let extractor = ReferenceExtractor::new();
    let edges = extractor.extract_references("chunk_1", &golden.sample_text, Some(&golden.method));
    assert!(
        edges.is_empty(),
        "Expected no edges for empty text, got: {:?}",
        edges
    );
}

#[test]
fn golden_files_are_valid_json() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let golden_dir = PathBuf::from(manifest_dir).join("tests").join("golden");

    if !golden_dir.exists() {
        return;
    }

    for entry in fs::read_dir(golden_dir).expect("Failed to read golden directory") {
        let entry = entry.expect("Failed to read directory entry");
        let path = entry.path();
        if path.extension().map(|e| e == "json").unwrap_or(false) {
            let content = fs::read_to_string(&path)
                .unwrap_or_else(|_| panic!("Failed to read golden file: {}", path.display()));
            let _: serde_json::Value = serde_json::from_str(&content)
                .unwrap_or_else(|_| panic!("Invalid JSON in golden file: {}", path.display()));
        }
    }
}
