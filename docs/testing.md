# Testing Standards

This document outlines comprehensive testing standards for this project.

## Testing Philosophy

### Core Principles

1. **Comprehensive Coverage**: Test both happy paths and error scenarios
2. **Isolation**: Each test should be independent and not rely on external services
3. **Determinism**: Tests must be predictable and repeatable
4. **Speed**: Tests should run quickly to enable rapid feedback
5. **Clarity**: Tests should serve as living documentation of expected behavior

## Test Types and Structure

### 1. Unit Tests (Activities)

- Test individual activities in isolation
- Mock external dependencies
- Focus on business logic and error handling
- Use `ActivityEnvironment` for execution

### 2. Unit Tests (Workflows)

- Test workflow orchestration logic
- Mock activities if activities have external dependencies
- Use `WorkflowEnvironment` with time skipping

## Testing Framework Configuration

This project uses `pytest` to write all tests.
Other testing dependencies are available in `pyproject.toml`.

### Pytest Configuration

The project uses the following pytest configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --cov-report=term-missing --cov=src"
python_files = ["*_tests.py"]
```

### Test File Structure

```
src/
├── conftest.py                            # Global test configuration
└── workflows/
    └── example/
        ├── example_activities.py          # Activity implementations
        ├── example_activities_tests.py    # Activity unit tests
        ├── example_workflow.py            # Workflow implementations
        ├── example_workflow_tests.py      # Workflow component tests
        └── worker.py                      # Worker configuration
```

## Activity Testing Standards

### Basic Activity Test Structure

```python
"""Tests for [activity_name] activities."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from temporalio.testing import ActivityEnvironment

from src.workflows.example.example_activities import MyActivity, MyActivityInput


class TestMyActivity:
    """Test suite for MyActivity.

    Tests cover successful operations, various error scenarios,
    and edge cases using ActivityEnvironment for isolation.
    """

    @pytest.mark.asyncio
    async def test_activity_success(self) -> None:
        """Test successful activity execution."""
        # Arrange
        activity_environment = ActivityEnvironment()
        input_data = MyActivityInput(param="test_value")

        # Mock external dependencies
        with patch("external_service.call") as mock_service:
            mock_service.return_value = "expected_result"

            # Act
            result = await activity_environment.run(my_activity, input_data)

            # Assert
            assert result.output == "expected_result"
            mock_service.assert_called_once_with("test_value")

    @pytest.mark.parametrize(
        "invalid_input,expected_exception",
        [
            ("", ValueError),
            (None, TypeError),
            ("invalid", CustomException),
        ],
    )
    @pytest.mark.asyncio
    async def test_activity_invalid_input(
        self, invalid_input, expected_exception
    ) -> None:
        """Test activity with various invalid inputs."""
        activity_environment = ActivityEnvironment()
        input_data = MyActivityInput(param=invalid_input)

        with pytest.raises(expected_exception):
            await activity_environment.run(my_activity, input_data)
```

### Activity Testing Requirements

1. **Use ActivityEnvironment**: Always test activities using `ActivityEnvironment` for proper isolation
1. **Mock External Dependencies**: Mock all HTTP calls, database connections, file operations, etc.
1. **Test Input Validation**: Verify Pydantic model validation works correctly
1. **Test Error Scenarios**: Always test code paths leading to Exceptions
1. **Parameterized Tests**: Use `@pytest.mark.parametrize` for testing multiple input scenarios
1. **Async Support**: Mark async tests with `@pytest.mark.asyncio`

### Activity Mocking Patterns

#### HTTP Client Mocking

```python
@pytest.mark.asyncio
async def test_http_activity_success(self) -> None:
    """Test successful HTTP request."""
    # Create mock response
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"result": "success"}')
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # Create mock session
    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        activity_environment = ActivityEnvironment()
        result = await activity_environment.run(http_activity, input_data)

        assert result.status_code == 200
```

## Workflow Testing Standards

### Basic Workflow Test Structure

```python
"""Tests for [workflow_name] workflow."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from src.workflows.example.workflow import (
    MyWorkflow,
    MyWorkflowInput,
    MyWorkflowOutput,
)


