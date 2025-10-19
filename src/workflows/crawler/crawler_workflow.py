"""Web crawler workflow for recursively crawling URLs."""

import asyncio
from datetime import timedelta
from urllib.parse import urlparse

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, HttpUrl

    from src.workflows.crawler.crawler_activities import (
        ParseLinksFromUrlInput,
        ParseLinksFromUrlOutput,
        parse_links_from_url,
    )


class CrawlerWorkflowInput(BaseModel):
    """Input model for the web crawler workflow."""

    start_url: HttpUrl
    """The starting URL to begin crawling from."""

    max_links: int = 10
    """Maximum number of links to crawl (default: 10)."""


class CrawlerWorkflowOutput(BaseModel):
    """Output model for the web crawler workflow."""

    total_links_crawled: int
    """Total number of links successfully crawled."""

    links_discovered: list[str]
    """List of unique links discovered."""

    domains_discovered: list[str]
    """List of unique domains discovered."""


@workflow.defn
class CrawlerWorkflow:
    """A workflow that recursively crawls web pages up to a specified limit."""

    @workflow.run
    async def run(self, input: CrawlerWorkflowInput) -> CrawlerWorkflowOutput:
        """Run the web crawler workflow."""
        workflow.logger.info(
            "Starting web crawler from %s (max links: %d)",
            input.start_url,
            input.max_links,
        )

        discovered_links: set[str] = set()
        discovered_domains: set[str] = set()
        links_to_crawl: list[str] = [str(input.start_url)]
        total_links_crawled: int = 0

        # Crawl links until we reach the max links or run out of links to crawl
        while links_to_crawl and total_links_crawled < input.max_links:
            remaining_links_to_crawl_count = input.max_links - total_links_crawled
            current_links_to_crawl = links_to_crawl[:remaining_links_to_crawl_count]
            results: list[ParseLinksFromUrlOutput] = await asyncio.gather(
                *[
                    workflow.execute_activity(
                        parse_links_from_url,
                        ParseLinksFromUrlInput(url=link),
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    for link in current_links_to_crawl
                ]
            )

            for parsed_links in results:
                for link in parsed_links.links:
                    if link not in discovered_links:
                        discovered_links.add(link)
                        links_to_crawl.append(link)
                        discovered_domains.add(urlparse(link).netloc)

            # Increment the total number of links crawled
            total_links_crawled += len(current_links_to_crawl)
            # Remove the links that have been crawled from the list of links to crawl
            links_to_crawl = links_to_crawl[remaining_links_to_crawl_count:]

        return CrawlerWorkflowOutput(
            total_links_crawled=total_links_crawled,
            links_discovered=sorted(discovered_links),
            domains_discovered=sorted(discovered_domains),
        )


async def main() -> None:  # pragma: no cover
    """Connects to the client and executes the crawler workflow."""
    import uuid  # noqa: PLC0415

    from temporalio.client import Client  # noqa: PLC0415
    from temporalio.contrib.pydantic import pydantic_data_converter  # noqa: PLC0415

    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)

    # Example crawl starting from a test site
    input_data = CrawlerWorkflowInput(
        start_url="https://httpbin.org/links/50",  # A page with 50 links for testing
        max_links=10,
    )

    result = await client.execute_workflow(
        CrawlerWorkflow.run,
        input_data,
        id=f"crawler-{uuid.uuid4()}",
        task_queue="crawler-task-queue",
    )

    print(f"Crawler Workflow Result: {result}")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
