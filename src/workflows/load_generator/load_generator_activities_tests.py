"""Tests for load generator activities."""

import pytest

from src.workflows.load_generator.load_generator_activities import (
    NoopActivityInput,
    noop_activity,
)


@pytest.mark.asyncio
async def test_noop_activity() -> None:
    """Test the noop activity."""
    input_data = NoopActivityInput(message="test")
    result = await noop_activity(input_data)
    assert result.message == "processed: test"
