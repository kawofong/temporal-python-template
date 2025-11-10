# Temporal Patterns

## Table of Contents

- [Activity Choice](#activity-choice)
- [Parallel Activity](#parallel-activity)
- [Cancellation](#cancellation)
- [Continue-as-New](#continue-as-new)
- [Long-running Entity](#long-running-entity)
- [Concurrent Timers](#concurrent-timers)
- [Child Workflow](#child-workflow)
- [Exceptions](#exceptions)
- [Local Activity](#local-activity)
- [Authenticate using mTLS](#authenticate-using-mtls)
- [Custom Metrics](#custom-metrics)
- [Encryption](#encryption)
- [Polling (frequent)](#polling-frequent)
- [Polling (infrequent)](#polling-infrequent)
- [Schedule](#schedule)
- [Pydantic Converter](#pydantic-converter)

## Activity Choice

The Activity Choice pattern enables workflows to dynamically select and execute different activities based on input conditions. This pattern is useful for conditional processing where different business logic needs to be applied based on data values.

**Key Implementation:**

- Use conditional logic (`if/elif/else`) to select activity functions
- Enables flexible workflow execution paths while maintaining deterministic replay behavior.
- Each activity handles specific business logic for different cases

```python
from enum import IntEnum
from typing import List
from temporalio import activity, workflow

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

class Fruit(IntEnum):
    APPLE = 1
    BANANA = 2
    CHERRY = 3

class ShoppingItem(BaseModel):
    fruit: Fruit
    amount: int

class ShoppingList(BaseModel):
    items: List[ShoppingItem]

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
from typing import Optional
from temporalio import workflow

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

class WorkflowState(BaseModel):
    iteration: int = 0
    processed_items: int = 0

class WorkflowInput(BaseModel):
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

## Long-running Entity

The Long-running Entity pattern enables workflows to model stateful entities that persist over long periods and respond to external events. This pattern uses signals, queries, and updates to manage entity state while leveraging Continue-as-New to prevent unbounded history growth.

**Key Implementation:**

- Use `@workflow.query` to expose entity state for external inspection
- Use `@workflow.signal` to modify entity state asynchronously
- Use `@workflow.update` to modify entity state with validation and return values
- Implement `while True` loop with `workflow.wait_condition()` for entity lifecycle management
- Use Continue-as-New when `workflow.info().is_continue_as_new_suggested()` returns `True`
- Use `await workflow.wait_condition(workflow.all_handlers_finished)` to wait for all handlers to finish before Workflow termination and Continue-as-New
- Handle entity termination through state flags and conditional logic
- Essential for modeling business entities like user accounts, orders, digital twins, or long-running processes

```python
from datetime import datetime, timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

@workflow.defn
class CustomerRewardAccount:
    """Long-running entity workflow for managing customer reward accounts."""

    def __init__(self):
        # Entity state maintained throughout workflow lifetime
        self._level: CustomerRewardLevel = CustomerRewardLevel.BASIC
        self._points: int = 0
        self._is_active: bool = True
        self._user_id: str | None = None
        self._create_time: datetime | None = None
        self._cancel_time: datetime | None = None
        self._update_count: int = 0

    @workflow.run
    async def run(self, inp: CustomerRewardAccountInput) -> CustomerRewardAccountStatus:
        """Initialize entity and enter long-running loop."""
        workflow.logger.info("Creating reward account for %s", inp.user_id)
        self._create_time = workflow.now()

        # Initialize entity with external data
        user: UserInfo = await workflow.execute_activity(
            get_user,
            inp.user_id,
            start_to_close_timeout=timedelta(seconds=1),
        )
        self._user_id = user.id

        workflow.logger.info(
            "Reward account for %s created at %s",
            self._user_id,
            self._create_time
        )

        # Long-running entity loop
        while True:
            # Wait for entity termination or update count threshold
            await workflow.wait_condition(
                lambda: not self._is_active or workflow.info().is_continue_as_new_suggested()
            )

            # Handle entity termination
            if not self._is_active:
                workflow.logger.info(
                    "Terminating reward account for %s at %s",
                    self._user_id,
                    self._cancel_time,
                )
                await workflow.wait_condition(workflow.all_handlers_finished)
                return CustomerRewardAccountStatus(
                    level=self._level,
                    points=self._points,
                    is_active=self._is_active,
                )

            # Handle Continue-as-New for history management
            if workflow.info().is_continue_as_new_suggested():
                await workflow.wait_condition(workflow.all_handlers_finished)
                workflow.continue_as_new(
                    CustomerRewardAccountInput(
                        user_id=self._user_id,
                        starting_points=self._points,
                        starting_level=self._level,
                    )
                )

    @workflow.query
    def query_reward_status(self) -> CustomerRewardAccountStatus:
        """Query handler to expose current entity state."""
        return CustomerRewardAccountStatus(
            level=self._level,
            points=self._points,
            is_active=self._is_active,
        )

    @workflow.update
    async def cancel(self) -> CustomerRewardAccountStatus:
        """Update handler to terminate the entity."""
        self._is_active = False
        self._cancel_time = workflow.now()
        return CustomerRewardAccountStatus(
            level=self._level,
            points=self._points,
            is_active=self._is_active,
        )

    @workflow.update
    async def add_points(self, inp: AddPointInput) -> CustomerRewardAccountStatus:
        """Update handler to modify entity state with business logic."""
        workflow.logger.info("Adding points for %s by %i", self._user_id, inp.points)

        self._update_count += 1
        self._points += inp.points
        self._points = max(self._points, 0)  # Prevent negative points

        # Update derived state based on business rules
        if 500 <= self._points < 1000:
            self._level = CustomerRewardLevel.GOLD
        elif self._points >= 1000:
            self._level = CustomerRewardLevel.PLATINUM
        else:
            self._level = CustomerRewardLevel.BASIC

        return CustomerRewardAccountStatus(
            level=self._level,
            points=self._points,
            is_active=self._is_active,
        )

    @add_points.validator
    def validate_add_point(self, inp: AddPointInput) -> None:
        """Validate update input before processing."""
        if not isinstance(inp.points, int):
            raise ValueError("Points must be an integer.")
```

**Benefits:**

- **Stateful Processing**: Maintains complex entity state across long periods
- **Real-time Interaction**: Responds immediately to queries and updates
- **History Management**: Uses Continue-as-New to prevent unbounded growth
- **Strong Consistency**: All state changes are durably persisted
- **Event Sourcing**: Complete audit trail of all entity state changes

## Concurrent Timers

The Concurrent Timers pattern enables workflows to manage multiple independent timers that can fire at different intervals. This pattern uses `asyncio.create_task()` with `workflow.wait()` to efficiently handle multiple concurrent timers, making it ideal for scheduling recurring events with different frequencies.

**Key Implementation:**

- Use `asyncio.create_task(asyncio.sleep())` to create independent timer tasks
- Use `workflow.wait()` with `asyncio.FIRST_COMPLETED` to wait for any timer to complete
- Reset completed timers by creating new tasks with the same intervals
- Handle multiple timer events in a single workflow execution loop
- Essential for managing recurring events with different schedules

```python
import asyncio
from datetime import timedelta
from temporalio import activity, workflow

@activity.defn
async def send_notification(user_email: str, message: str) -> None:
    # Replace this stub with your actual notification logic:
    # e.g., email, Slack, push, etc.
    activity.logger.info(f"[Notify] {user_email}: {message}")

@workflow.defn
class MaintenanceWorkflow:
    @workflow.run
    async def run(self, user_email: str) -> None:
        # Create concurrent timers for different maintenance events
        oil_change_timer = asyncio.create_task(
            asyncio.sleep(timedelta(months=3).total_seconds())  # Every 3 months
        )
        inspection_timer = asyncio.create_task(
            asyncio.sleep(timedelta(days=365).total_seconds())  # Yearly
        )
        coolant_timer = asyncio.create_task(
            asyncio.sleep(timedelta(months=24).total_seconds())  # Every 2 years
        )

        while True:
            # Wait for whichever timer fires first
            done, _ = await workflow.wait(
                {oil_change_timer, inspection_timer, coolant_timer},
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Handle oil change timer
            if oil_change_timer in done:
                workflow.logger.info("Time for oil change")
                await workflow.execute_activity(
                    send_notification,
                    user_email,
                    "Your car needs an oil change",
                    start_to_close_timeout=timedelta(seconds=30),
                )
                # Reset timer for next oil change
                oil_change_timer = asyncio.create_task(
                    asyncio.sleep(timedelta(months=3).total_seconds())
                )

            # Handle inspection timer
            if inspection_timer in done:
                workflow.logger.info("Time for car inspection")
                await workflow.execute_activity(
                    send_notification,
                    user_email,
                    "Your car needs an annual inspection",
                    start_to_close_timeout=timedelta(seconds=30),
                )
                # Reset timer for next inspection
                inspection_timer = asyncio.create_task(
                    asyncio.sleep(timedelta(days=365).total_seconds())
                )

            # Handle coolant timer
            if coolant_timer in done:
                workflow.logger.info("Time for coolant change")
                await workflow.execute_activity(
                    send_notification,
                    user_email,
                    "Your car needs a coolant system service",
                    start_to_close_timeout=timedelta(seconds=30),
                )
                # Reset timer for next coolant change
                coolant_timer = asyncio.create_task(
                    asyncio.sleep(timedelta(months=24).total_seconds())
                )
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
from temporalio import workflow
from temporalio.workflow import ParentClosePolicy

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

class ComposeGreetingInput(BaseModel):
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
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import FailureError

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

class ProcessingInput(BaseModel):
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
from datetime import timedelta
from temporalio import activity, workflow

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

class ProcessingInput(BaseModel):
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

The Encryption pattern enables end-to-end encryption of workflow and activity payloads using custom payload codecs. This ensures sensitive data is encrypted at rest and in transit, with only authorized workers able to decrypt the data.

**Key Implementation:**

- Create custom `PayloadCodec` to handle encryption/decryption of payload data
- Configure `data_converter` with custom codec for both clients and workers
- Include key ID metadata for key rotation and management
- Essential for protecting sensitive data in workflows

```python
import os
from typing import Iterable, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from temporalio.api.common.v1 import Payload
from temporalio.converter import DataConverter, PayloadCodec
import temporalio.converter
from temporalio.client import Client
from temporalio.worker import Worker

class EncryptionCodec(PayloadCodec):
    """Custom codec for encrypting/decrypting workflow payloads."""

    def __init__(self, key_id: str = "production-key-id", key: bytes = None) -> None:
        super().__init__()
        self.key_id = key_id
        if key is None:
            # In production, load from secure key management system
            key = os.environ.get("TEMPORAL_ENCRYPTION_KEY", "").encode()
        self.encryptor = AESGCM(key)

    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        """Encrypt all payloads with AES-GCM encryption."""
        return [
            Payload(
                metadata={
                    "encoding": b"binary/encrypted",
                    "encryption-key-id": self.key_id.encode(),
                },
                data=self.encrypt(p.SerializeToString()),
            )
            for p in payloads
        ]

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        """Decrypt payloads, skipping non-encrypted ones."""
        ret: List[Payload] = []
        for p in payloads:
            # Skip non-encrypted payloads
            if p.metadata.get("encoding", b"").decode() != "binary/encrypted":
                ret.append(p)
                continue

            # Verify key ID matches
            key_id = p.metadata.get("encryption-key-id", b"").decode()
            if key_id != self.key_id:
                raise ValueError(f"Unknown key ID: {key_id}")

            # Decrypt and append
            ret.append(Payload.FromString(self.decrypt(p.data)))
        return ret

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data with random nonce."""
        nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
        return nonce + self.encryptor.encrypt(nonce, data, None)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data, extracting nonce from prefix."""
        nonce = data[:12]
        ciphertext = data[12:]
        return self.encryptor.decrypt(nonce, ciphertext, None)

# Configure client and worker with encryption
async def create_encrypted_client() -> Client:
    """Create client with encryption codec."""
    # Create data converter with custom encryption codec
    default_converter = temporalio.converter.default()
    encrypted_converter = DataConverter(
        payload_converters=default_converter.payload_converters,
        failure_converters=default_converter.failure_converters,
        payload_codec=EncryptionCodec()
    )

    return await Client.connect(
        "localhost:7233",
        data_converter=encrypted_converter,
    )

async def run_encrypted_worker():
    """Run worker with encryption support."""
    client = await create_encrypted_client()

    async with Worker(
        client,
        task_queue="encrypted-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activity],
    ):
        print("Encrypted worker running...")
        # Worker processes encrypted payloads transparently

# Key management best practices:
# - Use environment variables or secure key management systems
# - Implement key rotation with multiple key IDs
# - Never hardcode encryption keys in source code
```

## Polling (frequent)

The Frequent Polling pattern enables activities to continuously poll external services until a condition is met or data becomes available. This pattern uses heartbeating and exception handling to maintain resilience during polling operations.

**Key Implementation:**

- Use infinite loop with `while True` for continuous polling
- Implement `activity.heartbeat()` to prevent activity timeouts during long polls
- Handle exceptions gracefully to continue polling when services are temporarily unavailable
- Use `asyncio.sleep()` for polling intervals to avoid overwhelming external services
- Handle `asyncio.CancelledError` for proper cleanup when activity is cancelled

```python
import asyncio
from temporalio import activity
from typing import Optional

@activity.defn
async def poll_external_service(service_url: str, poll_interval: int = 1) -> str:
    """Poll external service until data is available."""

    while True:
        try:
            try:
                # Attempt to get result from external service
                result = await fetch_from_service(service_url)
                if result is not None:
                    activity.logger.info(f"Service returned result: {result}")
                    return result
            except Exception as e:
                # Log but swallow exception - service may be temporarily down
                activity.logger.debug(
                    f"Service call failed: {e}, retrying in {poll_interval}s",
                    exc_info=True
                )
            # Heartbeat to prevent activity timeout
            activity.heartbeat(f"Polling service at {service_url}")
            # Wait before next poll attempt
            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            # Handle cancellation for cleanup
            activity.logger.info("Polling activity cancelled")
            # Perform any necessary cleanup here
            raise


async def fetch_from_service(url: str) -> Optional[str]:
    """Simulate external service call."""
    # Implementation would make actual HTTP request
    # Return None if no data available, raise exception on error
    pass

# Usage in workflow:
# result = await workflow.execute_activity(
#     poll_external_service,
#     "https://api.example.com/status",
#     start_to_close_timeout=timedelta(minutes=30),
#     heartbeat_timeout=timedelta(seconds=10),
# )
```

## Polling (infrequent)

The Infrequent Polling pattern uses Temporal's retry mechanism to poll external services at longer intervals without maintaining long-running activities. This pattern leverages activity failures and retry policies to achieve polling behavior efficiently.

**Key Implementation:**

- Use short activity timeouts with retry policies for polling intervals
- Configure `RetryPolicy` with appropriate `initial_interval` for polling frequency
- Set `backoff_coefficient=1.0` to maintain consistent polling intervals
- Activities fail quickly and rely on Temporal's retry system for timing
- More efficient than long-running activities for infrequent polling needs

```python
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Import activities safely in workflow
with workflow.unsafe.imports_passed_through():
    from my_app.activities import check_external_service

@activity.defn
async def poll_service_status(service_url: str) -> str:
    """Short-lived activity that checks service status."""

    # Attempt to get result from external service
    result = await fetch_service_status(service_url)

    if result is None or not result.is_ready:
        # Fail the activity to trigger retry
        activity.logger.info("Service not ready, will retry")
        raise RuntimeError("Service not ready")

    activity.logger.info(f"Service is ready: {result.status}")
    return result.status

@activity.defn
async def check_job_completion(job_id: str) -> bool:
    """Check if a long-running job has completed."""

    job_status = await get_job_status(job_id)

    if job_status.state in ["pending", "running"]:
        activity.logger.info(f"Job {job_id} still {job_status.state}")
        raise RuntimeError(f"Job not complete: {job_status.state}")

    if job_status.state == "failed":
        raise ValueError(f"Job {job_id} failed: {job_status.error}")

    activity.logger.info(f"Job {job_id} completed successfully")
    return True

@workflow.defn
class InfrequentPollingWorkflow:
    @workflow.run
    async def run(self, service_url: str) -> str:
        # Poll every 60 seconds until service is ready
        return await workflow.execute_activity(
            poll_service_status,
            service_url,
            start_to_close_timeout=timedelta(seconds=5),  # Short timeout
            retry_policy=RetryPolicy(
                backoff_coefficient=1.0,  # No exponential backoff
                initial_interval=timedelta(seconds=60),  # Poll every 60 seconds
                maximum_interval=timedelta(seconds=60),   # Keep consistent
                maximum_attempts=100,  # Limit total attempts
            ),
        )

@workflow.defn
class JobMonitoringWorkflow:
    @workflow.run
    async def run(self, job_id: str) -> bool:
        # Check job completion every 5 minutes
        return await workflow.execute_activity(
            check_job_completion,
            job_id,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                backoff_coefficient=1.0,
                initial_interval=timedelta(minutes=5),  # Check every 5 minutes
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=48,  # 4 hours maximum (48 * 5min)
            ),
        )

# Helper functions (would be implemented based on your external services)
async def fetch_service_status(url: str):
    """Fetch status from external service."""
    pass

async def get_job_status(job_id: str):
    """Get job status from external system."""
    pass

# Benefits over frequent polling:
# - Lower resource usage (no long-running activities)
# - Leverages Temporal's built-in retry mechanism
# - Automatic failure handling and exponential backoff if needed
# - Better for polling intervals > 30 seconds
```

## Schedule

The Schedule pattern enables automatic execution of workflows at specified intervals or times using Temporal's built-in scheduling system. Schedules provide cron-like functionality with additional features like manual triggering, backfilling, and overlap policies.

**Key Implementation:**

- Use `client.create_schedule()` to define recurring workflow executions
- Configure `ScheduleSpec` with intervals, cron expressions, or calendars
- Support manual triggering with `handle.trigger()` for on-demand execution
- Enable backfilling with `handle.backfill()` to run missed executions
- Control execution overlap with `ScheduleOverlapPolicy` settings

```python
import asyncio
from datetime import datetime, timedelta
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleBackfill,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    ScheduleSpec,
    ScheduleState,
)
from temporalio import workflow

@workflow.defn
class ScheduledWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        workflow.logger.info(f"Scheduled execution with data: {data}")
        return f"Processed: {data}"

async def create_interval_schedule():
    """Create a schedule that runs every 2 minutes."""
    client = await Client.connect("localhost:7233")

    await client.create_schedule(
        "interval-schedule-id",
        Schedule(
            action=ScheduleActionStartWorkflow(
                ScheduledWorkflow.run,
                "scheduled data",  # Workflow arguments
                id="scheduled-workflow-id",
                task_queue="scheduled-task-queue",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(minutes=2))]
            ),
            state=ScheduleState(
                note="Runs every 2 minutes",
                paused=False,  # Schedule is active
            ),
        ),
    )

async def create_cron_schedule():
    """Create a schedule using cron expression."""
    client = await Client.connect("localhost:7233")

    await client.create_schedule(
        "cron-schedule-id",
        Schedule(
            action=ScheduleActionStartWorkflow(
                ScheduledWorkflow.run,
                "daily report",
                id="daily-report-workflow",
                task_queue="reports-task-queue",
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 9 * * MON-FRI"]  # 9 AM weekdays
            ),
            state=ScheduleState(note="Daily report generation"),
        ),
    )

async def trigger_schedule_manually():
    """Manually trigger a scheduled workflow execution."""
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle("interval-schedule-id")

    # Trigger immediate execution
    await handle.trigger()
    print("Schedule triggered manually")

async def backfill_schedule():
    """Backfill missed schedule executions."""
    client = await Client.connect("localhost:7233")
    handle = client.get_schedule_handle("interval-schedule-id")

    now = datetime.utcnow()
    await handle.backfill(
        ScheduleBackfill(
            start_at=now - timedelta(hours=2),  # Backfill last 2 hours
            end_at=now - timedelta(minutes=5),  # Up to 5 minutes ago
            overlap=ScheduleOverlapPolicy.ALLOW_ALL,  # Allow overlapping executions
        ),
    )
    print("Schedule backfilled successfully")

async def manage_schedule():
    """Comprehensive schedule management example."""
    client = await Client.connect("localhost:7233")

    # Create schedule with multiple intervals
    await client.create_schedule(
        "complex-schedule-id",
        Schedule(
            action=ScheduleActionStartWorkflow(
                ScheduledWorkflow.run,
                "complex data",
                id="complex-workflow-id",
                task_queue="complex-task-queue",
            ),
            spec=ScheduleSpec(
                intervals=[
                    ScheduleIntervalSpec(every=timedelta(minutes=30)),  # Every 30 min
                ],
                cron_expressions=["0 0 * * SUN"],  # Also weekly on Sunday
            ),
            state=ScheduleState(
                note="Mixed interval and cron schedule",
                paused=False,
            ),
        ),
    )

    # Get handle for management operations
    handle = client.get_schedule_handle("complex-schedule-id")

    # Pause the schedule
    await handle.pause(note="Pausing for maintenance")

    # Resume the schedule
    await handle.unpause(note="Maintenance complete")

    # Update the schedule
    async def updater(input):
        input.schedule.state.note = "Updated schedule"
        return input.schedule

    await handle.update(updater)

# Common use cases:
# - Periodic data processing (ETL jobs)
# - Regular health checks and monitoring
# - Scheduled reports and notifications
# - Batch processing at off-peak hours
# - Cleanup and maintenance tasks
```

## Pydantic Converter

The Pydantic Converter pattern enables seamless serialization and deserialization of Pydantic models in Temporal workflows and activities. This provides type safety, validation, and rich data modeling capabilities while maintaining compatibility with Temporal's payload system.

**Key Implementation:**

- Use `pydantic_data_converter` for automatic Pydantic model serialization
- Import Pydantic safely with `workflow.unsafe.imports_passed_through()`
- Configure both client and worker with the same data converter
- Leverage Pydantic's validation and type conversion features
- Essential for complex data structures and type safety

```python
from datetime import datetime, timedelta
from ipaddress import IPv4Address
from typing import List
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Import Pydantic safely for workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, validator
    from temporalio.contrib.pydantic import pydantic_data_converter

class UserData(BaseModel):
    """Simple user data with validation."""
    user_id: int
    ip_address: IPv4Address

    @validator('user_id')
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('user_id must be positive')
        return v

@activity.defn
async def process_users(users: List[UserData]) -> int:
    """Process users and return count."""
    activity.logger.info(f"Processing {len(users)} users")

    for user in users:
        # Pydantic ensures type safety and validation
        activity.logger.info(f"Processing user {user.user_id} from {user.ip_address}")

    return len(users)

@workflow.defn
class PydanticWorkflow:
    @workflow.run
    async def run(self, users: List[UserData]) -> int:
        """Process users with type-safe Pydantic models."""
        return await workflow.execute_activity(
            process_users,
            users,
            start_to_close_timeout=timedelta(minutes=1)
        )

# Setup client and worker with Pydantic converter
async def main():
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter
    )

    async with Worker(
        client,
        task_queue="pydantic-task-queue",
        workflows=[PydanticWorkflow],
        activities=[process_users],
    ):
        # Execute workflow with validated Pydantic models
        users = [
            UserData(user_id=1, ip_address="192.168.1.1"),
            UserData(user_id=2, ip_address="10.0.0.1")
        ]

        result = await client.execute_workflow(
            PydanticWorkflow.run,
            users,
            id="pydantic-workflow-id",
            task_queue="pydantic-task-queue"
        )

        print(f"Processed {result} users")
```
