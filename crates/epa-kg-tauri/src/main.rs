//! Tauri v2 entry point for EPA Knowledge Graph

use epa_kg_core::Settings;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let settings = Settings::load().expect("Failed to load settings");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(move |_app| {
            let _settings = settings.clone();
            
            // Initialize logging
            tracing_subscriber::fmt()
                .with_env_filter("epa_kg=info,tauri=info")
                .init();

            // TODO: Start API server in background
            // TODO: Initialize ChromaDB connection
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            query_knowledge_graph,
            ingest_documents,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to EPA Knowledge Graph.", name)
}

#[tauri::command]
async fn query_knowledge_graph(question: String, top_k: usize) -> Result<String, String> {
    // TODO: Call API service
    Ok(format!("Query '{}' (top {}) - not yet implemented", question, top_k))
}

#[tauri::command]
async fn ingest_documents(pdf_dir: String, collection: String) -> Result<String, String> {
    // TODO: Call ingestion service
    Ok(format!("Ingesting from '{}' into '{}' - not yet implemented", pdf_dir, collection))
}

fn main() {
    run();
}