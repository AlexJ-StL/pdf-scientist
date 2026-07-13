//! Configuration management for EPA Knowledge Graph

use config::{Config, Environment, File};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub app: AppSettings,
    pub database: DatabaseSettings,
    pub chroma: ChromaSettings,
    pub ingestion: IngestionSettings,
    pub embedding: EmbeddingSettings,
    pub llm: LlmSettings,
}

#[allow(clippy::derivable_impls)]
impl Default for Settings {
    fn default() -> Self {
        Self {
            app: AppSettings::default(),
            database: DatabaseSettings::default(),
            chroma: ChromaSettings::default(),
            ingestion: IngestionSettings::default(),
            embedding: EmbeddingSettings::default(),
            llm: LlmSettings::default(),
        }
    }
}

impl Settings {
    pub fn load() -> crate::Result<Self> {
        let mut builder = Config::builder()
            .add_source(File::with_name("config").required(false))
            .add_source(File::with_name(".env").required(false))
            .add_source(Environment::with_prefix("EPA_KG").separator("__"));

        // Allow .env file override
        if std::path::Path::new(".env").exists() {
            builder = builder.add_source(File::with_name(".env").required(false));
        }

        let settings: Settings = builder.build()?.try_deserialize()?;
        Ok(settings)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub host: String,
    pub port: u16,
    pub log_level: String,
    pub data_dir: PathBuf,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".into(),
            port: 8080,
            log_level: "info".into(),
            data_dir: PathBuf::from("./data"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseSettings {
    pub url: String,
    pub max_connections: u32,
    pub min_connections: u32,
}

impl Default for DatabaseSettings {
    fn default() -> Self {
        Self {
            url: "postgresql://postgres:***@localhost:5432/epa_kg".into(),
            max_connections: 10,
            min_connections: 1,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChromaSettings {
    pub host: String,
    pub port: u16,
    pub collection_name: String,
    pub persist_dir: PathBuf,
    pub use_cloud: bool,
    pub api_key: Option<String>,
    pub tenant: Option<String>,
    pub database: Option<String>,
}

impl Default for ChromaSettings {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".into(),
            port: 8000,
            collection_name: "epa_methods".into(),
            persist_dir: PathBuf::from("./data/chroma"),
            use_cloud: false,
            api_key: None,
            tenant: None,
            database: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionSettings {
    pub pdf_dir: PathBuf,
    pub chunk_size: usize,
    pub chunk_overlap: usize,
    pub toc_aware: bool,
    pub extract_tables: bool,
    pub max_file_size_mb: u64,
}

impl Default for IngestionSettings {
    fn default() -> Self {
        Self {
            pdf_dir: PathBuf::from("./epa-methods"),
            chunk_size: 512,
            chunk_overlap: 64,
            toc_aware: true,
            extract_tables: true,
            max_file_size_mb: 100,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "provider")]
pub enum EmbeddingSettings {
    OpenRouter {
        api_key: String,
        model: String,
        dimensions: Option<usize>,
        batch_size: usize,
    },
    Ollama {
        host: String,
        model: String,
        batch_size: usize,
    },
    FastEmbed {
        model: String,
        batch_size: usize,
    },
}

impl Default for EmbeddingSettings {
    fn default() -> Self {
        Self::FastEmbed {
            model: "BAAI/bge-small-en-v1.5".into(),
            batch_size: 32,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "provider")]
pub enum LlmSettings {
    OpenRouter {
        api_key: String,
        model: String,
        temperature: f32,
        max_tokens: usize,
    },
    Ollama {
        host: String,
        model: String,
        temperature: f32,
        max_tokens: usize,
    },
    None,
}

impl Default for LlmSettings {
    fn default() -> Self {
        Self::Ollama {
            host: "http://localhost:11434".into(),
            model: "llama3.2:3b".into(),
            temperature: 0.1,
            max_tokens: 2048,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settings_defaults_are_sensible() {
        let settings = Settings::default();
        assert_eq!(settings.app.host, "127.0.0.1");
        assert_eq!(settings.app.port, 8080);
        assert_eq!(settings.chroma.port, 8000);
        assert_eq!(settings.chroma.collection_name, "epa_methods");
        assert_eq!(settings.ingestion.chunk_size, 512);
        assert_eq!(settings.ingestion.chunk_overlap, 64);
        assert!(settings.ingestion.toc_aware);
        assert!(matches!(settings.embedding, EmbeddingSettings::FastEmbed { .. }));
        assert!(matches!(settings.llm, LlmSettings::Ollama { .. }));
    }

    #[test]
    fn app_settings_defaults() {
        let app = AppSettings::default();
        assert_eq!(app.host, "127.0.0.1");
        assert_eq!(app.port, 8080);
        assert_eq!(app.log_level, "info");
        assert_eq!(app.data_dir, PathBuf::from("./data"));
    }

    #[test]
    fn chroma_settings_defaults() {
        let chroma = ChromaSettings::default();
        assert_eq!(chroma.host, "127.0.0.1");
        assert_eq!(chroma.port, 8000);
        assert!(!chroma.use_cloud);
        assert!(chroma.api_key.is_none());
    }

    #[test]
    fn embedding_settings_defaults() {
        let embedding = EmbeddingSettings::default();
        match embedding {
            EmbeddingSettings::FastEmbed { model, batch_size } => {
                assert_eq!(model, "BAAI/bge-small-en-v1.5");
                assert_eq!(batch_size, 32);
            }
            _ => panic!("Expected FastEmbed default"),
        }
    }

    #[test]
    fn llm_settings_defaults() {
        let llm = LlmSettings::default();
        match llm {
            LlmSettings::Ollama { host, model, temperature, max_tokens } => {
                assert_eq!(host, "http://localhost:11434");
                assert_eq!(model, "llama3.2:3b");
                assert!((temperature - 0.1).abs() < f32::EPSILON);
                assert_eq!(max_tokens, 2048);
            }
            _ => panic!("Expected Ollama default"),
        }
    }

    #[test]
    fn embedding_settings_serde_round_trip() {
        let original = EmbeddingSettings::OpenRouter {
            api_key: "test-key".into(),
            model: "openai/text-embedding-3-small".into(),
            dimensions: Some(1536),
            batch_size: 16,
        };
        let json = serde_json::to_string(&original).unwrap();
        let parsed: EmbeddingSettings = serde_json::from_str(&json).unwrap();
        match parsed {
            EmbeddingSettings::OpenRouter { api_key, model, dimensions, batch_size } => {
                assert_eq!(api_key, "test-key");
                assert_eq!(model, "openai/text-embedding-3-small");
                assert_eq!(dimensions, Some(1536));
                assert_eq!(batch_size, 16);
            }
            _ => panic!("Round-trip changed variant"),
        }
    }

    #[test]
    fn llm_settings_serde_round_trip() {
        let original = LlmSettings::None;
        let json = serde_json::to_string(&original).unwrap();
        let parsed: LlmSettings = serde_json::from_str(&json).unwrap();
        assert!(matches!(parsed, LlmSettings::None));
    }

    #[test]
    fn settings_default_serialization_matches_structure() {
        let settings = Settings::default();
        let json = serde_json::to_string(&settings).expect("serialize");
        let parsed: Settings = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(parsed.app.host, settings.app.host);
        assert_eq!(parsed.database.max_connections, settings.database.max_connections);
        assert_eq!(parsed.chroma.collection_name, settings.chroma.collection_name);
        assert_eq!(parsed.ingestion.chunk_size, settings.ingestion.chunk_size);
        assert_eq!(parsed.ingestion.chunk_overlap, settings.ingestion.chunk_overlap);
        assert!(matches!(parsed.embedding, EmbeddingSettings::FastEmbed { .. }));
        assert!(matches!(parsed.llm, LlmSettings::Ollama { .. }));
    }

    #[test]
    fn embedding_settings_variants_serialize_distinctly() {
        let fast = EmbeddingSettings::FastEmbed { model: "BGE".into(), batch_size: 16 };
        let or = EmbeddingSettings::OpenRouter { api_key: "k".into(), model: "m".into(), dimensions: None, batch_size: 8 };
        let ol = EmbeddingSettings::Ollama { host: "http://localhost".into(), model: "nomic".into(), batch_size: 4 };
        let fast_json = serde_json::to_string(&fast).unwrap();
        let or_json = serde_json::to_string(&or).unwrap();
        let ol_json = serde_json::to_string(&ol).unwrap();
        assert!(fast_json.contains("\"FastEmbed\"") || fast_json.contains("FastEmbed"));
        assert!(or_json.contains("\"OpenRouter\"") || or_json.contains("OpenRouter"));
        assert!(ol_json.contains("\"Ollama\"") || ol_json.contains("Ollama"));
        assert_ne!(fast_json, or_json);
        assert_ne!(or_json, ol_json);
    }

    #[test]
    fn llm_settings_none_variant_serializes() {
        let none = LlmSettings::None;
        let json = serde_json::to_string(&none).unwrap();
        assert!(json.contains("None") || json.contains("null"));
        let parsed: LlmSettings = serde_json::from_str(&json).unwrap();
        assert!(matches!(parsed, LlmSettings::None));
    }

    #[test]
    fn settings_serialization_round_trip() {
        let settings = Settings::default();
        let json = serde_json::to_string(&settings).expect("serialize failed");
        let parsed: Settings = serde_json::from_str(&json).expect("deserialize failed");
        assert_eq!(parsed.app.host, settings.app.host);
        assert_eq!(parsed.chroma.port, settings.chroma.port);
    }
}