.PHONY: install dev run test clean lint format check venv

# Default target
all: install

# Install dependencies
install:
	uv sync

# Development install with dev dependencies
dev: install
	uv add --dev pytest black ruff mypy

# Start trading engine
run:
	uv run python src/main.py

# Run tests
test:
	uv run pytest

# Format code
format:
	uv run black src/
	uv run ruff check src/ --fix

# Lint code
lint:
	uv run ruff check src/
	uv run mypy src/

# Full code check (format + lint)
check: format lint

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Create virtual environment
venv:
	uv venv --python 3.11

# Show help
help:
	@echo "Available commands:"
	@echo "  install  - Install project dependencies"
	@echo "  dev      - Install development dependencies"
	@echo "  run      - Start trading engine"
	@echo "  test     - Run tests"
	@echo "  format   - Format code"
	@echo "  lint     - Lint code"
	@echo "  check    - Full code check"
	@echo "  clean    - Clean cache files"
	@echo "  venv     - Create virtual environment"
	@echo "  help     - Show this help"