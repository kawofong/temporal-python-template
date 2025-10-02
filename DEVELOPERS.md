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

See [this](https://docs.astral.sh/uv/getting-started/features/) for the full list of `uv` commands.

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

See [this](https://docs.pytest.org/en/stable/how-to/usage.html) for the full list of `pytest` commands.

## Data Serialization

We use **[Pydantic](https://docs.pydantic.dev/)** for data validation and serialization because it provides runtime type checking, automatic data validation, and seamless JSON serialization/deserialization. This is important for Temporal Workflows because it is strongly recommended to pass object as input and output to Workflows and Activities.

To learn more about Pydantic, see their [documentation](https://docs.pydantic.dev/latest/why/).

### Temporal Integration

Temporal's Python SDK includes built-in Pydantic support via `temporalio.contrib.pydantic.pydantic_data_converter`:

```python
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

# Use Pydantic data converter for automatic serialization
client = await Client.connect(
    "localhost:7233",
    data_converter=pydantic_data_converter
)
```

This enables automatic serialization / deserialization of Pydantic models in Workflow inputs, outputs, and Activity parameters.

## Code Quality

We use **[Ruff](https://docs.astral.sh/ruff/)** for linting and auto-formatting because it's extremely fast (10-100x faster than alternatives), written in Rust, and combines multiple tools (flake8, isort, black) into one. It enforces comprehensive code quality rules while automatically fixing many issues.

### Common `ruff` Commands

```bash
# Check without fixing
uv run ruff check .

# Format specific file
uv run ruff format src/workflows/http/http_workflow.py
```

Full lists of `ruff` commands: [Ruff Linter](https://docs.astral.sh/ruff/linter/) and [Ruff Formatter](https://docs.astral.sh/ruff/formatter/).

We use **[pre-commit](https://pre-commit.com/)** to automatically run code quality checks before commits, ensuring consistent code standards and catching issues early in development.

### Common `pre-commit` Commands

```bash
# Install hooks
uv run pre-commit install --hook-type pre-commit --hook-type pre-push

# Run on all files
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate

# Run pre-commit against a single file
uv run pre-commit run --files src/workflows/http/http_workflow.py

# Run a specific hook against a single file
uv run pre-commit run check-toml --files pyproject.toml

# Skip hooks for emergency commits
git commit --no-verify -m "emergency fix"

# Disable pre-commit for this project
uv run pre-commit uninstall
```
