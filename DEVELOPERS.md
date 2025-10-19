# Development Guide

This template comes with opinionated tooling for Temporal development using its Python SDK.

## Table of Contents

- [Package Management](#package-management)
  - [Common `uv` Commands](#common-uv-commands)
- [Testing](#testing)
  - [Key Features](#key-features)
  - [Common `pytest` Commands](#common-pytest-commands)
- [Data Serialization](#data-serialization)
  - [Temporal Integration](#temporal-integration)
- [Code Quality](#code-quality)
  - [Common `ruff` Commands](#common-ruff-commands)
  - [Common `pre-commit` Commands](#common-pre-commit-commands)
- [Task Management](#task-management)
  - [Common `poe` Commands](#common-poe-commands)
- [Continuous Integration](#continuous-integration)
- [Dependency Automation](#dependency-automation)

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

## Task Management

We use **[poethepoet](https://poethepoet.natn.io/)** (poe) as a task runner because it provides a simple, declarative way to define and execute project tasks directly in `pyproject.toml`. Unlike Makefiles or shell scripts, poe tasks are cross-platform, integrate seamlessly with Python tooling, and automatically handle virtual environment activation.

### Common `poe` Commands

```bash
# Run tests with proper PYTHONPATH configuration
uv run poe test

# Lint code and automatically fix issues
uv run poe lint

# Format code with ruff
uv run poe format

# Install pre-commit hooks
uv run poe pre-commit-install

# Run pre-commit on all files
uv run poe pre-commit-run

# Update pre-commit hook versions
uv run poe pre-commit-update

# List all available tasks
uv run poe --help
```

**Important**: Always use `uv run poe test` instead of `uv run pytest` directly, as the poe task properly configures `PYTHONPATH=.` to ensure imports work correctly.

## Continuous Integration

We use **[GitHub Actions](https://docs.github.com/en/actions)** for continuous integration because it provides native integration with GitHub repositories, supports matrix builds across multiple Python versions and operating systems, and offers excellent caching capabilities for faster builds. GitHub Actions is free for public repositories and provides generous limits for private repositories.

In this project, GitHub Action is used for continuous integration (i.e. ensure code quality and test coverage).
To disable the CI pipeline, you can delete the [GitHub Action definition file](.github/workflows/ci.yml)
or append `.disabled` to the filename.

## Dependency Automation

We use **[Dependabot](https://docs.github.com/en/code-security/dependabot)** for automated dependency management because it provides proactive security updates, keeps dependencies current with minimal manual effort, and integrates seamlessly with GitHub's security advisory database.

Dependabot automatically creates pull requests for dependency updates, making it easy to review and merge changes while maintaining project security.

The Dependabot configuration for this project is stored at [`.github/dependabot.yml`](.github/dependabot.yml).
For full documentation on Dependabot configuration, see [Dependabot options reference](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference).
