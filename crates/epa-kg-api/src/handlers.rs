//! API Handlers

use crate::error::{ApiError, Result};
use crate::state::AppState;
use axum::{extract::State, response::Json};
use epa_kg_core::Error as CoreError;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

const PYTHON_SERVICE_URL: &str = "http://127.0.0.1:8001";

#[derive(Deserialize, Serialize)]
pub struct QueryRequest {
    pub question: String,
    #[serde(default = "default_top_k")]
    pub top_k: usize,
    #[serde(default = "default_collection")]
    pub collection: String,
}

fn default_top_k() -> usize {
    5
}
fn default_collection() -> String {
    "epa_methods".to_string()
}

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
    let client = Client::new();
    let url = format!("{}/query", PYTHON_SERVICE_URL);

    let response = client
        .post(url)
        .json(&payload)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(ApiError(CoreError::Internal(
            format!("Python query service returned {}", response.status()),
        )));
    }

    let body: serde_json::Value = response.json().await?;
    let answer = body
        .get("answer")
        .and_then(|v| v.as_str())
        .unwrap_or("No answer")
        .to_string();

    let sources: Vec<Source> = body
        .get("sources")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|s| {
                    Some(Source {
                        method: s.get("method")?.as_str()?.to_string(),
                        section: s.get("section")?.as_str()?.to_string(),
                        chunk_index: s.get("chunk_index")?.as_u64()? as usize,
                        text: s.get("text")?.as_str()?.to_string(),
                        score: s.get("score")?.as_f64()? as f32,
                    })
                })
                .collect()
        })
        .unwrap_or_default();

    Ok(Json(QueryResponse {
        answer,
        sources,
        query_time_ms: body.get("query_time_ms").and_then(|v| v.as_u64()).unwrap_or(0) as u64,
    }))
}

#[derive(Deserialize, Serialize)]
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

fn default_chunk_size() -> usize {
    512
}
fn default_chunk_overlap() -> usize {
    64
}
fn default_toc_aware() -> bool {
    true
}

#[derive(Serialize)]
pub struct IngestResponse {
    pub status: String,
    pub documents_processed: usize,
    pub chunks_created: usize,
    pub time_ms: u64,
}

pub async fn ingest_handler(
    State(_state): State<Arc<AppState>>,
    Json(payload): Json<IngestRequest>,
) -> Result<Json<IngestResponse>> {
    let client = Client::new();
    let url = format!("{}/ingest", PYTHON_SERVICE_URL);

    let response = client
        .post(url)
        .json(&payload)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(ApiError(CoreError::Internal(
            format!("Python ingest service returned {}", response.status()),
        )));
    }

    let body: serde_json::Value = response.json().await?;
    Ok(Json(IngestResponse {
        status: body
            .get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("accepted")
            .to_string(),
        documents_processed: body
            .get("documents_processed")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as usize,
        chunks_created: body
            .get("chunks_created")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as usize,
        time_ms: body
            .get("time_ms")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u64,
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
    async fn query_handler_requires_python_service() {
        let state = AppState::new();
        let request = QueryRequest {
            question: "test".into(),
            top_k: 5,
            collection: "epa_methods".into(),
        };
        let result = query_handler(State(state.clone()), Json(request)).await;
        // This will fail without the Python service running on port 8001
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn ingest_handler_requires_python_service() {
        let state = AppState::new();
        let request = IngestRequest {
            pdf_dir: "/tmp".into(),
            collection: "epa_methods".into(),
            force_reindex: false,
            chunk_size: 512,
            chunk_overlap: 64,
            toc_aware: true,
        };
        let result = ingest_handler(State(state.clone()), Json(request)).await;
        // This will fail without the Python service running on port 8001
        assert!(result.is_err());
    }

    #[test]
    fn query_request_deserializes() {
        let json =
            r#"{"question":"What is EPA Method 8270?","top_k":3,"collection":"epa_methods"}"#;
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
