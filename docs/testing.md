# Testing Standards

This document outlines comprehensive testing standards for this project, emphasizing behavioral driven testing (BDD) best practices.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
  - [Core Principles](#core-principles)
- [Test Types and Structure](#test-types-and-structure)
  - [Unit Tests (Activities)](#1-unit-tests-activities)
  - [Unit Tests (Workflows)](#2-unit-tests-workflows)
- [Testing Framework Configuration](#testing-framework-configuration)
  - [Pytest Configuration](#pytest-configuration)
  - [Test File Structure](#test-file-structure)
- [Activity Testing Standards](#activity-testing-standards)
  - [Basic Activity Test Structure](#basic-activity-test-structure)
  - [Activity Testing Requirements](#activity-testing-requirements)
  - [Activity Mocking Patterns](#activity-mocking-patterns)
- [Workflow Testing Standards](#workflow-testing-standards)
  - [Basic Workflow Test Structure](#basic-workflow-test-structure)
  - [Workflow Testing Requirements](#workflow-testing-requirements)
  - [Advanced Workflow Testing Patterns](#advanced-workflow-testing-patterns)
- [Test Organization and Naming](#test-organization-and-naming)
  - [File Naming Convention](#file-naming-convention)
  - [Test Method Naming Patterns](#test-method-naming-patterns)
  - [Test Class Organization](#test-class-organization)
- [Mocking and Test Isolation](#mocking-and-test-isolation)
  - [External Service Mocking](#external-service-mocking)
  - [Activity Mocking in Workflows](#activity-mocking-in-workflows)
  - [Test Data Management](#test-data-management)
- [Coverage Requirements](#coverage-requirements)
  - [Minimum Coverage Standards](#minimum-coverage-standards)
  - [Running Coverage Reports](#running-coverage-reports)
  - [Coverage Exclusions](#coverage-exclusions)
- [Error Handling and Edge Cases](#error-handling-and-edge-cases)
  - [Input Validation Testing](#input-validation-testing)
  - [Network Error Simulation](#network-error-simulation)
  - [Resource Exhaustion Testing](#resource-exhaustion-testing)
- [Best Practices](#best-practices)
  - [Test Documentation](#test-documentation)
  - [Test Structure](#test-structure)
  - [Mock Management](#mock-management)
  - [Test Data](#test-data)
  - [Performance Considerations](#performance-considerations)
  - [Debugging Support](#debugging-support)
- [Running Tests](#running-tests)
  - [Basic Test Execution](#basic-test-execution)
  - [Test Options](#test-options)
  - [Debugging Tests](#debugging-tests)
- [Continuous Integration](#continuous-integration)
  - [Pre-commit Hooks](#pre-commit-hooks)
  - [CI Pipeline Requirements](#ci-pipeline-requirements)

## Testing Philosophy

### Core Principles

1. **Behavior-Driven**: Tests describe business behavior and user scenarios, not just implementation details
2. **Comprehensive Coverage**: Test both happy paths and error scenarios using realistic business scenarios
3. **Isolation**: Each test should be independent and not rely on external services
4. **Determinism**: Tests must be predictable and repeatable
5. **Speed**: Tests should run quickly to enable rapid feedback
6. **Clarity**: Tests should serve as living documentation of expected behavior using natural language
7. **User-Centric**: Focus on what the system should do from a user's perspective
8. **Scenario-Based**: Structure tests around business scenarios using Given-When-Then patterns

## Test Types and Structure

### 1. Behavior Tests (Activities)

- Test individual activities as business behaviors
- Mock external dependencies to focus on business logic
- Structure tests using Given-When-Then scenarios
- Use `ActivityEnvironment` for execution
- Name tests to describe business outcomes

### 2. Behavior Tests (Workflows)

- Test workflow orchestration as business processes
- Mock activities if activities have external dependencies
- Use `WorkflowEnvironment` with time skipping
- Focus on business scenarios and user journeys
- Test complete business workflows end-to-end

## BDD Testing Structure

### Given-When-Then Pattern

All tests should follow the Given-When-Then (GWT) pattern to clearly describe business scenarios:

- **Given**: The initial context or preconditions
- **When**: The action or event that triggers the behavior
- **Then**: The expected outcome or result

### Test Scenario Structure

```python
@pytest.mark.asyncio
async def test_should_process_payment_when_valid_card_provided(self) -> None:
    """
    Scenario: Processing payment with valid card
    Given a customer has a valid credit card
    When they submit a payment request
    Then the payment should be processed successfully
    """
    # Given - Setup initial conditions
    valid_card = PaymentCard(number="4111111111111111", cvv="123")
    payment_request = PaymentRequest(amount=100.00, card=valid_card)

    # When - Execute the behavior
    result = await activity_environment.run(process_payment, payment_request)

    # Then - Verify the outcome
    assert result.status == PaymentStatus.SUCCESS
    assert result.transaction_id is not None
```

## Testing Framework Configuration

This project uses `pytest` to write all tests with BDD-style naming and structure.
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

```text
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

## Activity Behavior Testing Standards

### BDD Activity Test Structure

```python
"""Behavior tests for [activity_name] activities."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from temporalio.testing import ActivityEnvironment

from src.workflows.example.example_activities import MyActivity, MyActivityInput


class TestMyActivity:
    """Behavior tests for MyActivity.

    Tests describe business scenarios and expected outcomes
    using Given-When-Then structure for clarity.
    """

    @pytest.mark.asyncio
    async def test_my_activity_should_return_processed_data_when_valid_input_provided(self) -> None:
        """
        Scenario: Processing valid business data
        Given a valid business input is provided
        When the activity processes the data
        Then it should return the expected processed result
        """
        # Given - Valid business input
        activity_environment = ActivityEnvironment()
        business_input = MyActivityInput(param="valid_business_data")

        # Mock external service to return expected business result
        with patch("external_service.call") as mock_service:
            mock_service.return_value = "processed_business_result"

            # When - Activity processes the input
            result = await activity_environment.run(my_activity, business_input)

            # Then - Should return processed business data
            assert result.output == "processed_business_result"
            mock_service.assert_called_once_with("valid_business_data")

    @pytest.mark.parametrize(
        "scenario,invalid_input,expected_exception,business_context",
        [
            ("empty_input", "", ValueError, "User provides empty input field"),
            ("null_input", None, TypeError, "System receives null data"),
            ("malformed_input", "invalid", CustomException, "User provides malformed data"),
        ],
    )
    @pytest.mark.asyncio
    async def test_my_activity_should_reject_invalid_input_when_business_rules_violated(
        self, scenario: str, invalid_input, expected_exception, business_context: str
    ) -> None:
        """
        Scenario: Handling invalid business input
        Given invalid business data is provided
        When the activity attempts to process it
        Then it should reject the input with appropriate error
        """
        # Given - Invalid business input based on scenario
        activity_environment = ActivityEnvironment()

        # When/Then - Should reject invalid input
        with pytest.raises(expected_exception):
            invalid_business_input = MyActivityInput(param=invalid_input)
            await activity_environment.run(my_activity, invalid_business_input)
```

### Activity Behavior Testing Requirements

1. **Use ActivityEnvironment**: Always test activities using `ActivityEnvironment` for proper isolation
1. **Mock External Dependencies**: Mock all HTTP calls, database connections, file operations, etc.
1. **Business-Focused Naming**: Name tests to describe business outcomes, not implementation details
1. **Given-When-Then Structure**: Structure all tests with clear Given-When-Then comments
1. **Scenario Documentation**: Include business scenario descriptions in test docstrings
1. **Test Business Rules**: Verify business logic and validation rules work correctly
1. **Test Error Scenarios**: Always test business rule violations and edge cases
1. **Parameterized Scenarios**: Use `@pytest.mark.parametrize` with scenario names and business context
1. **Async Support**: Mark async tests with `@pytest.mark.asyncio`

### Activity Mocking Patterns

#### HTTP Client Mocking with BDD Structure

```python
@pytest.mark.asyncio
async def test_user_data_fetcher_should_fetch_user_data_when_api_responds_successfully(self) -> None:
    """
    Scenario: Fetching user data from external API
    Given the external API is available and responds with user data
    When the activity makes a request for user information
    Then it should return the user data successfully
    """
    # Given - External API responds with user data
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value='{"user_id": 123, "name": "John Doe"}')
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    user_request = UserDataRequest(user_id=123)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        activity_environment = ActivityEnvironment()

        # When - Activity fetches user data
        result = await activity_environment.run(fetch_user_data, user_request)

        # Then - Should return user data successfully
        assert result.status_code == 200
        assert result.user_name == "John Doe"
```

## Workflow Behavior Testing Standards

### BDD Workflow Test Structure

```python
"""Behavior tests for [workflow_name] workflow."""

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
    """Behavior tests for MyWorkflow.

    Tests describe complete business processes and user journeys
    using Given-When-Then structure for end-to-end scenarios.
    """

    @pytest.fixture
    def task_queue(self) -> str:
        """Generate unique task queue name for each test."""
        return f"test-my-workflow-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_my_workflow_should_complete_business_process_when_all_steps_succeed(
        self, client: Client, task_queue: str
    ) -> None:
        """
        Scenario: Completing a successful business process
        Given all required business data is available
        When the workflow executes the complete business process
        Then it should complete successfully with expected results
        """

        @activity.defn(name="my_activity")
        async def my_activity_mocked(input_data) -> MyActivityOutput:
            """Mocked activity representing successful business operation."""
            return MyActivityOutput(result="business_process_completed")

        # Given - All business prerequisites are met
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[MyWorkflow],
            activities=[my_activity_mocked],
            activity_executor=ThreadPoolExecutor(5),
        ):
            business_input = MyWorkflowInput(param="valid_business_data")

            # When - Business process is executed
            result = await client.execute_workflow(
                MyWorkflow.run,
                business_input,
                id=f"test-business-process-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Business process should complete successfully
            assert isinstance(result, MyWorkflowOutput)
            assert result.output == "business_process_completed"
```

### Workflow Behavior Testing Requirements

1. **Use WorkflowEnvironment**: Leverage the test environment from `conftest.py`
1. **Mock Activities for Business Logic**: Create test implementations of activities that focus on business outcomes
1. **Business Process Focus**: Test complete business workflows, not just technical orchestration
1. **Unique Task Queues**: Use UUID-based task queue names to avoid conflicts
1. **Time Skipping**: Use time-skipping test environment for faster execution
1. **Business Error Scenarios**: Test how workflows handle business rule violations and process failures
1. **User Journey Testing**: Test workflows from the user's perspective and business value
1. **Scenario-Based Naming**: Name tests to describe business scenarios, not technical implementation
1. **Avoid testing Timeout and Retry**: Temporal handles timeouts and retry. Focus on business logic instead

### Advanced Workflow Testing Patterns

#### Testing Complex Business Workflows with Multiple Steps

```python
@pytest.mark.asyncio
async def test_order_fulfillment_workflow_should_complete_order_fulfillment_when_all_business_steps_succeed(
    self, client: Client, task_queue: str
) -> None:
    """
    Scenario: Complete order fulfillment process
    Given a customer has placed a valid order
    When the fulfillment workflow processes all business steps
    Then the order should be completed successfully
    """
    business_steps_executed = []

    @activity.defn(name="validate_inventory")
    async def validate_inventory_mocked(input_data) -> InventoryValidationOutput:
        """Mock inventory validation step."""
        business_steps_executed.append("inventory_validated")
        return InventoryValidationOutput(available=True, reserved_quantity=5)

    @activity.defn(name="process_payment")
    async def process_payment_mocked(input_data) -> PaymentProcessingOutput:
        """Mock payment processing step."""
        business_steps_executed.append("payment_processed")
        return PaymentProcessingOutput(transaction_id="txn_123", status="completed")

    # Given - Customer has placed a valid order
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[OrderFulfillmentWorkflow],
        activities=[validate_inventory_mocked, process_payment_mocked],
    ):
        order_input = OrderFulfillmentInput(
            order_id="order_123",
            customer_id="customer_456",
            items=[{"product_id": "prod_789", "quantity": 5}]
        )

        # When - Order fulfillment workflow processes all steps
        result = await client.execute_workflow(
            OrderFulfillmentWorkflow.run,
            order_input,
            id=f"test-order-fulfillment-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Then - Order should be completed with all business steps executed
        assert result.order_status == "fulfilled"
        assert "inventory_validated" in business_steps_executed
        assert "payment_processed" in business_steps_executed
        assert result.fulfillment_details.transaction_id == "txn_123"
```

## BDD Test Organization and Naming

### File Naming Convention

- Test files: `*_tests.py`
- Test classes: `Test[ComponentName]`
- Test methods: `test_[component]_should_[expected_outcome]_when_[condition]`

### BDD Test Method Naming Patterns

Use behavior-focused naming that describes business outcomes, starting with the component being tested:

```python
def test_[component]_should_[expected_outcome]_when_[condition](self) -> None:
    """
    Scenario: [Business scenario description]
    Given [preconditions]
    When [action/trigger]
    Then [expected outcome]
    """
```

### BDD Naming Examples

**Good BDD Names (Business-Focused):**

- `test_payment_processor_should_process_payment_when_valid_card_provided()`
- `test_order_validator_should_reject_order_when_insufficient_inventory()`
- `test_notification_service_should_send_notification_when_workflow_completes()`
- `test_retry_handler_should_retry_failed_step_when_temporary_error_occurs()`

**Avoid Technical Names:**

- ❌ `test_http_activity_success()`
- ❌ `test_workflow_timeout_raises_exception()`
- ❌ `test_activity_invalid_url_raises_client_error()`

**Better Business-Focused Alternatives:**

- ✅ `test_user_data_fetcher_should_fetch_user_data_when_api_responds_successfully()`
- ✅ `test_business_process_should_handle_failure_when_external_service_unavailable()`
- ✅ `test_input_validator_should_validate_input_when_user_provides_invalid_data()`

### BDD Test Class Organization

```python
class TestMyComponent:
    """Behavior tests for MyComponent.

    Tests describe business scenarios and expected outcomes
    from the user's perspective. Each test represents a
    specific business use case or user journey.
    """

    # Happy path business scenarios first
    def test_my_component_should_complete_business_operation_when_valid_conditions_met(self) -> None:
        """
        Scenario: Successful business operation
        Given valid business conditions are met
        When the user initiates the operation
        Then the business operation should complete successfully
        """
        pass

    # Business rule violations
    def test_my_component_should_reject_operation_when_business_rules_violated(self) -> None:
        """
        Scenario: Business rule validation
        Given business rules are configured
        When invalid business data is provided
        Then the operation should be rejected with clear feedback
        """
        pass

    # Edge cases and boundary conditions
    def test_my_component_should_handle_boundary_conditions_when_edge_cases_occur(self) -> None:
        """
        Scenario: Handling edge cases
        Given boundary conditions exist
        When edge case scenarios occur
        Then the system should handle them gracefully
        """
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

### Business Rule Validation Testing

```python
@pytest.mark.parametrize(
    "business_scenario,invalid_input,expected_error,business_context",
    [
        ("empty_url_submission", "", "URL cannot be empty", "User submits form without URL"),
        ("malformed_url_entry", "not-a-url", "Invalid URL format", "User enters invalid URL format"),
        ("incomplete_url_input", "https://", "Incomplete URL", "User provides incomplete URL"),
    ],
)
@pytest.mark.asyncio
async def test_input_validator_should_reject_invalid_business_data_when_validation_rules_violated(
    self, business_scenario: str, invalid_input: str, expected_error: str, business_context: str
) -> None:
    """
    Scenario: Business data validation
    Given business validation rules are in place
    When invalid business data is provided
    Then the system should reject it with appropriate business error
    """
    # Given - Business validation rules are configured
    # When - Invalid business data is provided
    # Then - Should reject with business-appropriate error
    with pytest.raises(ValueError, match=expected_error):
        MyActivityInput(url=invalid_input)
```

### Business Process Error Simulation

```python
@pytest.mark.asyncio
async def test_external_service_handler_should_handle_service_unavailable_when_external_dependency_fails(self) -> None:
    """
    Scenario: External service unavailability
    Given the business process depends on an external service
    When the external service becomes unavailable
    Then the system should handle the failure gracefully
    """
    # Given - Business process requires external service
    activity_environment = ActivityEnvironment()
    business_request = BusinessDataRequest(customer_id="cust_123")

    # When - External service is unavailable
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get.side_effect = (
            aiohttp.ClientConnectorError("External service unavailable")
        )

        # Then - Should handle the business process failure appropriately
        with pytest.raises(aiohttp.ClientConnectorError):
            await activity_environment.run(fetch_customer_data, business_request)
```

### Business Load Testing

```python
@pytest.mark.asyncio
async def test_data_processor_should_process_large_business_data_when_high_volume_submitted(self) -> None:
    """
    Scenario: High-volume business data processing
    Given the system needs to handle large business datasets
    When a high-volume business request is submitted
    Then it should process the data efficiently without failure
    """
    # Given - Large business dataset needs processing
    large_business_data = BusinessDataInput(
        customer_records="x" * (10 * 1024 * 1024),  # 10MB of customer data
        processing_type="bulk_analysis"
    )

    activity_environment = ActivityEnvironment()

    # When - High-volume business data is processed
    result = await activity_environment.run(process_business_data, large_business_data)

    # Then - Should handle large business data gracefully
    assert result is not None
    assert result.processing_status == "completed"
    assert result.records_processed > 0
```

## BDD Best Practices

### Business-Focused Test Documentation

1. **Scenario Docstrings**: Every test method should describe the business scenario using Given-When-Then
2. **Business Context**: Explain the business value and user perspective
3. **Descriptive Names**: Use names that business stakeholders can understand
4. **Living Documentation**: Tests should serve as executable business requirements

### BDD Test Structure

1. **Given-When-Then**: Follow the GWT pattern consistently with clear comments
2. **Single Business Scenario**: Each test should verify one specific business behavior
3. **Independent Scenarios**: Tests should represent independent business cases
4. **Business Language**: Use domain terminology that business users understand

### Business-Focused Mock Management

1. **Business-Realistic Mocking**: Mock external services to return realistic business data
2. **Scenario-Based Mocks**: Create mocks that support specific business scenarios
3. **Business Outcome Verification**: Assert that business outcomes are achieved, not just technical calls

### Business Test Data

1. **Realistic Business Data**: Use test data that represents actual business scenarios
2. **Business Edge Cases**: Include business boundary conditions and edge cases
3. **Domain Fixtures**: Create fixtures that represent real business entities and relationships

### Performance Considerations

1. **Fast Tests**: Keep tests fast to encourage frequent running
2. **Parallel Execution**: Structure tests to support parallel execution
3. **Resource Cleanup**: Ensure tests clean up resources properly

### Business-Focused Debugging Support

1. **Business-Meaningful Assertions**: Use assertion messages that describe business expectations
2. **Scenario Isolation**: Make it easy to run individual business scenarios
3. **Business Context in Output**: Include business context and scenario information in test output

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

## Summary

These BDD testing standards ensure that Temporal workflows and activities are tested from a business perspective, creating living documentation that describes system behavior in terms that business stakeholders can understand. By following these behavioral driven testing practices, you will:

1. **Create Executable Business Requirements**: Tests serve as living documentation of business rules and processes
2. **Improve Communication**: Business stakeholders can understand and validate test scenarios
3. **Focus on User Value**: Tests describe what the system should do from a user's perspective
4. **Build Maintainable Tests**: Business-focused tests are more stable and meaningful over time
5. **Enable Confident Refactoring**: Well-described business behaviors provide safety nets for code changes

Follow these BDD guidelines consistently to build robust, business-aligned distributed applications with confidence and clarity.