class TestMyWorkflow:
    """Test suite for MyWorkflow.

    Tests cover end-to-end workflow execution, mocked activities,
    timeout scenarios, and error handling.
    """

    @pytest.fixture
    def task_queue(self) -> str:
        """Generate unique task queue name for each test."""
        return f"test-my-workflow-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_workflow_success(
        self, client: Client, task_queue: str
    ) -> None:
        """Test successful workflow execution with mocked activities."""

        @activity.defn(name="my_activity")
        async def my_activity_mocked(input_data) -> MyActivityOutput:
            """Mocked activity for testing."""
            return MyActivityOutput(result="mocked_result")

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[MyWorkflow],
            activities=[my_activity_mocked],
            activity_executor=ThreadPoolExecutor(5),
        ):
            input_data = MyWorkflowInput(param="test")

            result = await client.execute_workflow(
                MyWorkflow.run,
                input_data,
                id=f"test-workflow-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert isinstance(result, MyWorkflowOutput)
            assert result.output == "mocked_result"
```

### Workflow Testing Requirements

1. **Use WorkflowEnvironment**: Leverage the test environment from `conftest.py`
1. **Mock Activities if necessary**: Create test implementations of activities for workflow tests if activities have external dependencies (e.g. network calls, database query)
1. **Unique Task Queues**: Use UUID-based task queue names to avoid conflicts
1. **Time Skipping**: Use time-skipping test environment for faster execution
1. **Error Propagation**: Test how workflows handle activity failures
1. **Avoid testing Timeout and Retry**: Temporal handles timeouts and retry. You shall avoid writing tests to test timeout. and retries.

### Advanced Workflow Testing Patterns

#### Testing Workflow with Multiple Activities

```python
@pytest.mark.asyncio
async def test_workflow_multiple_activities(
    self, client: Client, task_queue: str
) -> None:
    """Test workflow that executes multiple activities."""

    @activity.defn(name="database_query")
    async def database_query_mocked(input_data) -> DatabaseQueryOutput:
        activity_calls.append("database_query")
        return DatabaseQueryOutput(result="database_query")

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MyWorkflow],
        activities=[first_activity, database_query_mocked],
    ):
        result = await client.execute_workflow(
            MyWorkflow.run,
            input_data,
            id=f"test-workflow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Verify activity execution order
        assert result.combined_result == "first_result,database_query"
```

## Test Organization and Naming

### File Naming Convention

- Test files: `*_tests.py`
- Test classes: `Test[ComponentName]`
- Test methods: `test_[component]_[scenario]`

### Test Method Naming Patterns

```python
def test_[component]_[scenario]_[expected_outcome](self) -> None:
    """Test [component] [scenario] [expected_outcome]."""
```

Examples:

- `test_http_activity_success()`
- `test_workflow_timeout_raises_exception()`
- `test_activity_invalid_url_raises_client_error()`

### Test Class Organization

```python
class TestMyComponent:
    """Test suite for MyComponent.

    Brief description of what this component does and
    what aspects are covered by these tests.
    """

    # Happy path tests first
    def test_component_success(self) -> None:
        """Test successful operation."""
        pass

    # Error scenarios
    def test_component_invalid_input(self) -> None:
        """Test handling of invalid input."""
        pass

    # Edge cases
    def test_component_edge_case(self) -> None:
        """Test edge case behavior."""
        pass
```

## Mocking and Test Isolation

### External Service Mocking

```python
# HTTP services
with patch("aiohttp.ClientSession") as mock_session:
    mock_session.return_value.__aenter__.return_value.get.return_value.text = AsyncMock(return_value="response")

# Database connections
with patch("asyncpg.connect") as mock_connect:
    mock_connect.return_value.fetch.return_value = [{"id": 1}]

# File operations
with patch("aiofiles.open", mock_open(read_data="file content")):
    # Test file-based activity
```

### Activity Mocking in Workflows

```python
@activity.defn(name="original_activity_name")
async def mocked_activity(input_data: InputType) -> OutputType:
    """Mocked version of activity for workflow testing."""
    # Return controlled test data
    return OutputType(result="test_result")
```

### Test Data Management

```python
# Use fixtures for reusable test data
@pytest.fixture
def sample_input() -> MyActivityInput:
    """Provide sample input for testing."""
    return MyActivityInput(
        url="https://api.example.com/test",
        timeout=30,
    )

@pytest.fixture
def expected_output() -> MyActivityOutput:
    """Provide expected output for testing."""
    return MyActivityOutput(
        response="test response",
        status_code=200,
    )
```

## Coverage Requirements

### Minimum Coverage Standards

- **Overall project coverage**: 80%
- **Individual modules**: 80%
- **Critical workflows**: 80%
- **Activities with external dependencies**: 80%

### Running Coverage Reports

```bash
# Run tests with coverage
uv run poe test

# Generate HTML coverage report
uv run poe test --cov=src --cov-report=html

# Check coverage for specific module
uv run poe test --cov=src.workflows.http --cov-report=term-missing
```

### Coverage Exclusions

```python
# Exclude main execution blocks
if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
```

## Error Handling and Edge Cases

### Input Validation Testing

```python
@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        ("", "URL cannot be empty"),
        ("not-a-url", "Invalid URL format"),
        ("https://", "Incomplete URL"),
    ],
)
@pytest.mark.asyncio
async def test_activity_input_validation(
    self, invalid_input: str, expected_error: str
) -> None:
    """Test activity input validation."""
    with pytest.raises(ValueError, match=expected_error):
        MyActivityInput(url=invalid_input)
