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
    Json(payload): Json<IngestRequest>,
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