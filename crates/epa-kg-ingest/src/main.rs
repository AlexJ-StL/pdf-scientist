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

    #[arg(short, long, global = true)]
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
        Commands::Ingest { pdf_dir, collection, force_reindex } => {
            run_ingest(settings, pdf_dir, collection, force_reindex).await
        }
        Commands::Query { question, top_k, collection } => {
            run_query(settings, question, top_k, collection).await
        }
        Commands::Graph { method, depth } => {
            run_graph(settings, method, depth).await
        }
        Commands::Serve { port } => {
            run_server(settings, port).await
        }
    }
}

async fn run_ingest(
    settings: Settings,
    pdf_dir: PathBuf,
    collection: String,
    force_reindex: bool,
) -> Result<()> {
    tracing::info!("Starting ingestion from {:?} into collection '{}'", pdf_dir, collection);

    if !pdf_dir.exists() {
        return Err(Error::Ingestion(format!("PDF directory does not exist: {:?}", pdf_dir)));
    }

    // TODO: Call Python ingestion service via HTTP
    // For now, just log what would happen
    let pdf_files: Vec<_> = std::fs::read_dir(&pdf_dir)?
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "pdf"))
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
                let result: serde_json::Value = response.json().await.map_err(|e| Error::Internal(e.to_string()))?;
                tracing::info!("Result: {}", serde_json::to_string_pretty(&result)?);
            } else {
                tracing::error!("Ingestion failed: {}", response.text().await.map_err(|e| Error::Internal(e.to_string()))?);
            }
        }
        Err(e) => {
            tracing::error!("Failed to connect to ingestion service: {}", e);
            tracing::info!("Make sure the Python ingestion service is running on port 8001");
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
                let result: serde_json::Value = response.json().await.map_err(|e| Error::Internal(e.to_string()))?;
                println!("\n{}", serde_json::to_string_pretty(&result)?);
            } else {
                tracing::error!("Query failed: {}", response.text().await.map_err(|e| Error::Internal(e.to_string()))?);
            }
        }
        Err(e) => {
            tracing::error!("Failed to connect to query service: {}", e);
        }
    }

    Ok(())
}

async fn run_graph(
    _settings: Settings,
    method: String,
    depth: usize,
) -> Result<()> {
    tracing::info!("Showing citation graph for method '{}' (depth {})", method, depth);
    // TODO: Implement graph traversal
    println!("Graph for {} (depth {}):", method, depth);
    println!("  (not yet implemented)");
    Ok(())
}

async fn run_server(_settings: Settings, port: u16) -> Result<()> {
    tracing::info!("Starting API server on port {}", port);
    // TODO: Start Axum server
    println!("Server not yet implemented");
    Ok(())
}