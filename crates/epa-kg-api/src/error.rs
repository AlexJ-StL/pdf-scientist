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

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;

    #[test]
    fn not_found_maps_to_404() {
        let err = ApiError(CoreError::NotFound("missing".into()));
        let response = err.into_response();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[test]
    fn internal_error_maps_to_500() {
        let err = ApiError(CoreError::Internal("boom".into()));
        let response = err.into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }

    #[test]
    fn chroma_error_maps_to_500() {
        let err = ApiError(CoreError::Chroma("db down".into()));
        let response = err.into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }

    #[tokio::test]
    async fn response_body_contains_error_message() {
        let err = ApiError(CoreError::Internal("boom".into()));
        let response = err.into_response();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json["error"].as_str().unwrap().contains("Internal error"));
        assert!(json["error"].as_str().unwrap().contains("boom"));
    }

    #[test]
    fn from_core_error_works() {
        let core_err: CoreError = CoreError::NotFound("x".into());
        let api_err: ApiError = core_err.into();
        assert!(matches!(api_err.0, CoreError::NotFound(_)));
    }
}
