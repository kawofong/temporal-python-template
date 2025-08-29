"""HTTP activities for making external API calls."""

import aiohttp
from pydantic import BaseModel
from temporalio import activity


class HttpGetActivityInput(BaseModel):
    """Input model for HTTP workflow."""

    url: str
    """The URL to make the HTTP GET request to."""


class HttpGetActivityOutput(BaseModel):
    """Output model for HTTP workflow."""

    response_text: str
    """The response text from the HTTP GET request."""

    status_code: int = 200
    """The HTTP status code of the response."""


@activity.defn
async def http_get(input: HttpGetActivityInput) -> HttpGetActivityOutput:
    """A basic activity that makes an HTTP GET call."""
    activity.logger.info("Activity: making HTTP GET call to %s", input.url)
    async with (
        aiohttp.ClientSession() as session,
        session.get(str(input.url)) as response,
    ):
        response_text = await response.text()
        return HttpGetActivityOutput(
            response_text=response_text,
            status_code=response.status,
        )
