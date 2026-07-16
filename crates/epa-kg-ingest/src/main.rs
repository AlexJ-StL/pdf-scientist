//! EPA Knowledge Graph CLI

use clap::{Parser, Subcommand};
use epa_kg_core::{Error, Result, Settings};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "epa-kg")]
#[command(about = "EPA Knowledge Graph - Semantic search for environmental methods")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    #[arg(short = 'C', long, global = true)]
    config: Option<PathBuf>,

    #[arg(short, long, global = true)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Ingest EPA method PDFs into the vector store
    Ingest {
        #[arg(short, long, default_value = "./epa-methods")]
        pdf_dir: PathBuf,

        #[arg(short, long, default_value = "epa_methods")]
        collection: String,

        #[arg(long)]
        force_reindex: bool,
    },

    /// Query the knowledge graph
    Query {
        #[arg(short, long)]
        question: String,

        #[arg(short, long, default_value = "5")]
        top_k: usize,

        #[arg(short, long, default_value = "epa_methods")]
        collection: String,
    },

    /// Show citation graph for a method
    Graph {
        #[arg(short, long)]
        method: String,

        #[arg(short, long, default_value = "2")]
        depth: usize,
    },

    /// Run the API server
    Serve {
        #[arg(short, long, default_value = "8080")]
        port: u16,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize tracing
    let log_level = if cli.verbose { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(format!("epa_kg={},tower_http=info", log_level))
        .init();

    // Load settings
    let settings = Settings::load()?;

    match cli.command {
        Commands::Ingest {
            pdf_dir,
            collection,
            force_reindex,
        } => run_ingest(settings, pdf_dir, collection, force_reindex).await,
        Commands::Query {
            question,
            top_k,
            collection,
        } => run_query(settings, question, top_k, collection).await,
        Commands::Graph { method, depth } => run_graph(settings, method, depth).await,
        Commands::Serve { port } => run_server(settings, port).await,
    }
}

async fn run_ingest(
    settings: Settings,
    pdf_dir: PathBuf,
    collection: String,
    force_reindex: bool,
) -> Result<()> {
    tracing::info!(
        "Starting ingestion from {:?} into collection '{}'",
        pdf_dir,
        collection
    );

    if !pdf_dir.exists() {
        return Err(Error::Ingestion(format!(
            "PDF directory does not exist: {:?}",
            pdf_dir
        )));
    }

    // TODO: Call Python ingestion service via HTTP
    // For now, just log what would happen
    let pdf_files: Vec<_> = std::fs::read_dir(&pdf_dir)?
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().is_some_and(|ext| ext == "pdf"))
        .collect();

    tracing::info!("Found {} PDF files", pdf_files.len());

    for entry in &pdf_files {
        tracing::info!("  - {}", entry.file_name().to_string_lossy());
    }

    if force_reindex {
        tracing::info!("Force reindex enabled - will overwrite existing chunks");
    }

    // Call Python service
    let client = reqwest::Client::new();
    let ingest_url = format!("http://{}:{}/ingest", "127.0.0.1", 8001);

    let payload = serde_json::json!({
        "pdf_dir": pdf_dir.to_string_lossy(),
        "collection": collection,
        "force_reindex": force_reindex,
        "chunk_size": settings.ingestion.chunk_size,
        "chunk_overlap": settings.ingestion.chunk_overlap,
        "toc_aware": settings.ingestion.toc_aware,
    });

    match client.post(&ingest_url).json(&payload).send().await {
        Ok(response) => {
            if response.status().is_success() {
                tracing::info!("Ingestion completed successfully");
                let result: serde_json::Value = response
                    .json()
                    .await
                    .map_err(|e| Error::Internal(e.to_string()))?;
                tracing::info!("Result: {}", serde_json::to_string_pretty(&result)?);

                // Extract citation graph after ingestion
                if let Err(e) = extract_and_persist_graph(&settings, &collection).await {
                    tracing::warn!("Graph extraction failed: {}", e);
                }
            } else {
                tracing::error!(
                    "Ingestion failed: {}",
                    response
                        .text()
                        .await
                        .map_err(|e| Error::Internal(e.to_string()))?
                );
            }
        }
        Err(e) => {
            tracing::error!("Failed to connect to ingestion service: {}", e);
            tracing::info!("Make sure the Python ingestion service is running on port 8001");
        }
    }

    Ok(())
}

async fn extract_and_persist_graph(settings: &Settings, collection: &str) -> Result<()> {
    tracing::info!("Extracting citation graph from collection '{}'", collection);

    let client = reqwest::Client::new();
    let extract_url = format!("http://{}:{}/graph/extract", "127.0.0.1", 8001);

    let payload = serde_json::json!({
        "collection": collection,
    });

    let response = client.post(&extract_url).json(&payload).send().await?;

    if !response.status().is_success() {
        let error_text = response.text().await?;
        return Err(Error::Internal(format!(
            "Graph extraction failed: {}",
            error_text
        )));
    }

    let extract_result: serde_json::Value = response.json().await?;
    let edges_extracted = extract_result
        .get("edges_extracted")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    tracing::info!("Extracted {} citation edges", edges_extracted);

    // Persist edges to SQLite graph store
    if edges_extracted > 0 {
        if let Some(edges_array) = extract_result.get("edges").and_then(|v| v.as_array()) {
            let graph_path = settings.app.data_dir.join("citation_graph.sqlite");
            let mut store = epa_kg_graph::store::GraphStore::new(&graph_path)?;

            for edge_json in edges_array {
                let source_id = edge_json
                    .get("source_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                let target_id = edge_json
                    .get("target_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                let edge_type_str = edge_json
                    .get("edge_type")
                    .and_then(|v| v.as_str())
                    .unwrap_or("REFERENCES");

                let edge_type = edge_type_str
                    .parse::<epa_kg_graph::models::EdgeType>()
                    .unwrap_or(epa_kg_graph::models::EdgeType::References);

                let confidence = edge_json
                    .get("confidence")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0) as f32;

                let context = edge_json
                    .get("context")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());

                let edge = epa_kg_graph::models::CitationEdge {
                    source_id,
                    target_id,
                    edge_type,
                    confidence,
                    context,
                };

                store.upsert_edge(&edge)?;
            }

            tracing::info!(
                "Persisted {} edges to graph store at {:?}",
                edges_extracted,
                graph_path
            );
        }
    }

    Ok(())
}

