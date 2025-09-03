# Temporal Patterns

## Activity Choice

The Activity Choice pattern enables workflows to dynamically select and execute different activities based on input conditions. This pattern is useful for conditional processing where different business logic needs to be applied based on data values.

**Key Implementation:**

- Use conditional logic (`if/elif/else`) to select activity functions
- Enables flexible workflow execution paths while maintaining deterministic replay behavior.
- Each activity handles specific business logic for different cases

```python
from enum import IntEnum
from temporalio import activity, workflow

class Fruit(IntEnum):
    APPLE = 1
    BANANA = 2
    CHERRY = 3

@activity.defn
def order_apples(amount: int) -> str:
    return f"Ordered {amount} Apples..."

@activity.defn
def order_bananas(amount: int) -> str:
    return f"Ordered {amount} Bananas..."

@workflow.defn
class PurchaseFruitsWorkflow:
    @workflow.run
    async def run(self, shopping_list: ShoppingList) -> str:
        ordered = []
        for item in shopping_list.items:
            if item.fruit is Fruit.APPLE:
                order_function = order_apples
            elif item.fruit is Fruit.BANANA:
                order_function = order_bananas
            else:
                raise ValueError(f"Unrecognized fruit: {item.fruit}")

            result = await workflow.execute_activity(
                order_function,
                item.amount,
                start_to_close_timeout=timedelta(seconds=5)
            )
            ordered.append(result)
        return "".join(ordered)
```

## Parallel Activity

The Parallel Activity pattern enables workflows to execute multiple activities concurrently, improving performance when activities are independent and can run simultaneously. This pattern uses `asyncio.gather()` to coordinate parallel execution.

**Key Implementation:**

- Use `asyncio.gather()` to execute multiple activities concurrently
- Activities run independently and can complete in any order
- Results are collected and can be processed after all activities complete
- Significantly reduces total execution time for independent operations

```python
import asyncio
from temporalio import activity, workflow

@activity.defn
def say_hello_activity(name: str) -> str:
    return f"Hello, {name}!"

@workflow.defn
class SayHelloWorkflow:
    @workflow.run
    async def run(self) -> List[str]:
        # Run 5 activities concurrently
        results = await asyncio.gather(
            workflow.execute_activity(
                say_hello_activity,
                "user1",
                start_to_close_timeout=timedelta(seconds=5)
            ),
            workflow.execute_activity(
                say_hello_activity,
                "user2",
                start_to_close_timeout=timedelta(seconds=5)
            ),
            workflow.execute_activity(
                say_hello_activity,
                "user3",
                start_to_close_timeout=timedelta(seconds=5)
            ),
        )
        # Sort results since completion order is non-deterministic
        return list(sorted(results))
```

## Cancellation

The Cancellation pattern enables workflows to gracefully handle cancellation requests while performing cleanup operations. Long-running activities must heartbeat to receive cancellation signals, and workflows can use try/finally blocks to ensure cleanup activities execute.

**Key Implementation:**

- Activities use `activity.heartbeat()` to heartbeat long-running Activities and receive cancellation signals
- Handle `CancelledError` in activities for graceful shutdown
- Use `try/finally` blocks in workflows to guarantee cleanup execution
- Set appropriate heartbeat timeouts for long-running activities

```python
from temporalio import activity, workflow
from temporalio.exceptions import CancelledError

@activity.defn
def never_complete_activity() -> None:
    try:
        while True:
            print("Heartbeating activity")
            activity.heartbeat()  # Required for cancellation delivery
            time.sleep(1)
    except CancelledError:
        print("Activity cancelled")
        raise

@activity.defn
def cleanup_activity() -> None:
    print("Executing cleanup activity")

@workflow.defn
class CancellationWorkflow:
    @workflow.run
    async def run(self) -> None:
        try:
            await workflow.execute_activity(
                never_complete_activity,
                start_to_close_timeout=timedelta(seconds=1000),
                heartbeat_timeout=timedelta(seconds=2),  # Critical for cancellation
            )
        finally:
            # Cleanup always executes, even on cancellation
            await workflow.execute_activity(
                cleanup_activity,
                start_to_close_timeout=timedelta(seconds=5)
            )
```

## Continue-as-New

The Continue-as-New pattern enables workflows to reset their execution history while preserving state, preventing unbounded history growth in long-running or looping workflows. This creates a new workflow execution with the same Workflow ID but fresh Event History.

**Key Implementation:**

- Use `workflow.continue_as_new()` to restart workflow with new parameters
- Design workflow parameters to include current state for continuation
- Check `workflow.info().is_continue_as_new_suggested()` for Continue-as-New timing
- Avoid calling Continue-as-New from Update / Signal handlers. Use Workflow wait conditions to ensure your handler completes before a Workflow finishes.
- Essential for preventing Event History limits and performance degradation

