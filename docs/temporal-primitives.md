# Temporal Primitives

## Table of Contents

- [Workflow](#workflow)
- [Activity](#activity)
- [Timer (fixed time)](#timer-fixed-time)
- [Timer (event-driven)](#timer-event-driven)
- [Query](#query)
- [Signal](#signal)
- [Update](#update)
- [Retry Policy](#retry-policy)
- [Search Attributes](#search-attributes)

## Workflow

Workflows orchestrate business logic and coordinate activities. They must be deterministic and replay-safe.

```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> None:
        await workflow.execute_activity_method(
            MyActivities.do_database_thing,
            start_to_close_timeout=timedelta(seconds=10),
        )
```

**Key characteristics:**

- Use `@workflow.defn` decorator
- Entry point marked with `@workflow.run`
- Execute activities via `workflow.execute_activity_method()`
- Must be deterministic (no direct I/O, random numbers, system calls)

## Activity

Activities handle non-deterministic operations like database operations, HTTP calls, and file I/O. They can be retried independently and must be idempotent.

```python
class MyActivities:
    def __init__(self, db_client: MyDatabaseClient) -> None:
        self.db_client = db_client

    @activity.defn
    async def do_database_thing(self) -> None:
        await self.db_client.run_database_update()
```

**Key characteristics:**

- Use `@activity.defn` decorator
- Can maintain state through class instances
- Handle all non-deterministic operations
- Automatically retryable on failure

## Timer (fixed time)

Timers provide deterministic delays in Workflows using `asyncio.sleep()`. Timers are replay-safe and respect Temporal's execution guarantees.

```python
import asyncio

@workflow.defn
class TimerWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        greeting = f"Hello, {name}!"
        # Deterministic 2-second delay
        await asyncio.sleep(2)
        return f"Goodbye, {name}!"
```

**Key characteristics:**

- Use `asyncio.sleep(seconds)` for deterministic delays
- Timers are replay-safe and persistent across workflow restarts
- Never use `time.sleep()` in workflows

## Timer (event-driven)

```python
import asyncio
from typing import List

@workflow.defn
class TimerWorkflow:
    def __init__(self) -> None:
        self._exit = False
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    @workflow.run
    async def run(self) -> List[str]:
        results = []
        while True:
            # Wait for condition or timeout
            await workflow.wait_condition(
                lambda: not self._queue.empty() or self._exit
            )
            # Process queue items
            while not self._queue.empty():
                results.append(self._queue.get_nowait())
            if self._exit:
                return results

    @workflow.signal
    async def add_item(self, item: str) -> None:
        await self._queue.put(item)
```

**Key characteristics:**

- Use `workflow.wait_condition(lambda: condition)` for event-based waiting
- Timers are replay-safe and persistent across workflow restarts

## Query

Queries allow external clients to read workflow state without affecting execution. They're synchronous, read-only operations that work even after workflow completion.

```python
@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._greeting = ""

    @workflow.run
    async def run(self, name: str) -> None:
        self._greeting = f"Hello, {name}!"
        await asyncio.sleep(2)
        self._greeting = f"Goodbye, {name}!"

    @workflow.query
    def greeting(self) -> str:
        return self._greeting

# Client usage
handle = await client.start_workflow(GreetingWorkflow.run, "World")
result = await handle.query(GreetingWorkflow.greeting)
```

**Key characteristics:**

- Use `@workflow.query` decorator for query methods
- Read-only operations that don't modify workflow state
- Work during execution and after workflow completion
- Synchronous and deterministic

## Signal

Signals allow external clients to send asynchronous messages to running workflows, enabling dynamic interaction and state changes during execution.

```python
@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._pending_greetings: asyncio.Queue[str] = asyncio.Queue()
        self._exit = False

    @workflow.run
    async def run(self) -> List[str]:
        greetings = []
        while True:
            await workflow.wait_condition(
                lambda: not self._pending_greetings.empty() or self._exit
            )
            while not self._pending_greetings.empty():
                greetings.append(f"Hello, {self._pending_greetings.get_nowait()}")
            if self._exit:
                return greetings

    @workflow.signal
    async def submit_greeting(self, name: str) -> None:
        await self._pending_greetings.put(name)

    @workflow.signal
    def exit(self) -> None:
        self._exit = True

# Client usage
handle = await client.start_workflow(GreetingWorkflow.run)
await handle.signal(GreetingWorkflow.submit_greeting, "user1")
await handle.signal(GreetingWorkflow.exit)
```

**Key characteristics:**

- Use `@workflow.signal` decorator for signal methods
- Asynchronous, fire-and-forget operations
- Can modify workflow state and trigger workflow logic
- Often combined with `workflow.wait_condition()` for event-driven workflows

## Update

Updates allow external clients to send synchronous messages to workflows and receive responses. Unlike signals, updates can return values and provide stronger consistency guarantees.

```python
from dataclasses import dataclass
from temporalio.exceptions import ApplicationError

@dataclass
class ApproveInput:
    name: str

@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.language = Language.ENGLISH
        self.greetings = {Language.ENGLISH: "Hello, world"}
        self.lock = asyncio.Lock()

    @workflow.update
    def set_language(self, language: Language) -> Language:
        # Synchronous update - mutates state and returns value
        previous_language, self.language = self.language, language
        return previous_language

    @set_language.validator
    def validate_language(self, language: Language) -> None:
        if language not in self.greetings:
            raise ValueError(f"{language.name} is not supported")

    @workflow.update
    async def set_language_using_activity(self, language: Language) -> Language:
        # Async update - can execute activities
        async with self.lock:
            greeting = await workflow.execute_activity(
                call_greeting_service,
                language,
                start_to_close_timeout=timedelta(seconds=10),
            )
            if greeting is None:
                raise ApplicationError(f"Service doesn't support {language.name}")

            self.greetings[language] = greeting
            previous_language, self.language = self.language, language
            return previous_language

# Client usage
handle = await client.start_workflow(GreetingWorkflow.run)
result = await handle.execute_update(
    GreetingWorkflow.set_language,
    Language.CHINESE
)
```

**Key characteristics:**

- Use `@workflow.update` decorator for update methods
- Can return values to clients (unlike signals)
- Support validators with `@update_method.validator`
- Can be synchronous (state-only) or async (with activities)
- Use `ApplicationError` for client-visible failures
- Often use locks for thread-safe async operations

## Retry Policy

Retry policies define how activities and child workflows should be retried when they fail. Temporal provides automatic retry capabilities with configurable backoff strategies, maximum attempts, and timeout settings.

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    print(f"Invoking activity, attempt number {activity.info().attempt}")
    # Fail the first 3 attempts, succeed the 4th
    if activity.info().attempt < 4:
        raise RuntimeError("Intentional failure")
    return f"{input.greeting}, {input.name}!"

@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_interval=timedelta(seconds=2)),
        )
```

**Default retry behavior:**

- Activities retry automatically with exponential backoff
- Initial interval: 1 second
- Backoff coefficient: 2.0 (doubles each retry)
- Maximum interval: 100 × initial interval
- Unlimited attempts and duration by default
- It's very common for Temporal Activity to use the default Retry Policy

**Custom retry policy configuration:**

```python
from temporalio.common import RetryPolicy

# Custom retry policy with specific limits
custom_retry = RetryPolicy(
    initial_interval=timedelta(seconds=1),      # First retry after 1s
    backoff_coefficient=2.0,                    # Double interval each retry
    maximum_interval=timedelta(seconds=30),     # Cap at 30s between retries
    maximum_attempts=5,                         # Stop after 5 attempts
    non_retryable_error_types=["ValueError"],   # Don't retry these errors
)

await workflow.execute_activity(
    my_activity,
    input_data,
    start_to_close_timeout=timedelta(minutes=5),
    retry_policy=custom_retry,
)
```

**Activity retry information:**

```python
@activity.defn
def my_activity() -> str:
    # Access retry attempt information
    attempt = activity.info().attempt
    activity.logger.info(f"Attempt #{attempt}")

    # Conditional logic based on attempt
    if attempt < 3:
        raise RuntimeError(f"Failing attempt {attempt}")

    return "Success!"
```

**Key characteristics:**

- Use `RetryPolicy` class to configure retry behavior
- Access current attempt via `activity.info().attempt`
- Exponential backoff prevents overwhelming downstream services
- `non_retryable_error_types` for permanent failures
- Applies to both activities and child workflows
- Retry state persists across worker restarts

## Search Attributes

Search Attributes are key-value pairs that enable filtering and searching workflows in Temporal. They're indexed metadata that can be set at workflow start and updated during execution, making workflows discoverable through the Temporal Web UI and programmatic queries.

```python
from temporalio.common import SearchAttributeKey, SearchAttributePair, TypedSearchAttributes

# Define typed search attribute keys
customer_id_key = SearchAttributeKey.for_keyword("CustomerId")
misc_data_key = SearchAttributeKey.for_text("MiscData")

@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self) -> None:
        # Wait a couple seconds, then alter the search attributes
        await asyncio.sleep(2)
        workflow.upsert_search_attributes(TypedSearchAttributes([
            SearchAttributePair(customer_id_key, "customer_2")
        ]))

# Client usage - starting workflow with typed search attributes
handle = await client.start_workflow(
    GreetingWorkflow.run,
    id="search-attributes-workflow-id",
    task_queue="search-attributes-task-queue",
    search_attributes=TypedSearchAttributes([
        SearchAttributePair(customer_id_key, "customer_1"),
        SearchAttributePair(misc_data_key, "customer_1_data")
    ]),
)

# Reading search attributes from workflow handle
search_attrs = (await handle.describe()).search_attributes
print("Search attribute values:", search_attrs.get("CustomerId"))
```

**Creating typed search attribute keys:**

```python
from temporalio.common import SearchAttributeKey

# Different types of search attribute keys
customer_id_key = SearchAttributeKey.for_keyword("CustomerId")
order_value_key = SearchAttributeKey.for_float("OrderValue")
item_count_key = SearchAttributeKey.for_int("ItemCount")
is_priority_key = SearchAttributeKey.for_bool("IsPriority")
created_date_key = SearchAttributeKey.for_datetime("CreatedDate")
tags_key = SearchAttributeKey.for_keyword_list("Tags")
description_key = SearchAttributeKey.for_text("Description")
```

**Updating search attributes during workflow execution:**

```python
from datetime import datetime

@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order_id: str) -> str:
        # Set initial search attributes using typed API
        workflow.upsert_search_attributes(TypedSearchAttributes([
            SearchAttributePair(customer_id_key, "customer_1"),
            SearchAttributePair(order_value_key, 100.50),
            SearchAttributePair(item_count_key, 3),
            SearchAttributePair(is_priority_key, True),
            SearchAttributePair(created_date_key, datetime.now()),
            SearchAttributePair(tags_key, ["electronics", "urgent"])
        ]))

        # Process order...
        await workflow.execute_activity(
            process_payment,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Update search attributes after processing
        workflow.upsert_search_attributes(TypedSearchAttributes([
            SearchAttributePair(customer_id_key, "customer_1_processed")
        ]))

        return "Order completed"

```

**Removing search attributes:**

```python
@workflow.defn
class CleanupWorkflow:
    @workflow.run
    async def run(self) -> str:
        # Set some initial search attributes
        workflow.upsert_search_attributes(TypedSearchAttributes([
            SearchAttributePair(customer_id_key, "customer_1"),
            SearchAttributePair(tags_key, ["electronics", "urgent"]),
            SearchAttributePair(is_priority_key, True)
        ]))

        # Do some work...
        await asyncio.sleep(1)

        # Remove specific search attributes by setting them to empty list
        workflow.upsert_search_attributes(TypedSearchAttributes([
            SearchAttributePair(tags_key, []),           # Remove tags
            SearchAttributePair(is_priority_key, [])     # Remove priority flag
        ]))

        # customer_id_key remains set, only tags and is_priority are removed
        return "Cleanup completed"
```

**Querying workflows by search attributes:**

```python
# List workflows with specific search attributes using string queries
async for workflow in client.list_workflows(
    query='WorkflowType="GreetingWorkflow"'
):
    print(f"Workflow: {workflow.id}")

# Advanced queries with multiple conditions
query = """
    CustomerId="customer_1" AND
    OrderValue > 50.0 AND
    ItemCount >= 1 AND
    StartTime > "2024-01-01T00:00:00Z"
"""
async for workflow in client.list_workflows(query=query):
    print(f"Found workflow: {workflow.id}")

# Query with keyword lists
query = 'Tags IN ("electronics", "urgent")'
workflows = client.list_workflows(query=query)
```

**Key characteristics:**

- Use typed search attributes with `SearchAttributeKey` for type safety
- Create search attributes with `TypedSearchAttributes` and `SearchAttributePair`
- Use `workflow.upsert_search_attributes()` to set/update attributes during execution
- Set initial attributes via `search_attributes` parameter when starting workflows
- Search attributes are indexed and queryable through Temporal Web UI and CLI
- Support multiple data types: Bool, Datetime, Double, Int, Keyword, KeywordList, Text
- Remove attributes by setting them to empty list: `[]`
- Enable powerful workflow discovery and monitoring capabilities
- Persist across workflow restarts and are available after completion
