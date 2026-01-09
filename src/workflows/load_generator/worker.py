"""Worker for the Load Generator workflow."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from src.workflows.load_generator.load_generator_activities import noop_activity
from src.workflows.load_generator.load_generator_workflow import (
    GenerateLoadWorkflow,
    RunActivityWorkflow,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Connects to the client and starts the worker."""
    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)

    worker = Worker(
        client,
        task_queue="load-generator-task-queue",
        workflows=[GenerateLoadWorkflow, RunActivityWorkflow],
        activities=[noop_activity],
    )

    logger.info("Starting Load Generator worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
