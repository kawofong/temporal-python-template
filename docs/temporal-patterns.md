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

The Local Activity pattern enables workflows to execute activities directly within the worker process without task queue scheduling. Local activities provide lower latency and reduced overhead for short-duration operations, but sacrifice some of Temporal's durability guarantees.

**Key Implementation:**

- Use `workflow.execute_local_activity()` instead of `workflow.execute_activity()`
- Activities run in the same worker process as the workflow
- Lower latency and reduced network overhead compared to regular activities
- Limited retry capabilities and no cross-worker execution
- Best for fast, lightweight operations that don't require full durability
- Avoid Local Acitivty for external API calls, long-running operations, operations requiring durability

```python
from dataclasses import dataclass
from datetime import timedelta
from temporalio import activity, workflow

@dataclass
class ProcessingInput:
    greeting: str
    name: str

@activity.defn
def compose_greeting(input: ProcessingInput) -> str:
    """Fast local activity for simple string processing."""
    return f"{input.greeting}, {input.name}!"

@activity.defn
def validate_input(data: str) -> bool:
    """Quick validation that runs locally."""
    return len(data.strip()) > 0

@workflow.defn
class LocalActivityWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        # Execute local activity for fast processing
        result = await workflow.execute_local_activity(
            compose_greeting,
            ProcessingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Chain multiple local activities
        is_valid = await workflow.execute_local_activity(
            validate_input,
            result,
            start_to_close_timeout=timedelta(seconds=5),
        )

        return result if is_valid else "Invalid result"
```

## Authenticate using mTLS

The mTLS (mutual Transport Layer Security) pattern enables secure authentication between Temporal clients/workers and the Temporal server using client certificates. This provides strong authentication and encryption for production deployments.

**Key Implementation:**

- Use `TLSConfig` to configure client certificates and server CA validation
- Load client certificate and private key from files
- Optionally specify server root CA certificate for validation
- Apply TLS configuration to both client connections and workers
- Essential for secure production Temporal deployments

```python
import argparse
from typing import Optional
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.service import TLSConfig
from temporalio.worker import Worker

async def create_secure_client(
    target_host: str = "localhost:7233",
    namespace: str = "default",
    server_root_ca_cert_path: Optional[str] = None,
    client_cert_path: str = "client.crt",
    client_key_path: str = "client.key"
) -> Client:
    """Create a Temporal client with mTLS authentication."""

    # Load server root CA certificate (optional)
    server_root_ca_cert: Optional[bytes] = None
    if server_root_ca_cert_path:
        with open(server_root_ca_cert_path, "rb") as f:
            server_root_ca_cert = f.read()

    # Load client certificate and private key (required)
    with open(client_cert_path, "rb") as f:
        client_cert = f.read()

    with open(client_key_path, "rb") as f:
        client_key = f.read()

    # Create client with TLS configuration
    return await Client.connect(
        target_host,
        namespace=namespace,
        tls=TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        ),
    )

@workflow.defn
class SecureWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        return f"Securely processed: {data}"

# Usage example
async def main():
    # Create secure client
    client = await create_secure_client(
        target_host="your-temporal-server:7233",
        client_cert_path="/path/to/client.crt",
        client_key_path="/path/to/client.key",
        server_root_ca_cert_path="/path/to/server-ca.crt"
    )

    # Worker also uses the same secure client
    async with Worker(
        client,
        task_queue="secure-task-queue",
        workflows=[SecureWorkflow],
    ):
        result = await client.execute_workflow(
            SecureWorkflow.run,
            "sensitive-data",
            id="secure-workflow-id",
            task_queue="secure-task-queue",
        )
        print(f"Result: {result}")
```

## Custom Metrics

The Custom Metrics pattern enables workflows and activities to emit custom telemetry data using Temporal's built-in metrics system. This pattern uses interceptors to capture timing data and Prometheus for metrics collection and monitoring.

**Key Implementation:**

- Use `Runtime` with `TelemetryConfig` to configure Prometheus metrics
- Create interceptors to capture custom metrics during activity execution
- Use `activity.metric_meter()` to create and record histogram metrics
- Configure Prometheus endpoint for metrics collection
- Essential for monitoring workflow performance and business metrics

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from temporalio import activity
from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    Worker,
)

class CustomMetricsInterceptor(Interceptor):
    """Interceptor to add custom metrics collection."""

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return ActivityMetricsInterceptor(next)

class ActivityMetricsInterceptor(ActivityInboundInterceptor):
    """Captures activity scheduling and execution metrics."""

    async def execute_activity(self, input: ExecuteActivityInput):
        # Calculate schedule-to-start latency
        schedule_to_start = (
            activity.info().started_time -
            activity.info().current_attempt_scheduled_time
        )

        # Create custom histogram metric
        meter = activity.metric_meter()
        latency_histogram = meter.create_histogram_timedelta(
            "activity_schedule_to_start_latency",
            description="Time between activity scheduling and start",
            unit="duration",
        )

        # Record metric with labels
        latency_histogram.record(
            schedule_to_start,
            {
                "workflow_type": activity.info().workflow_type,
                "activity_type": activity.info().activity_type,
            }
        )

        # Create business metrics
        counter = meter.create_counter_int(
            "activity_executions_total",
            description="Total number of activity executions",
        )
        counter.add(1, {"status": "started"})

        try:
            result = await self.next.execute_activity(input)
            counter.add(1, {"status": "completed"})
            return result
        except Exception as e:
            counter.add(1, {"status": "failed"})
            raise

async def create_metrics_worker():
    """Create worker with custom metrics configuration."""

    # Configure Prometheus metrics
    runtime = Runtime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(bind_address="0.0.0.0:9090")
        )
    )

    # Create client with metrics runtime
    client = await Client.connect("localhost:7233", runtime=runtime)

    # Create worker with custom interceptor
    return Worker(
        client,
        task_queue="metrics-task-queue",
        interceptors=[CustomMetricsInterceptor()],
        workflows=[MyWorkflow],
        activities=[my_activity],
        activity_executor=ThreadPoolExecutor(2),
    )

# Metrics are available at http://localhost:9090/metrics
# Common metrics: activity latency, execution counts, error rates, business KPIs
```

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