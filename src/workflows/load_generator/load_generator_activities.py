"""Activities for the load generator workflow."""

from pydantic import BaseModel
from temporalio import activity


class NoopActivityInput(BaseModel):
    """Input for the noop activity."""

    message: str = "ping"


class NoopActivityOutput(BaseModel):
    """Output for the noop activity."""

    message: str = "pong"


@activity.defn
async def noop_activity(input: NoopActivityInput) -> NoopActivityOutput:
    """A simple no-op activity that just returns a value."""
    return NoopActivityOutput(message=f"processed: {input.message}")
