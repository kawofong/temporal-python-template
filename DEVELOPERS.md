# Development Guide

This template comes with opinionated tooling for Temporal development using its Python SDK.

## Package Management

We use **[uv](https://docs.astral.sh/uv/)** for package management instead of `pip` or `poetry` because it's significantly faster (10-100x speedup), written in Rust, downloads packages in parallel, and provides a drop-in replacement for common `pip` workflows.

Reference: [Faster pip installs: caching, bytecode compilation, and uv](https://pythonspeed.com/articles/faster-pip-installs/)

### Common `uv` Commands

```bash
# Install dependencies and sync environment
uv sync --dev

# Add a new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Create virtual environment
uv venv

# Run commands in the environment
uv run python script.py
```

## Testing

We use **[pytest](https://docs.pytest.org/)** for testing because it provides excellent `asyncio` support (essential for Temporal Workflows), powerful fixtures for test setup, and comprehensive coverage reporting.

### Key Features

- **Async Support**: `pytest-asyncio` enables testing of async workflows and activities
- **Coverage Reporting**: `pytest-cov` ensures 80% minimum test coverage
- **Timeout Protection**: `pytest-timeout` prevents hanging tests
- **Flexible Discovery**: Automatically finds `*_tests.py` files

### Common `pytest` Commands

```bash
# Run specific test file
PYTHONPATH=. uv run pytest src/workflows/http/http_workflow_tests.py

# Run tests with verbose output
PYTHONPATH=. uv run pytest -v

# Run tests and stop on first failure
PYTHONPATH=. uv run pytest -x

# Run tests matching a pattern
PYTHONPATH=. uv run pytest -k "test_http"

# Generate HTML coverage report
PYTHONPATH=. uv run pytest --cov-report=html
```
