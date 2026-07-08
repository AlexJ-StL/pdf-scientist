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
    // Cloud settings
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