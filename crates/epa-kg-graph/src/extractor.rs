//! Reference extractor for finding cross-references in EPA method text

use crate::models::{CitationEdge, EdgeType};
use regex::Regex;
use std::collections::HashSet;

pub struct ReferenceExtractor {
    // Regex patterns for different reference types
    method_pattern: Regex,
    section_pattern: Regex,
    sw846_pattern: Regex,
    supersedes_pattern: Regex,
    cfr_pattern: Regex,
}

impl ReferenceExtractor {
    pub fn new() -> Self {
        Self {
            // Matches "Method 8270E", "EPA Method 8270E", "SW-846 8270E"
            method_pattern: Regex::new(
                r"(?i)(?:EPA\s+)?(?:Method|SW-846)\s+(\d{4}[A-Z]?)\b",
            ).unwrap(),
            // Matches "Section 4.2.1", "§4.2.1", "Sec. 4.2.1"
            section_pattern: Regex::new(
                r"(?i)(?:Section|Sec\.|§)\s+(\d+(?:\.\d+)+)\b",
            ).unwrap(),
            // Matches "SW-846 3500C", "SW-846 8000D"
            sw846_pattern: Regex::new(
                r"(?i)SW-846\s+(\d{4}[A-Z]?)\b",
            ).unwrap(),
            supersedes_pattern: Regex::new(
                r"(?i)(?:Method\s+)?(\d{4}[A-Z]?)\s+(?:supersedes?|replaces?)\s+(?:Method\s+)?(\d{4}[A-Z]?)",
            ).unwrap(),
            cfr_pattern: Regex::new(
                r"(?i)(\d+)\s+CFR\s+(?:§\s+)?(?:Part\s+)?(\d+(?:\.\d+)*)",
            ).unwrap(),
        }
    }

    /// Extract all citation edges from a chunk of text
    pub fn extract_references(
        &self,
        source_chunk_id: &str,
        text: &str,
        source_method: Option<&str>,
    ) -> Vec<CitationEdge> {
        let mut edges = Vec::new();
        let mut seen = HashSet::new();

        // Extract method references
        for cap in self.method_pattern.captures_iter(text) {
            if let Some(method_match) = cap.get(1) {
                let target_method = method_match.as_str().to_uppercase();

                // Skip self-references
                if let Some(src) = source_method {
                    if target_method == src.to_uppercase() {
                        continue;
                    }
                }

                let edge = self.create_edge(
                    source_chunk_id,
                    &target_method,
                    EdgeType::References,
                    0.9,
                    cap.get(0).map(|m| m.as_str().to_string()),
                    source_method,
                );
                if seen
                    .insert(edge.source_id.clone() + &edge.target_id + &edge.edge_type.to_string())
                {
                    edges.push(edge);
                }
            }
        }

        // Extract SW-846 references
        for cap in self.sw846_pattern.captures_iter(text) {
            if let Some(method_match) = cap.get(1) {
                let target_method = method_match.as_str().to_uppercase();

                // Skip self-references
                if let Some(src) = source_method {
                    if target_method == src.to_uppercase() {
                        continue;
                    }
                }

                let edge = self.create_edge(
                    source_chunk_id,
                    &target_method,
                    EdgeType::References,
                    0.95,
                    cap.get(0).map(|m| m.as_str().to_string()),
                    source_method,
                );
                if seen
                    .insert(edge.source_id.clone() + &edge.target_id + &edge.edge_type.to_string())
                {
                    edges.push(edge);
                }
            }
        }

        // Extract section references (need source method to construct full target)
        if let Some(src_method) = source_method {
            for cap in self.section_pattern.captures_iter(text) {
                if let Some(section_match) = cap.get(1) {
                    let section = section_match.as_str();
                    let target = format!("{}_{}", src_method, section.replace('.', "_"));
                    let edge = self.create_edge(
                        source_chunk_id,
                        &target,
                        EdgeType::CitesSection,
                        0.85,
                        cap.get(0).map(|m| m.as_str().to_string()),
                        source_method,
                    );
                    if seen.insert(
                        edge.source_id.clone() + &edge.target_id + &edge.edge_type.to_string(),
                    ) {
                        edges.push(edge);
                    }
                }
            }
        }

        // Extract supersedes relationships
        if let Some(src_method) = source_method {
            for cap in self.supersedes_pattern.captures_iter(text) {
                if let (Some(new_method), Some(old_method)) = (cap.get(1), cap.get(2)) {
                    let new_method_str = new_method.as_str().to_uppercase();
                    let old_method_str = old_method.as_str().to_uppercase();

                    // Skip self-references
                    if new_method_str == old_method_str {
                        continue;
                    }

                    let source_id =
                        format!("METHOD_{}_{}", src_method.to_uppercase(), source_chunk_id);
                    let edge = CitationEdge {
                        source_id,
                        target_id: format!("METHOD_{}", old_method_str),
                        edge_type: EdgeType::Supersedes,
                        confidence: 0.95,
                        context: cap.get(0).map(|m| m.as_str().to_string()),
                    };

                     let edge_key =
                         format!("{}{}{}", edge.source_id, edge.target_id, edge.edge_type);
                     if seen.insert(edge_key) {
                         edges.push(edge);
                     }
                 }
             }
         }

         // Extract CFR references
         for cap in self.cfr_pattern.captures_iter(text) {
             if let (Some(title), Some(section)) = (cap.get(1), cap.get(2)) {
                 let cfr_title = title.as_str();
                 let cfr_section = section.as_str();
                 let target_id = format!("CFR_{}_{}", cfr_title, cfr_section.replace('.', "_"));
                 let context = cap.get(0).map(|m| m.as_str().to_string());

                 let source_id = if let Some(src_method) = source_method {
                     format!("METHOD_{}_{}", src_method.to_uppercase(), source_chunk_id)
                 } else {
                     source_chunk_id.to_string()
                 };

                 let edge = CitationEdge {
                     source_id,
                     target_id,
                     edge_type: EdgeType::CfrReference,
                     confidence: 0.9,
                     context,
                 };

                 let edge_key =
                     format!("{}{}{}", edge.source_id, edge.target_id, edge.edge_type);
                 if seen.insert(edge_key) {
                     edges.push(edge);
                 }
             }
         }

         edges
     }