async fn run_query(
    _settings: Settings,
    question: String,
    top_k: usize,
    collection: String,
) -> Result<()> {
    tracing::info!("Querying '{}' (top {})", question, top_k);

    let client = reqwest::Client::new();
    let query_url = format!("http://{}:{}/query", "127.0.0.1", 8001);

    let payload = serde_json::json!({
        "question": question,
        "top_k": top_k,
        "collection": collection,
    });

    match client.post(&query_url).json(&payload).send().await {
        Ok(response) => {
            if response.status().is_success() {
                let result: serde_json::Value = response
                    .json()
                    .await
                    .map_err(|e| Error::Internal(e.to_string()))?;
                println!("\n{}", serde_json::to_string_pretty(&result)?);
            } else {
                tracing::error!(
                    "Query failed: {}",
                    response
                        .text()
                        .await
                        .map_err(|e| Error::Internal(e.to_string()))?
                );
            }
        }
        Err(e) => {
            tracing::error!("Failed to connect to query service: {}", e);
        }
    }

    Ok(())
}

async fn run_graph(settings: Settings, method: String, depth: usize) -> Result<()> {
    tracing::info!(
        "Showing citation graph for method '{}' (depth {})",
        method,
        depth
    );

    // Open the graph database
    let graph_path = settings.app.data_dir.join("citation_graph.sqlite");
    let store = epa_kg_graph::store::GraphStore::new(&graph_path)?;

    // Print the graph tree
    store.print_graph_tree(&method, depth);

    Ok(())
}

async fn run_server(_settings: Settings, port: u16) -> Result<()> {
    tracing::info!("Starting API server on port {}", port);

    use epa_kg_api::{routes::router, state::AppState};
    use std::net::SocketAddr;

    let state = AppState::new();
    let app = router(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("EPA Knowledge Graph API listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cli_parse_ingest_command() {
        let result = Cli::try_parse_from([
            "epa-kg",
            "ingest",
            "--pdf-dir",
            "/tmp",
            "--collection",
            "test",
        ]);
        assert!(result.is_ok());
        let cli = result.unwrap();
        match cli.command {
            Commands::Ingest {
                pdf_dir,
                collection,
                ..
            } => {
                assert_eq!(pdf_dir, PathBuf::from("/tmp"));
                assert_eq!(collection, "test");
            }
            _ => panic!("Expected Ingest command"),
        }
    }

    #[test]
    fn cli_parse_query_command() {
        let result = Cli::try_parse_from([
            "epa-kg",
            "query",
            "--question",
            "What is EPA 8270?",
            "--top-k",
            "3",
        ]);
        assert!(result.is_ok());
        let cli = result.unwrap();
        match cli.command {
            Commands::Query {
                question, top_k, ..
            } => {
                assert_eq!(question, "What is EPA 8270?");
                assert_eq!(top_k, 3);
            }
            _ => panic!("Expected Query command"),
        }
    }

    #[test]
    fn cli_parse_graph_command() {
        let result = Cli::try_parse_from(["epa-kg", "graph", "--method", "8270E", "--depth", "3"]);
        assert!(result.is_ok());
        let cli = result.unwrap();
        match cli.command {
            Commands::Graph { method, depth, .. } => {
                assert_eq!(method, "8270E");
                assert_eq!(depth, 3);
            }
            _ => panic!("Expected Graph command"),
        }
    }

    #[test]
    fn cli_parse_serve_command() {
        let result = Cli::try_parse_from(["epa-kg", "serve", "--port", "9090"]);
        assert!(result.is_ok());
        let cli = result.unwrap();
        match cli.command {
            Commands::Serve { port, .. } => {
                assert_eq!(port, 9090);
            }
            _ => panic!("Expected Serve command"),
        }
    }

    #[test]
    fn run_graph_returns_ok() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut settings = Settings::default();
        settings.app.data_dir = temp_dir.path().to_path_buf();

        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let result = run_graph(settings, "8270E".into(), 2).await;
            assert!(result.is_ok());
        });
    }

    #[test]
    fn run_server_returns_ok() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let result = run_server(Settings::default(), 8080).await;
            assert!(result.is_ok());
        });
    }

    #[test]
    fn extract_and_persist_graph_returns_err_when_service_down() {
        let temp_dir = tempfile::tempdir().unwrap();
        let mut settings = Settings::default();
        settings.app.data_dir = temp_dir.path().to_path_buf();

        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let result = extract_and_persist_graph(&settings, "epa_methods").await;
            assert!(result.is_err());
        });
    }
}
