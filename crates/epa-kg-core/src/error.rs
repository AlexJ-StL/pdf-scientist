//! Error types for EPA Knowledge Graph

use thiserror::Error;

#[derive(Error, Debug)]
pub enum Error {
    #[error("Configuration error: {0}")]
    Config(#[from] config::ConfigError),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("ChromaDB error: {0}")]
    Chroma(String),

    #[error("PDF parsing error: {0}")]
    PdfParse(String),

    #[error("Embedding error: {0}")]
    Embedding(String),

    #[error("LLM error: {0}")]
    Llm(String),

    #[error("Ingestion error: {0}")]
    Ingestion(String),

    #[error("Graph error: {0}")]
    Graph(String),

    #[error("Validation error: {0}")]
    Validation(#[from] validator::ValidationErrors),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("URL parse error: {0}")]
    UrlParse(#[from] url::ParseError),

    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),

    #[error("UUID error: {0}")]
    Uuid(#[from] uuid::Error),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl From<anyhow::Error> for Error {
    fn from(err: anyhow::Error) -> Self {
        Error::Internal(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, Error>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn config_error_displays_correctly() {
        let err = Error::Config(config::ConfigError::NotFound("missing".into()));
        assert!(err.to_string().contains("Configuration error"));
    }

    #[test]
    fn io_error_conversion() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
        let err = Error::from(io_err);
        assert!(err.to_string().contains("IO error"));
    }

    #[test]
    fn chroma_error_message() {
        let err = Error::Chroma("connection refused".into());
        assert_eq!(err.to_string(), "ChromaDB error: connection refused");
    }

    #[test]
    fn pdf_parse_error_message() {
        let err = Error::PdfParse("invalid PDF header".into());
        assert_eq!(err.to_string(), "PDF parsing error: invalid PDF header");
    }

    #[test]
    fn embedding_error_message() {
        let err = Error::Embedding("model not loaded".into());
        assert_eq!(err.to_string(), "Embedding error: model not loaded");
    }

    #[test]
    fn llm_error_message() {
        let err = Error::Llm("rate limited".into());
        assert_eq!(err.to_string(), "LLM error: rate limited");
    }

    #[test]
    fn ingestion_error_message() {
        let err = Error::Ingestion("empty PDF".into());
        assert_eq!(err.to_string(), "Ingestion error: empty PDF");
    }

    #[test]
    fn graph_error_message() {
        let err = Error::Graph("cycle detected".into());
        assert_eq!(err.to_string(), "Graph error: cycle detected");
    }

    #[test]
    fn not_found_error_message() {
        let err = Error::NotFound("method 8270E".into());
        assert_eq!(err.to_string(), "Not found: method 8270E");
    }

    #[test]
    fn internal_error_message() {
        let err = Error::Internal("unexpected state".into());
        assert_eq!(err.to_string(), "Internal error: unexpected state");
    }

    #[test]
    fn result_type_alias_works() {
        fn returns_ok() -> Result<i32> {
            Ok(42)
        }
        fn returns_err() -> Result<i32> {
            Err(Error::Internal("boom".into()))
        }
        assert_eq!(returns_ok().unwrap(), 42);
        assert!(returns_err().is_err());
    }

    #[test]
    fn error_debug_does_not_panic() {
        let err = Error::Ingestion("test".into());
        let debug = format!("{:?}", err);
        assert!(debug.contains("Ingestion"));
    }
}
