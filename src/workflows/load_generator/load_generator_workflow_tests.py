"""Tests for load generator workflow."""

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.worker import Worker

from src.workflows.load_generator.load_generator_activities import (
    NoopActivityInput,
    NoopActivityOutput,
)
from src.workflows.load_generator.load_generator_workflow import (
    GenerateLoadWorkflow,
    GenerateLoadWorkflowInput,
    RunActivityWorkflow,
    RunActivityWorkflowInput,
    RunActivityWorkflowOutput,
)


class TestLoadGeneratorWorkflow:
    """Test suite for Load Generator workflows."""

    @pytest.fixture
    def task_queue(self) -> str:
        """Generate unique task queue name for each test."""
        return f"test-load-generator-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_run_activity_workflow(self, client: Client, task_queue: str) -> None:
        """Test RunActivityWorkflow with mocked activity."""
        expected_activities = 5

        @activity.defn(name="noop_activity")
        async def mock_noop_activity(input: NoopActivityInput) -> NoopActivityOutput:
            return NoopActivityOutput(message=f"mocked: {input.message}")

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[RunActivityWorkflow],
            activities=[mock_noop_activity],
        ):
            result = await client.execute_workflow(
                RunActivityWorkflow.run,
                RunActivityWorkflowInput(number_of_activities=expected_activities),
                id=f"test-run-activity-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            assert isinstance(result, RunActivityWorkflowOutput)
            assert result.total_activities_executed == expected_activities

    @pytest.mark.asyncio
    async def test_generate_load_workflow(self, client: Client, task_queue: str) -> None:
        """Test GenerateLoadWorkflow runs and schedules children."""
        activity_counter = 0

        @activity.defn(name="noop_activity")
        async def mock_noop_activity(input: NoopActivityInput) -> NoopActivityOutput:
            nonlocal activity_counter
            activity_counter += 1
            return NoopActivityOutput(message=f"mocked: {input.message}")

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[GenerateLoadWorkflow, RunActivityWorkflow],
            activities=[mock_noop_activity],
        ):
            handle = await client.start_workflow(
                GenerateLoadWorkflow.run,
                GenerateLoadWorkflowInput(activity_per_second=5),
                id=f"test-generate-load-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Wait for some activities to run
            # In a time-skipping env, we might need to sleep to let the workflow progress
            # The workflow waits 1s between iterations.
            for _ in range(10):
                if activity_counter > 0:
                    break
                await asyncio.sleep(0.5)

            assert activity_counter > 0, "No activities were executed"

            await handle.cancel()

            # Verify cancellation
            with pytest.raises(WorkflowFailureError):
                await handle.result()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
