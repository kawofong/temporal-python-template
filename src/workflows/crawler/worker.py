"""Worker for the web crawler workflow."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from src.workflows.crawler.crawler_activities import parse_links_from_url
from src.workflows.crawler.crawler_workflow import CrawlerWorkflow


async def main() -> None:
    """Start the crawler worker."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Connect to Temporal server
    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)
    task_queue = "crawler-task-queue"
    # Create worker
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[CrawlerWorkflow],
        activities=[parse_links_from_url],
        activity_executor=ThreadPoolExecutor(max_workers=16),
    )

    print(f"Starting crawler worker on task queue '{task_queue}'...")  # noqa: T201
    print("Press Ctrl+C to stop the worker.")  # noqa: T201

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
