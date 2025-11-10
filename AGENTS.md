# Temporal Python SDK Project Template

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Key Concepts for AI Assistants](#key-concepts-for-ai-assistants)
  - [Temporal Architecture Patterns](#temporal-architecture-patterns)
  - [Data Models](#data-models)
  - [Testing](#testing)
  - [Documentation](#documentation)
- [Development Guidelines](#development-guidelines)
  - [Code Quality Standards](#code-quality-standards)
  - [Project Commands](#project-commands)
- [AI Assistant Instructions](#ai-assistant-instructions)
  - [When Working with This Project](#when-working-with-this-project)
  - [Common Tasks](#common-tasks)
  - [Security Considerations](#security-considerations)
- [Example Usage Patterns](#example-usage-patterns)
  - [Creating a New Activity](#creating-a-new-activity)
  - [Creating a New Workflow](#creating-a-new-workflow)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Getting Help](#getting-help)

## Project Overview

This is a **Temporal Python SDK project template** (`temporal-python-template`) designed for building reliable, distributed applications. The project demonstrates an AI-enabled approach to workflow development with comprehensive testing and modern Python tooling.

## Tech Stack

- **Temporal**: Workflow orchestration engine for building resilient distributed systems
- **Python 3.12+**: Modern Python with async/await support
- **uv**: Package management and virtual environment management
- **Pydantic**: Data validation and serialization
- **pytest**: Testing framework with async support

For more information on how to use these tools, see [DEVELOPERS.md](./DEVELOPERS.md).

## Project Structure

```text
temporal-python-template/
├── docs/
│   ├── temporal-patterns.md          # Advanced Temporal patterns and examples
│   ├── temporal-primitives.md        # Core Temporal primitives documentation
│   ├── testing.md                    # Testing standards and guidelines
│   └── write-new-workflow.md         # Guide for adding new workflows
├── src/
│   ├── conftest.py                   # Test configuration and fixtures
│   └── workflows/
│       └── http/                        # HTTP workflow example
│           ├── http_activities.py       # Activity definitions
│           ├── http_activities_tests.py # Activity unit tests
│           ├── http_workflow.py         # Workflow definitions (orchestration)
│           ├── http_workflow_tests.py   # Workflow integration tests
│           └── worker.py                # Worker process for running workflows
├── AGENTS.md                         # AI assistant instructions (this file)
├── LICENSE                           # Project license
├── pyproject.toml                    # Project configuration and dependencies
├── README.md                         # Project documentation
└── uv.lock                           # Dependency lock file
```

## Key Concepts for AI Assistants

### Temporal Architecture Patterns

1. **Workflows** (e.g., `src/workflows/http/http_workflow.py`):
   - Orchestration logic that coordinates activities
   - Must be deterministic and replay-safe
   - Use `@workflow.defn` decorator
   - Handle timeouts, retries, and failure scenarios

2. **Activities** (e.g., `src/workflows/http/http_activities.py`):
   - Side effects like HTTP calls, database operations, file I/O
   - Non-deterministic operations
   - Use `@activity.defn` decorator
   - Can be retried independently

3. **Workers** (e.g., `src/workflows/http/worker.py`):
   - Processes that execute workflows and activities
   - Connect to Temporal server
   - Register workflows and activities
   - Note: Not all workflow packages may have a worker file

See [temporal-primitive.md](./docs/temporal-primitives.md) and [temporal-patterns.md](./docs/temporal-patterns.md) for more details.

### Data Models

The project uses **Pydantic models** for type safety and validation.

### Testing

For comprehensive testing standards and guidelines, see [testing.md](./docs/testing.md).

### Documentation

Additional documentation is available:

- [temporal-patterns.md](./docs/temporal-patterns.md): Advanced Temporal patterns and implementation examples
- [temporal-primitives.md](./docs/temporal-primitives.md): Core Temporal primitives and their usage

## Development Guidelines

### Code Quality Standards

- **Ruff**: Comprehensive linting and formatting (configured in `pyproject.toml`)
- **Type Hints**: Full type annotation coverage
- **Docstrings**: Comprehensive documentation for all public APIs
- **Test Coverage**: Minimum 80% coverage enforced with `pytest-cov`
- **Pre-commit**: Automated code quality checks on commit
- **Pytest Configuration**: 5-second timeout per test, async support enabled

### Project Commands

```bash
# Install dependencies
uv sync --dev

# Run tests with coverage
uv run poe test
# Never use `uv run pytest` directly because `PYTHONPATH` will not be configured properly.

# Lint code
uv run poe lint

# Format code
uv run poe format

# Install pre-commit hooks
uv run poe pre-commit-install

# Run pre-commit on all files
uv run poe pre-commit-run

# Update pre-commit hooks
uv run poe pre-commit-update

# Run worker (for workflows that have a worker module)
uv run -m src.workflows.http.worker

# Execute workflow directly (if workflow has main execution)
uv run -m src.workflows.http.http_workflow
```

## AI Assistant Instructions

### When Working with This Project

1. **Understand Temporal Patterns**:
   - Workflows orchestrate, activities execute side effects
   - Workflows must be deterministic (no random numbers, system calls, etc.)
   - Use `workflow.unsafe.imports_passed_through()` for non-deterministic imports
   - Activities handle all external interactions

2. **Follow Existing Patterns**:
   - Use Pydantic models for all inputs/outputs
   - Implement comprehensive error handling
   - Add proper logging with `workflow.logger` and `activity.logger`
   - Include timeout configurations

3. **Testing Approach**:
   - Create unit tests for activities with mocked dependencies
   - Write integration tests using the test environment
   - Use the existing fixtures in `conftest.py`
   - Test both success and failure scenarios
   - Test files must end with `_tests.py` (configured in `pyproject.toml`)
   - Use `pytest-asyncio` for async test support
   - 5-second timeout per test to catch infinite loops

4. **Code Organization**:
   - Keep workflows and activities in separate files
   - Group related functionality in subdirectories
   - Follow the existing naming conventions
   - Maintain clear separation of concerns

### Common Tasks

#### Adding a New Workflow

For instructions on adding a new Workflow to this project, see [write-new-workflow.md](./docs/write-new-workflow.md).

#### Adding External Dependencies

1. Update `dependencies` in `pyproject.toml`
2. Run `uv sync --dev` to update lock file
3. Import within `workflow.unsafe.imports_passed_through()` if used in workflows
4. Add to activities if side effects are needed

### Security Considerations

- Validate all external inputs with Pydantic
- Use environment variables for sensitive configuration
- Implement proper authentication for external services
- Follow principle of least privilege for worker permissions

## Example Usage Patterns

### Creating a New Activity

```python
from pydantic import BaseModel
from temporalio import activity

class MyActivityInput(BaseModel):
    """Input model for the activity."""
    data: str

class MyActivityOutput(BaseModel):
    """Output model for the activity."""
    result: str

@activity.defn
async def my_activity(input: MyActivityInput) -> MyActivityOutput:
    """Activity description."""
    activity.logger.info("Processing %s", input.data)
    # Perform side effect
    processed_data = f"Processed: {input.data}"
    return MyActivityOutput(result=processed_data)
```

### Creating a New Workflow

```python
@workflow.defn
class MyWorkflow:
    """Workflow description."""

    @workflow.run
    async def run(self, input: MyWorkflowInput) -> MyWorkflowOutput:
        """Run the workflow."""
        result = await workflow.execute_activity(
            my_activity,
            input,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return MyWorkflowOutput(data=result.data)
```

## Troubleshooting

### Common Issues

- **Import Errors**: Ensure proper use of `workflow.unsafe.imports_passed_through()`
- **Determinism Violations**: Move non-deterministic code to activities
- **Timeout Errors**: Adjust timeout values or implement proper retry logic
- **Test Failures**: Check for async/await patterns and proper fixture usage

### Getting Help

- [Temporal Documentation](https://docs.temporal.io/)
- [Python SDK Guide](https://docs.temporal.io/dev-guide/python)
- [Community Forum](https://community.temporal.io/)
- Project Documentation: See `docs/` directory for detailed guides

---

This project serves as a template for building production-ready Temporal applications with modern Python practices. Follow the established patterns and testing strategies for consistent, maintainable code.
