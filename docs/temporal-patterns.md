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

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_cancellation.py

## Continue-as-New

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_continue_as_new.py

## Child Workflow

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_child_workflow.py

## Exceptions

https://raw.githubusercontent.com/temporalio/samples-python/refs/heads/main/hello/hello_exception.py

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