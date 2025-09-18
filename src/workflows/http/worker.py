"""Worker for the HTTP Workflow."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ray

import ray
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from src.workflows.http.http_activities import http_get
from src.workflows.http.http_workflow import HttpWorkflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@ray.remote
class TemporalWorkerTask:
    """Ray task for running a Temporal worker."""

    def __init__(
        self,
        temporal_server_url: str = "localhost:7233",
        task_queue: str = "http-task-queue",
        max_concurrent_activities: int = 5,
    ) -> None:
        """Initialize the Temporal worker task.

        Args:
            temporal_server_url: The Temporal server URL to connect to
            task_queue: The task queue name for this worker
            max_concurrent_activities: Maximum number of concurrent activities

        """
        self.temporal_server_url = temporal_server_url
        self.task_queue = task_queue
        self.max_concurrent_activities = max_concurrent_activities
        self.client: Client | None = None
        self.worker: Worker | None = None

    async def start_worker(self) -> None:
        """Start the Temporal worker."""
        logger.info("Starting Temporal worker on Ray task...")

        # Connect to Temporal server
        self.client = await Client.connect(
            self.temporal_server_url, data_converter=pydantic_data_converter
        )

        # Create worker
        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[HttpWorkflow],
            activities=[http_get],
            activity_executor=ThreadPoolExecutor(self.max_concurrent_activities),
        )

        logger.info(
            "Temporal worker initialized - Task Queue: %s, Server: %s",
            self.task_queue,
            self.temporal_server_url,
        )

        # Run the worker (this will block until shutdown)
        await self.worker.run()

    async def shutdown(self) -> None:
        """Shutdown the worker gracefully."""
        logger.info("Shutting down Temporal worker...")
        if self.worker:
            self.worker.shutdown()
        if self.client:
            await self.client.close()


async def run_ray_worker(
    temporal_server_url: str = "localhost:7233",
    task_queue: str = "http-task-queue",
    max_concurrent_activities: int = 5,
    num_workers: int = 3,
) -> list[ray.ObjectRef]:
    """Run Temporal workers as Ray tasks.

    Args:
        temporal_server_url: The Temporal server URL to connect to
        task_queue: The task queue name for workers
        max_concurrent_activities: Maximum number of concurrent activities per worker
        num_workers: Number of worker instances to start

    Returns:
        List of Ray object references for the worker tasks

    """
    logger.info("Starting %d Temporal worker(s) as Ray tasks...", num_workers)

    # Create and start Ray worker tasks
    worker_tasks = []
    for i in range(num_workers):
        logger.info("Creating Ray worker task %d/%d", i + 1, num_workers)
        worker_task = TemporalWorkerTask.remote(
            temporal_server_url=temporal_server_url,
            task_queue=task_queue,
            max_concurrent_activities=max_concurrent_activities,
        )

        # Start the worker (this returns immediately as it's async)
        worker_ref = worker_task.start_worker.remote()
        worker_tasks.append(worker_ref)

    return worker_tasks


async def main() -> None:
    """Main function to start Ray and run Temporal workers."""
    # Initialize Ray if not already initialized
    if not ray.is_initialized():
        logger.info("Initializing Ray...")
        ray.init()

    try:
        # Start Ray workers
        worker_tasks = await run_ray_worker(
            temporal_server_url="localhost:7233",
            task_queue="http-task-queue",
            max_concurrent_activities=5,
        )

        logger.info("Ray workers started. Waiting for completion...")

        # Wait for workers to complete (they run indefinitely until interrupted)
        await asyncio.gather(*[ray.get(task) for task in worker_tasks])

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception:
        logger.exception("Error running Ray workers")
        raise
    finally:
        # Shutdown Ray
        if ray.is_initialized():
            logger.info("Shutting down Ray...")
            ray.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
