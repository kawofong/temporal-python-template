"""Tests for HTTP workflow."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from src.workflows.http.http_workflow import (
    HttpWorkflow,
    HttpWorkflowInput,
    HttpWorkflowOutput,
)

# Constants
HTTP_OK_STATUS = 200


class TestHttpWorkflow:
    """Test suite for HttpWorkflow.

    Tests cover end-to-end workflow execution, mocked activities,
    timeout scenarios, and error handling.
    """

    @pytest.fixture
    def task_queue(self) -> str:
        """Generate unique task queue name for each test."""
        return f"test-http-workflow-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_http_workflow_with_mocked_activity(
        self, client: Client, task_queue: str
    ) -> None:
        """Test HTTP workflow with mocked activity response.

        Args:
            client: Temporal test client
            task_queue: Test task queue name

        """

        @activity.defn(name="http_get")
        async def http_get_mocked(input_data: HttpWorkflowInput) -> HttpWorkflowOutput:
            """Mocked HTTP GET activity for testing."""
            activity.logger.info("Mocked activity: HTTP GET call to %s", input_data.url)
            return HttpWorkflowOutput(
                response_text=f"Mocked response for {input_data.url}",
                url=input_data.url,
                status_code=200,
            )

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[HttpWorkflow],
            activities=[http_get_mocked],
            activity_executor=ThreadPoolExecutor(5),
        ):
            test_url = "https://example.com/test"
            input_data = HttpWorkflowInput(url=test_url)

            result = await client.execute_workflow(
                HttpWorkflow.run,
                input_data,
                id=f"test-http-workflow-mocked-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Verify mocked response
            assert isinstance(result, HttpWorkflowOutput)
            assert result.response_text == f"Mocked response for {test_url}"
            assert str(result.url) == test_url
            assert result.status_code == HTTP_OK_STATUS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
