//! API error type bridging core errors to Axum responses

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use epa_kg_core::Error as CoreError;
use serde_json::json;

/// Wraps a core error so handlers can return Axum-compatible responses.
#[derive(Debug)]
pub struct ApiError(pub CoreError);

impl From<CoreError> for ApiError {
    fn from(err: CoreError) -> Self {
        ApiError(err)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = match &self.0 {
            CoreError::NotFound(_) => StatusCode::NOT_FOUND,
            CoreError::Validation(_) => StatusCode::BAD_REQUEST,
            CoreError::Config(_)
            | CoreError::Io(_)
            | CoreError::Database(_)
            | CoreError::Chroma(_)
            | CoreError::PdfParse(_)
            | CoreError::Embedding(_)
            | CoreError::Llm(_)
            | CoreError::Ingestion(_)
            | CoreError::Graph(_)
            | CoreError::Internal(_)
            | CoreError::Serialization(_)
            | CoreError::UrlParse(_)
            | CoreError::Uuid(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };
        let body = json!({ "error": self.0.to_string() });
        (status, Json(body)).into_response()
    }
}

pub type Result<T> = std::result::Result<T, ApiError>;
