"""Test configuration for workflow tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment


@pytest_asyncio.fixture(scope="session")
async def env() -> AsyncGenerator[WorkflowEnvironment, None]:
    """Create a Temporal test workflow environment."""
    env = await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter,
    )
    yield env
    await env.shutdown()


@pytest_asyncio.fixture
async def client(env: WorkflowEnvironment) -> Client:
    """Create a Temporal test client."""
    return env.client