```python
from dataclasses import dataclass
from typing import Optional
from temporalio import workflow

@dataclass
class WorkflowState:
    iteration: int = 0
    processed_items: int = 0

@dataclass
class WorkflowInput:
    state: Optional[WorkflowState] = None
    max_iterations: int = 1000

@workflow.defn
class LongRunningWorkflow:
    @workflow.run
    async def run(self, input: WorkflowInput) -> None:
        # Initialize or restore state
        self.state = input.state or WorkflowState()

        while self.state.iteration < input.max_iterations:
            # Perform work
            await self.process_batch()
            self.state.iteration += 1

            # Check if Continue-as-New is suggested
            if workflow.info().is_continue_as_new_suggested():
                await workflow.wait_condition(workflow.all_handlers_finished)
                workflow.continue_as_new(
                    WorkflowInput(
                        state=self.state,
                        max_iterations=input.max_iterations
                    )
                )
                return

        workflow.logger.info("Completed all %d iterations", input.max_iterations)

    async def process_batch(self):
        # Simulate work
        await asyncio.sleep(0.1)
        self.state.processed_items += 10
```

## Child Workflow

The Child Workflow pattern enables workflows to spawn and manage other workflow executions as children, providing composition and modularity. Child workflows run independently but are tracked in the parent's Event History, enabling complex orchestration patterns.

**Key Implementation:**

- Use `workflow.execute_child_workflow()` to start and wait for completion
- Use `workflow.start_child_workflow()` to start and get handle for advanced control
- Set `parent_close_policy` to control child behavior when parent closes
- Child workflow events are logged in parent's Event History
- In general, Activity or chain of Activity can be used in place of Child Workflows. If possible, it is recommended to use Activity instead of Child Workflows

```python
from dataclasses import dataclass
from temporalio import workflow
from temporalio.workflow import ParentClosePolicy

@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str

@workflow.defn
class ComposeGreetingWorkflow:
    """Child workflow that composes a greeting message."""

    @workflow.run
    async def run(self, input: ComposeGreetingInput) -> str:
        return f"{input.greeting}, {input.name}!"

@workflow.defn
class GreetingWorkflow:
    """Parent workflow that orchestrates child workflows."""

    @workflow.run
    async def run(self, name: str) -> str:
        # Execute child workflow and wait for completion
        return await workflow.execute_child_workflow(
            ComposeGreetingWorkflow.run,
            ComposeGreetingInput("Hello", name),
            id="greeting-child-workflow-id",
            parent_close_policy=ParentClosePolicy.ABANDON,
        )

# Advanced usage with handle
@workflow.defn
class AdvancedParentWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        # Start child workflow and get handle
        handle = await workflow.start_child_workflow(
            ComposeGreetingWorkflow.run,
            ComposeGreetingInput("Hi", name),
            id="advanced-child-workflow-id",
        )

        # Can signal the child or perform other operations
        workflow.logger.info(f"Started child: {handle.id}")

        # Wait for completion
        return await handle
```

## Exceptions

The Exception pattern demonstrates proper error handling in Temporal workflows, including activity failures, retry policies, and exception propagation. Temporal wraps exceptions in specific error types that preserve stack traces and failure details for debugging.

**Key Implementation:**

- Activities can raise exceptions that propagate through workflows
- Use `RetryPolicy` to configure automatic retry behavior for failed activities
- Handle `WorkflowFailureError` when executing workflows from clients
- Exceptions maintain causality chain: WorkflowFailureError → ActivityError → ApplicationError

```python
from dataclasses import dataclass
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import FailureError

@dataclass
class ProcessingInput:
    data: str
    should_fail: bool = False

@activity.defn
def process_data(input: ProcessingInput) -> str:
    if input.should_fail:
        # Activity raises exception
        raise RuntimeError(f"Processing failed for: {input.data}")
    return f"Processed: {input.data}"

@workflow.defn
class DataProcessingWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        return await workflow.execute_activity(
            process_data,
            ProcessingInput(data, should_fail=True),
            start_to_close_timeout=timedelta(seconds=10),
            # Configure retry behavior
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

# Client-side exception handling
async def execute_with_error_handling():
    try:
        result = await client.execute_workflow(
            DataProcessingWorkflow.run,
            "test-data",
            id="exception-workflow-id",
            task_queue="exception-task-queue",
        )
    except WorkflowFailureError as err:
        # Enhance error with stack trace
        append_temporal_stack(err)
        logger.exception("Workflow execution failed")
        raise

def append_temporal_stack(exc: BaseException) -> None:
    """Helper to append Temporal stack traces to exception messages."""
    while exc:
        if (isinstance(exc, FailureError) and exc.failure and
            exc.failure.stack_trace and "\\nStack:\\n" not in str(exc)):
            exc.args = (f"{exc}\\nStack:\\n{exc.failure.stack_trace.rstrip()}",)
        exc = exc.__cause__
```

## Local Activity

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_local_activity.py

## Authenticate using mTLS

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_mtls.py

## Custom Metrics

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/custom_metric/worker.py

## Encryption

https://github.com/temporalio/samples-python/blob/main/encryption/codec.py
https://github.com/temporalio/samples-python/blob/main/encryption/worker.py

## Polling (frequent)

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/polling/frequent/activities.py

## Polling (infrequent)

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/polling/infrequent/workflows.py

## Schedule

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/schedules/start_schedule.py
https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/schedules/trigger_schedule.py
https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/schedules/backfill_schedule.py

## Pydantic Converter

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/pydantic_converter/worker.py