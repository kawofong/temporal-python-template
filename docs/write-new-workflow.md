# Write a New Workflow

## Table of Contents

- [File naming convention](#file-naming-convention)
- [Best practices when writing a new Workflow](#best-practices-when-writing-a-new-workflow)

1. Create a new subdirectory under `src/workflows/`
1. Create a workflow file with `@workflow.defn` class
1. Define input/output Pydantic models
1. Use the following Temporal primitives to build a Workflow:
   - Activity
   - Signal
   - Query
   - Update
   - Timer
1. Create a activities file
1. Add happy path tests for both workflows and activities
1. Create a Worker file for running the workflow

Follow existing naming conventions (see examples below).

## File naming convention

- `src/workflows/http/` - uses prefixed names: `http_activities.py`, `http_workflow.py`
- Test files always end with `_tests.py`

## Best practices when writing a new Workflow

- Always stubs Activities using `activity.logger.info` functions to simulate actions
- Within a Workflow, Use a reasonable value for `start_to_close_timeout` for each Activity invocation
- Within a Workflow, do not explicitly configure retries. Do not use `temporalio.common.RetryPolicy`.
- When Workflows, Activities, Updates, Signals, and Queries require input parameter or output value, use a single `pydantic` object to define input and output.
- Never use Child Workflows. Use Activities instead of Child Workflows.
- In the Workflow Definition, always include a `main` function that will instantiate a Temporal Client and execute the Workflow.

```python
async def main() -> None:  # pragma: no cover
    """Connects to the client, starts a worker, and executes the workflow."""
    from temporalio.client import Client  # noqa: PLC0415
    from temporalio.contrib.pydantic import pydantic_data_converter  # noqa: PLC0415

    client = await Client.connect(
        "localhost:7233", data_converter=pydantic_data_converter
    )
    input_data = HttpWorkflowInput(url="https://httpbin.org/anything/http-workflow")
    success_result = await client.execute_workflow(
        HttpWorkflow.run,
        input_data,
        id="http-workflow-id",
        task_queue="http-task-queue",
    )
    print(f"\nSuccessful Workflow Result: {success_result}\n")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())

```
