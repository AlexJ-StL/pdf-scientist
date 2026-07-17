#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-api}"

if [ "$SERVICE" = "api" ]; then
    echo "Starting EPA Knowledge Graph API server on port ${PORT:-8080}..."
    exec epa-kg serve --port "${PORT:-8080}"
elif [ "$SERVICE" = "ingestion" ]; then
    echo "Starting Python ingestion service on port ${INGESTION_PORT:-8001}..."
    export PYTHONPATH=/app/python
    exec uvicorn ingestion.main:app --host 0.0.0.0 --port "${INGESTION_PORT:-8001}" --workers 1
else
    echo "Unknown SERVICE: $SERVICE"
    echo "Valid values: api, ingestion"
    exit 1
fi
