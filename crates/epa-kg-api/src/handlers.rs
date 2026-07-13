//! API Handlers

use axum::{
    extract::State,
    response::Json,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::error::Result;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct QueryRequest {
    pub question: String,
    #[serde(default = "default_top_k")]
    pub top_k: usize,
    #[serde(default = "default_collection")]
    pub collection: String,
}

fn default_top_k() -> usize { 5 }
fn default_collection() -> String { "epa_methods".to_string() }

#[derive(Serialize)]
pub struct QueryResponse {
    pub answer: String,
    pub sources: Vec<Source>,
    pub query_time_ms: u64,
}

#[derive(Serialize)]
pub struct Source {
    pub method: String,
    pub section: String,
    pub chunk_index: usize,
    pub text: String,
    pub score: f32,
}

pub async fn query_handler(
    State(_state): State<Arc<AppState>>,
    Json(payload): Json<QueryRequest>,
) -> Result<Json<QueryResponse>> {
    // TODO: Implement actual query against ChromaDB
    Ok(Json(QueryResponse {
        answer: format!("Query '{}' received (not yet implemented)", payload.question),
        sources: vec![],
        query_time_ms: 0,
    }))
}

#[derive(Deserialize)]
pub struct IngestRequest {
    pub pdf_dir: String,
    pub collection: String,
    #[serde(default)]
    pub force_reindex: bool,
    #[serde(default = "default_chunk_size")]
    pub chunk_size: usize,
    #[serde(default = "default_chunk_overlap")]
    pub chunk_overlap: usize,
    #[serde(default = "default_toc_aware")]
    pub toc_aware: bool,
}

fn default_chunk_size() -> usize { 512 }
fn default_chunk_overlap() -> usize { 64 }
fn default_toc_aware() -> bool { true }

#[derive(Serialize)]
pub struct IngestResponse {
    pub status: String,
    pub documents_processed: usize,
    pub chunks_created: usize,
    pub time_ms: u64,
}

pub async fn ingest_handler(
    State(_state): State<Arc<AppState>>,
    Json(_payload): Json<IngestRequest>,
) -> Result<Json<IngestResponse>> {
    // TODO: Forward to Python ingestion service
    Ok(Json(IngestResponse {
        status: "accepted".to_string(),
        documents_processed: 0,
        chunks_created: 0,
        time_ms: 0,
    }))
}

pub async fn health_handler() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::AppState;

    #[tokio::test]
    async fn health_handler_returns_ok() {
        let response = health_handler().await;
        let body = response.0;
        assert_eq!(body["status"], "ok");
    }

    #[tokio::test]
    async fn query_handler_returns_placeholder() {
        let state = AppState::new();
        let request = QueryRequest { question: "test".into(), top_k: 5, collection: "epa_methods".into() };
        let result = query_handler(State(state.clone()), Json(request)).await;
        assert!(result.is_ok());
        let body = result.unwrap().0;
        assert!(body.answer.contains("test"));
    }

    #[tokio::test]
    async fn ingest_handler_returns_accepted() {
        let state = AppState::new();
        let request = IngestRequest { pdf_dir: "/tmp".into(), collection: "epa_methods".into(), force_reindex: false, chunk_size: 512, chunk_overlap: 64, toc_aware: true };
        let result = ingest_handler(State(state.clone()), Json(request)).await;
        assert!(result.is_ok());
        let body = result.unwrap().0;
        assert_eq!(body.status, "accepted");
    }

    #[test]
    fn query_request_deserializes() {
        let json = r#"{"question":"What is EPA Method 8270?","top_k":3,"collection":"epa_methods"}"#;
        let req: QueryRequest = serde_json::from_str(json).unwrap();
        assert_eq!(req.question, "What is EPA Method 8270?");
        assert_eq!(req.top_k, 3);
    }

    #[test]
    fn query_request_defaults() {
        let json = r#"{"question":"test"}"#;
        let req: QueryRequest = serde_json::from_str(json).unwrap();
        assert_eq!(req.top_k, 5);
        assert_eq!(req.collection, "epa_methods");
    }

    #[test]
    fn ingest_request_defaults() {
        let json = r#"{"pdf_dir":"/tmp","collection":"epa_methods"}"#;
        let req: IngestRequest = serde_json::from_str(json).unwrap();
        assert_eq!(req.chunk_size, 512);
        assert_eq!(req.chunk_overlap, 64);
        assert!(req.toc_aware);
        assert!(!req.force_reindex);
    }
}