```

### Network Error Simulation

```python
@pytest.mark.asyncio
async def test_activity_network_error(self) -> None:
    """Test activity handling of network errors."""
    activity_environment = ActivityEnvironment()

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get.side_effect = (
            aiohttp.ClientConnectorError("Connection failed")
        )

        with pytest.raises(aiohttp.ClientConnectorError):
            await activity_environment.run(http_activity, input_data)
```

### Resource Exhaustion Testing

```python
@pytest.mark.asyncio
async def test_activity_memory_limit(self) -> None:
    """Test activity behavior under memory constraints."""
    # Test with large input data
    large_input = MyActivityInput(
        data="x" * (10 * 1024 * 1024)  # 10MB string
    )

    activity_environment = ActivityEnvironment()

    # Should handle large inputs gracefully
    result = await activity_environment.run(my_activity, large_input)
    assert result is not None
```

## Best Practices

### Test Documentation

1. **Docstrings**: Every test method should have a clear docstring
2. **Comments**: Explain complex test logic and mock setups
3. **Test Names**: Use descriptive names that explain the scenario

### Test Structure

1. **Arrange-Act-Assert**: Follow the AAA pattern consistently
2. **Single Responsibility**: Each test should verify one specific behavior
3. **Independent Tests**: Tests should not depend on each other

### Mock Management

1. **Minimal Mocking**: Mock only what's necessary for isolation
2. **Realistic Mocks**: Mocks should behave like real dependencies
3. **Mock Verification**: Assert that mocks are called as expected

### Test Data

1. **Meaningful Data**: Use realistic test data that represents actual usage
2. **Edge Cases**: Include boundary conditions and edge cases
3. **Data Factories**: Use fixtures or factories for complex test data

### Performance Considerations

1. **Fast Tests**: Keep tests fast to encourage frequent running
2. **Parallel Execution**: Structure tests to support parallel execution
3. **Resource Cleanup**: Ensure tests clean up resources properly

### Debugging Support

1. **Descriptive Assertions**: Use clear assertion messages
2. **Test Isolation**: Make it easy to run individual tests
3. **Debug Information**: Include helpful debug information in test output

## Running Tests

### Basic Test Execution

```bash
# Run all tests
uv run poe test

# Run specific test file
uv run poe test src/workflows/http/http_activities_tests.py

# Run specific test class
uv run poe test src/workflows/http/http_activities_tests.py::TestHttpGetActivity

# Run specific test method
uv run poe test src/workflows/http/http_activities_tests.py::TestHttpGetActivity::test_http_get_success
```

**Important**: never use `uv run pytest` directly because `PYTHONPATH` will not be configured properly.

### Test Options

```bash
# Run with verbose output
uv run poe test -v

# Run with coverage
uv run poe test --cov=src

# Run failed tests only
uv run poe test --lf

# Run tests in parallel (with pytest-xdist)
uv run poe test -n auto
```

### Debugging Tests

```bash
# Run with pdb on failure
uv run poe test --pdb

# Run with detailed output
uv run poe test -vvv --tb=long

# Run specific test with prints
uv run poe test -s src/workflows/http/activities_tests.py::TestHttpGetActivity::test_http_get_success
```

## Continuous Integration

### Pre-commit Hooks

```bash
# Run linting
uv run poe lint

# Run formatting
uv run poe format

# Run tests
uv run poe test
```

### CI Pipeline Requirements

1. **Linting**: Code must pass all linting checks
2. **Formatting**: Code must be properly formatted
3. **Tests**: All tests must pass
4. **Coverage**: Coverage requirements must be met

---

These testing standards ensure that Temporal workflows and activities are thoroughly tested, maintainable, and reliable. Follow these guidelines consistently to build robust distributed applications with confidence.
