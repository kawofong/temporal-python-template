"""HTTP workflow for making external API calls."""

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflows.http.activities import http_get


@workflow.defn
class HttpWorkflow:
    """A basic workflow that makes an HTTP GET call."""

    @workflow.run
    async def run(self, url: str) -> str:
        """Run the workflow."""
        workflow.logger.info("Workflow: triggering HTTP GET activity to %s", url)
        return await workflow.execute_activity(
            http_get,
            url,
            start_to_close_timeout=timedelta(seconds=3),
        )


async def main() -> None:
    """Connects to the client, starts a worker, and executes the workflow."""
    from temporalio.client import Client  # noqa: PLC0415

    client = await Client.connect("localhost:7233")
    success_result = await client.execute_workflow(
        HttpWorkflow.run,
        "https://httpbin.org/anything/http-workflow",
        id="http-workflow-id",
        task_queue="http-task-queue",
    )
    print(f"\nSuccessful Workflow Result: {success_result}\n")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
