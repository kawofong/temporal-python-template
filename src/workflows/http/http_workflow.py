"""HTTP workflow for making external API calls."""

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

    from src.workflows.http.http_activities import HttpGetActivityOutput, http_get


class HttpWorkflowInput(BaseModel):
    """Input model for HTTP workflow."""

    url: str
    """The URL to make the HTTP GET request to."""


class HttpWorkflowOutput(BaseModel):
    """Output model for HTTP workflow."""

    response_text: str
    """The response text from the HTTP GET request."""

    url: str
    """The original URL that was requested."""

    status_code: int = 200
    """The HTTP status code of the response."""


@workflow.defn
class HttpWorkflow:
    """A basic workflow that makes an HTTP GET call."""

    @workflow.run
    async def run(self, input: HttpWorkflowInput) -> HttpWorkflowOutput:
        """Run the workflow."""
        workflow.logger.info("Workflow: triggering HTTP GET activity to %s", input.url)
        http_get_result: HttpGetActivityOutput = await workflow.execute_activity(
            http_get,
            input,
            start_to_close_timeout=timedelta(seconds=3),
        )
        return HttpWorkflowOutput(
            response_text=http_get_result.response_text,
            url=input.url,
            status_code=http_get_result.status_code,
        )


async def main() -> None:  # pragma: no cover
    """Connects to the client, starts a worker, and executes the workflow."""
    from temporalio.client import Client  # noqa: PLC0415
    from temporalio.contrib.pydantic import pydantic_data_converter  # noqa: PLC0415

    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)
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
