"""HTTP activities for making external API calls."""

import aiohttp
from temporalio import activity


@activity.defn
async def http_get(url: str) -> str:
    """A basic activity that makes an HTTP GET call."""
    activity.logger.info("Activity: making HTTP GET call to %s", url)
    async with aiohttp.ClientSession() as session, session.get(url) as response:
        return await response.text()
