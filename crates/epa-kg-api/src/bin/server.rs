//! EPA Knowledge Graph API server binary

use epa_kg_api::{routes::router, state::AppState};
use std::net::SocketAddr;
use tracing_subscriber::{fmt, EnvFilter};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    fmt().with_env_filter(EnvFilter::from_default_env().add_directive("epa_kg_api=debug".parse()?)).init();

    let state = AppState::new();
    let app = router(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("EPA Knowledge Graph API listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
