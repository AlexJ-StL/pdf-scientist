# Stage 1: Build Rust binary
FROM rust:1.80-bookworm AS rust-builder
WORKDIR /app

# Cache dependencies
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
RUN cargo build --release --workspace

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS python-deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen

# Stage 3: Runtime
FROM debian:bookworm-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust binaries
COPY --from=rust-builder /app/target/release/epa-kg /usr/local/bin/

# Copy Python environment
COPY --from=python-deps /root/.local /root/.local
ENV PATH="/root/.local/bin:${PATH}"

# Copy Python source
COPY python/ingestion ./python/ingestion

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directory
RUN mkdir -p /app/data/chroma

EXPOSE 8001 8080
ENTRYPOINT ["/entrypoint.sh"]
