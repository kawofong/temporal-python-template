"""Workflow for generating load by executing activities.

To run this workflow, use the following command:

1. Run the worker:
    ```
    uv run -m src.workflows.load_generator.worker
    ```

2. Run the workflow:
    ```
    uv run -m src.workflows.load_generator.load_generator_workflow
    ```
"""

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, Field

    from src.workflows.load_generator.load_generator_activities import (
        NoopActivityInput,
        noop_activity,
    )

# A Workflow Execution can support up to 2,000 concurrent Activities.
# https://docs.temporal.io/cloud/limits#per-workflow-execution-concurrency-limits
MAX_CONCURRENT_ACTIVITIES = 2000


class GenerateLoadWorkflowInput(BaseModel):
    """Input for the load generator workflow."""

    activity_per_second: int = Field(
        default=1,
        gt=0,
        description="Approximate number of activities to run per second",
    )


@workflow.defn
class GenerateLoadWorkflow:
    """A workflow that generates load by running activities at a specified rate."""

    @workflow.run
    async def run(self, input: GenerateLoadWorkflowInput) -> None:
        """Run the workflow."""
        workflow.logger.info(
            "Starting Load Generator: %d activities/sec",
            input.activity_per_second,
        )
        num_child_wf_per_iter = input.activity_per_second // MAX_CONCURRENT_ACTIVITIES + 1
        # Enter loop to generate load
        while True:
            activities_left = input.activity_per_second
            child_wf_futures = []
            # Run child workflows in parallel
            for i in range(num_child_wf_per_iter):
                number_of_activities = min(activities_left, MAX_CONCURRENT_ACTIVITIES)
                future = workflow.execute_child_workflow(
                    RunActivityWorkflow.run,
                    RunActivityWorkflowInput(number_of_activities=number_of_activities),
                    id=f"{workflow.info().workflow_id}-activity-wf-{i}",
                )
                child_wf_futures.append(future)
                activities_left -= number_of_activities
            # Wait for all child workflows to complete
            await asyncio.gather(*child_wf_futures)
            # Wait for 1 second
            await asyncio.sleep(1)
            if workflow.info().is_continue_as_new_suggested():
                await workflow.wait_condition(workflow.all_handlers_finished)
                workflow.continue_as_new(input)


class RunActivityWorkflowInput(BaseModel):
    """Input for the load generator workflow."""

    number_of_activities: int = Field(
        ...,
        gt=0,
        le=MAX_CONCURRENT_ACTIVITIES,
        description="Number of activities to run",
    )


class RunActivityWorkflowOutput(BaseModel):
    """Output for the load generator workflow."""

    total_activities_executed: int


@workflow.defn
class RunActivityWorkflow:
    """A workflow that runs a number of activities in parallel."""

    @workflow.run
    async def run(self, input: RunActivityWorkflowInput) -> RunActivityWorkflowOutput:
        """Run the workflow."""
        workflow.logger.info(
            "Starting Run Activity Workflow: %d activities",
            input.number_of_activities,
        )

        results = await asyncio.gather(
            *[
                workflow.execute_activity(
                    noop_activity,
                    NoopActivityInput(message="ping"),
                    start_to_close_timeout=timedelta(seconds=1),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=1),
                    ),
                )
                for _ in range(input.number_of_activities)
            ]
        )

        return RunActivityWorkflowOutput(
            total_activities_executed=len(results),
        )


async def main() -> None:  # pragma: no cover
    """Connects to the client and executes the crawler workflow."""
    import uuid  # noqa: PLC0415

    from temporalio.client import Client  # noqa: PLC0415
    from temporalio.contrib.pydantic import pydantic_data_converter  # noqa: PLC0415

    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)

    input_data = GenerateLoadWorkflowInput(
        activity_per_second=1,
    )

    await client.start_workflow(
        GenerateLoadWorkflow.run,
        input_data,
        id=f"load-generator-{uuid.uuid4()}",
        task_queue="load-generator-task-queue",
    )

    print("Load generator workflow started")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
