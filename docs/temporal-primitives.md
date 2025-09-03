# Temporal Primitives

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
