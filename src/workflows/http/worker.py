"""Worker for the HTTP Workflow."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from src.workflows.http.http_activities import http_get
from src.workflows.http.http_workflow import HttpWorkflow


async def main() -> None:
    """Connects to the client, starts a worker, and executes the workflow."""
    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)
    task_queue = "http-task-queue"
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[HttpWorkflow],
        activities=[http_get],
        activity_executor=ThreadPoolExecutor(5),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