    /// Create a citation edge with proper IDs
    fn create_edge(
        &self,
        source_chunk_id: &str,
        target_method: &str,
        edge_type: EdgeType,
        confidence: f32,
        context: Option<String>,
        source_method: Option<&str>,
    ) -> CitationEdge {
        let source_id = if let Some(src_method) = source_method {
            format!("METHOD_{}_{}", src_method.to_uppercase(), source_chunk_id)
        } else {
            source_chunk_id.to_string()
        };

        let target_id = format!("METHOD_{}", target_method);

        CitationEdge {
            source_id,
            target_id,
            edge_type,
            confidence,
            context,
        }
    }

    /// Find supersession relationships (Method X supersedes Method Y)
    pub fn find_supersedes(&self, text: &str) -> Vec<(String, String)> {
        let mut results = Vec::new();
        // Pattern: "Method 8270E supersedes Method 8270D" or "replaces 8270D"
        let supersedes_pattern = Regex::new(
            r"(?i)(?:Method\s+)?(\d{4}[A-Z]?)\s+(?:supersedes?|replaces?)\s+(?:Method\s+)?(\d{4}[A-Z]?)"
        ).unwrap();

        for cap in supersedes_pattern.captures_iter(text) {
            if let (Some(new_method), Some(old_method)) = (cap.get(1), cap.get(2)) {
                results.push((
                    new_method.as_str().to_uppercase(),
                    old_method.as_str().to_uppercase(),
                ));
            }
        }
        results
    }

    /// Find shared analytes between methods
    pub fn find_shared_analytes(&self, text: &str) -> Vec<String> {
        let mut analytes = Vec::new();
        // Common analyte patterns in EPA methods
        let analyte_keywords = [
            "PAH",
            "PCB",
            "dioxin",
            "furan",
            "phenol",
            "phthalate",
            "benzene",
            "toluene",
            "xylene",
            "naphthalene",
            "anthracene",
            "fluoranthene",
            "pyrene",
            "chrysene",
            "benzo",
            "indeno",
            "dibenz",
            "metals",
            "mercury",
            "lead",
            "arsenic",
            "cadmium",
            "chromium",
            "selenium",
            "silver",
            "barium",
            "copper",
            "zinc",
            "cyanide",
            "sulfide",
            "pesticide",
            "herbicide",
            "VOC",
            "SVOC",
        ];

        let text_lower = text.to_lowercase();
        for analyte in &analyte_keywords {
            if text_lower.contains(&analyte.to_lowercase()) {
                analytes.push(analyte.to_string());
            }
        }
        analytes
    }
}

impl Default for ReferenceExtractor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_method_references() {
        let extractor = ReferenceExtractor::new();
        let text = "This method references Method 3500C and SW-846 3600C for sample preparation.";
        let edges = extractor.extract_references("chunk_1", text, Some("8270E"));

        assert!(edges.iter().any(|e| e.target_id == "METHOD_3500C"));
        assert!(edges.iter().any(|e| e.target_id == "METHOD_3600C"));
    }

    #[test]
    fn extract_section_references() {
        let extractor = ReferenceExtractor::new();
        let text = "See Section 4.2.1 for sample preparation and Section 7.3 for analysis.";
        let edges = extractor.extract_references("chunk_1", text, Some("8270E"));

        assert!(edges.iter().any(|e| e.target_id == "METHOD_8270E_4_2_1"));
        assert!(edges.iter().any(|e| e.target_id == "METHOD_8270E_7_3"));
        assert!(edges
            .iter()
            .any(|e| matches!(e.edge_type, EdgeType::CitesSection)));
    }

    #[test]
    fn find_supersedes() {
        let extractor = ReferenceExtractor::new();
        let text = "Method 8270E supersedes Method 8270D. Method 8260D replaces 8260C.";
        let supersedes = extractor.find_supersedes(text);

        assert_eq!(supersedes.len(), 2);
        assert!(supersedes.contains(&("8270E".to_string(), "8270D".to_string())));
        assert!(supersedes.contains(&("8260D".to_string(), "8260C".to_string())));
    }

    #[test]
    fn extract_cfr_references() {
        let extractor = ReferenceExtractor::new();
        let text =
            "See 40 CFR 261.24 for toxicity characteristic and 40 CFR Part 264 for standards.";
        let edges = extractor.extract_references("chunk_1", text, Some("8270E"));
        assert!(edges.iter().any(|e| e.edge_type == EdgeType::CfrReference));
        assert!(edges.iter().any(|e| e.target_id == "CFR_40_261_24"));
        assert!(edges.iter().any(|e| e.target_id == "CFR_40_264"));
    }
}
