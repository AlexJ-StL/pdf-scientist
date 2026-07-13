.PHONY: help test test-python test-rust test-rust-clippy clean

PYTHON := C:/Users/AlexJ/AppData/Local/Programs/Python/Python312/python.exe

help:
	@echo "EPA Knowledge Graph - Available commands:"
	@echo "  make test            - Run all tests (Python + Rust)"
	@echo "  make test-python     - Run Python tests with coverage"
	@echo "  make test-rust       - Run Rust tests"
	@echo "  make test-rust-clippy - Run Rust clippy lints"
	@echo "  make clean           - Remove build artifacts and caches"

test: test-python test-rust

test-python:
	$(PYTHON) -m pytest python/ingestion/tests/ --cov=python/ingestion --cov-report=term-missing -v

test-rust:
	cargo test --workspace --verbose

test-rust-clippy:
	cargo clippy --workspace -- -D warnings

clean:
	cargo clean
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	find python/ingestion/tests -name "*.pyc" -delete
	find python/ingestion -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
