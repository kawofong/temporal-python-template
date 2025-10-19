"""Behavior tests for web crawler workflow."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from src.workflows.crawler.crawler_activities import (
    ParseLinksFromUrlInput,
    ParseLinksFromUrlOutput,
)
from src.workflows.crawler.crawler_workflow import (
    CrawlerWorkflow,
    CrawlerWorkflowInput,
    CrawlerWorkflowOutput,
)

# Constants to avoid magic numbers
MAX_CRAWL_LIMIT = 5
SINGLE_PAGE_LIMIT = 1
EXPECTED_INITIAL_LINKS = 2
EXPECTED_MULTIPLE_DOMAINS = 3
MODERATE_CRAWL_LIMIT = 3
CROSS_DOMAIN_LIMIT = 2
LARGE_SCALE_LIMIT = 100
MAX_DISCOVERY_CALLS = 3


class TestWebCrawlerWorkflow:
    """Behavior tests for web crawler workflow.

    Tests describe complete business processes for automated web crawling,
    focusing on user scenarios and business value of discovering web content.
    """

    @pytest.fixture
    def task_queue(self) -> str:
        """Generate unique task queue name for each test."""
        return f"test-web-crawler-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_web_crawler_should_discover_multiple_pages_when_crawling_interconnected_website(
        self, client: Client, task_queue: str
    ) -> None:
        """Scenario: Crawling an interconnected website to discover multiple pages.

        Given a user wants to discover content from an interconnected website
        When the crawler explores the website up to a specified limit
        Then it should discover links from multiple pages and various domains
        """

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,
        ) -> ParseLinksFromUrlOutput:
            """Mocked link discovery activity for business scenario testing."""
            activity.logger.info("Business scenario: discovering links from %s", input_data.url)

            # Simulate realistic business website structure
            # Note: Pydantic HttpUrl may add trailing slash
            url_str = str(input_data.url).rstrip("/")
            if url_str == "https://business-site.com":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://business-site.com/products",
                        "https://business-site.com/services",
                        "https://partner-site.com/collaboration",
                    ]
                )
            if url_str == "https://business-site.com/products":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://business-site.com/product-catalog",
                        "https://business-site.com/pricing",
                    ]
                )
            if url_str == "https://business-site.com/services":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://business-site.com/consulting",
                        "https://external-partner.com/integration",
                    ]
                )
            # Other pages have no outbound links
            return ParseLinksFromUrlOutput(links=[])

        # Given - A user wants to discover content from an interconnected website
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            crawling_request = CrawlerWorkflowInput(
                start_url="https://business-site.com",
                max_links=MAX_CRAWL_LIMIT,
            )

            # When - The crawler explores the website up to a specified limit
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                crawling_request,
                id=f"test-interconnected-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should discover links from multiple pages and various domains
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Should respect the crawling limit
            assert crawling_result.total_links_crawled <= MAX_CRAWL_LIMIT
            assert (
                crawling_result.total_links_crawled >= SINGLE_PAGE_LIMIT
            )  # Should crawl at least the starting page

            # Should discover the initial business pages
            expected_business_pages = {
                "https://business-site.com/products",
                "https://business-site.com/services",
                "https://partner-site.com/collaboration",
            }
            discovered_pages = set(crawling_result.links_discovered)
            assert expected_business_pages.issubset(discovered_pages)

            # Should identify multiple business domains
            expected_business_domains = {"business-site.com", "partner-site.com"}
            discovered_domains = set(crawling_result.domains_discovered)
            assert expected_business_domains.issubset(discovered_domains)

    @pytest.mark.asyncio
    async def test_web_crawler_should_respect_crawling_limits_when_user_sets_small_boundary(
        self, client: Client, task_queue: str
    ) -> None:
        """Scenario: Respecting user-defined crawling limits for focused discovery.

        Given a user wants to perform limited web discovery to avoid overwhelming the system
        When the crawler is configured with a small crawling limit
        Then it should discover content only from the specified number of pages
        """

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,
        ) -> ParseLinksFromUrlOutput:
            """Mocked activity for limited crawling scenario."""
            url_str = str(input_data.url).rstrip("/")
            if url_str == "https://company-site.com":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://company-site.com/about",
                        "https://company-site.com/contact",
                    ]
                )
            return ParseLinksFromUrlOutput(links=[])

        # Given - A user wants to perform limited web discovery
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            limited_crawling_request = CrawlerWorkflowInput(
                start_url="https://company-site.com",
                max_links=SINGLE_PAGE_LIMIT,  # Very limited crawling
            )

            # When - The crawler is configured with a small crawling limit
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                limited_crawling_request,
                id=f"test-limited-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should discover content only from the specified number of pages
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Only crawled the starting page
            assert crawling_result.total_links_crawled == SINGLE_PAGE_LIMIT
            assert (
                len(crawling_result.links_discovered) == EXPECTED_INITIAL_LINKS
            )  # Should discover links from that one page
            assert "https://company-site.com/about" in crawling_result.links_discovered
            assert "https://company-site.com/contact" in crawling_result.links_discovered
            assert "company-site.com" in crawling_result.domains_discovered

    @pytest.mark.asyncio
    async def test_web_crawler_should_handle_empty_websites_when_pages_contain_no_links(
        self, client: Client, task_queue: str
    ) -> None:
        """Scenario: Handling websites with no outbound links.

        Given a user attempts to crawl a website that has no outbound links
        When the crawler explores the site looking for additional content
        Then it should complete gracefully without discovering additional pages
        """

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,
        ) -> ParseLinksFromUrlOutput:
            """Mocked activity for empty website scenario."""
            activity.logger.info(
                "Business scenario: exploring site with no links at %s", input_data.url
            )
            return ParseLinksFromUrlOutput(links=[])

        # Given - A user attempts to crawl a website that has no outbound links
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            empty_site_request = CrawlerWorkflowInput(
                start_url="https://simple-landing-page.com",
                max_links=10,
            )

            # When - The crawler explores the site looking for additional content
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                empty_site_request,
                id=f"test-empty-site-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should complete gracefully without discovering additional pages
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Only the starting page
            assert crawling_result.total_links_crawled == SINGLE_PAGE_LIMIT
            expected_empty_count = 0
            # No additional pages found
            assert len(crawling_result.links_discovered) == expected_empty_count
            # No additional domains found
            assert len(crawling_result.domains_discovered) == expected_empty_count

    @pytest.mark.asyncio
    async def test_web_crawler_should_eliminate_duplicates_when_sites_have_circular_references(
        self,
        client: Client,
        task_queue: str,
    ) -> None:
        """Scenario: Handling websites with circular link references.

        Given a website has pages that link back to each other creating circular references
        When the crawler explores the site to avoid infinite loops
        Then it should eliminate duplicate discoveries and provide unique results
        """

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,
        ) -> ParseLinksFromUrlOutput:
            """Mocked activity for circular reference scenario."""
            url_str = str(input_data.url).rstrip("/")
            if url_str == "https://circular-site.com":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://circular-site.com/page1",
                        "https://circular-site.com/page1",  # Duplicate link
                        "https://circular-site.com/page2",
                    ]
                )
            if url_str == "https://circular-site.com/page1":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://circular-site.com/page2",  # Already discovered
                        "https://circular-site.com/page3",  # New discovery
                    ]
                )
            return ParseLinksFromUrlOutput(links=[])

        # Given - A website has pages that link back to each other
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            circular_site_request = CrawlerWorkflowInput(
                start_url="https://circular-site.com",
                max_links=MODERATE_CRAWL_LIMIT,
            )

            # When - The crawler explores the site to avoid infinite loops
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                circular_site_request,
                id=f"test-circular-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should eliminate duplicates and provide unique results
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Should respect limit
            assert crawling_result.total_links_crawled <= MODERATE_CRAWL_LIMIT
            # Should crawl at least starting page
            assert crawling_result.total_links_crawled >= SINGLE_PAGE_LIMIT

            # Should have unique links only (no duplicates)
            unique_discoveries = set(crawling_result.links_discovered)
            assert len(unique_discoveries) == len(crawling_result.links_discovered)

            # Should discover the expected unique pages
            expected_unique_pages = {
                "https://circular-site.com/page1",
                "https://circular-site.com/page2",
            }
            discovered_pages = set(crawling_result.links_discovered)
            assert expected_unique_pages.issubset(discovered_pages)

    @pytest.mark.asyncio
    async def test_web_crawler_should_discover_cross_domain_content_when_sites_reference_partners(
        self,
        client: Client,
        task_queue: str,
    ) -> None:
        """Scenario: Discovering content across multiple business domains.

        Given a business website references external partner sites and resources
        When the crawler explores to understand the business ecosystem
        Then it should discover and catalog content from multiple related domains
        """

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,
        ) -> ParseLinksFromUrlOutput:
            """Mocked activity for cross-domain discovery scenario."""
            url_str = str(input_data.url).rstrip("/")
            if url_str == "https://main-business.com":
                return ParseLinksFromUrlOutput(
                    links=[
                        "https://partner-network.org/directory",
                        "https://industry-resources.net/tools",
                        "https://certification-body.edu/standards",
                    ]
                )
            return ParseLinksFromUrlOutput(links=[])

        # Given - A business website references external partner sites
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            cross_domain_request = CrawlerWorkflowInput(
                start_url="https://main-business.com",
                max_links=CROSS_DOMAIN_LIMIT,
            )

            # When - The crawler explores to understand the business ecosystem
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                cross_domain_request,
                id=f"test-cross-domain-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should discover and catalog content from multiple related domains
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Crawled main site + one more
            assert crawling_result.total_links_crawled == CROSS_DOMAIN_LIMIT
            # All external links discovered
            assert len(crawling_result.links_discovered) == EXPECTED_MULTIPLE_DOMAINS

            # Should discover the expected external business resources
            expected_external_resources = {
                "https://partner-network.org/directory",
                "https://industry-resources.net/tools",
                "https://certification-body.edu/standards",
            }
            discovered_resources = set(crawling_result.links_discovered)
            assert discovered_resources == expected_external_resources

            # Should identify multiple business domains in the ecosystem
            expected_business_domains = {
                "partner-network.org",
                "industry-resources.net",
                "certification-body.edu",
            }
            discovered_domains = set(crawling_result.domains_discovered)
            assert discovered_domains == expected_business_domains

    @pytest.mark.asyncio
    async def test_web_crawler_should_handle_large_requests_when_user_needs_comprehensive_analysis(
        self,
        client: Client,
        task_queue: str,
    ) -> None:
        """Scenario: Handling large-scale web discovery for comprehensive business analysis.

        Given a user needs comprehensive analysis of a large business website ecosystem
        When the crawler is configured for extensive discovery within reasonable limits
        Then it should efficiently discover content while respecting system boundaries
        """
        discovery_call_count = 0

        @activity.defn
        def parse_links_from_url(
            input_data: ParseLinksFromUrlInput,  # noqa: ARG001
        ) -> ParseLinksFromUrlOutput:
            """Mocked activity for large-scale discovery scenario."""
            nonlocal discovery_call_count
            discovery_call_count += 1

            # Simulate discovering content from multiple business sections
            if discovery_call_count <= MAX_DISCOVERY_CALLS:
                return ParseLinksFromUrlOutput(
                    links=[
                        f"https://enterprise-site.com/section{discovery_call_count}-{i}"
                        for i in range(EXPECTED_INITIAL_LINKS)
                    ]
                )
            return ParseLinksFromUrlOutput(links=[])

        # Given - A user needs comprehensive analysis of a large business website
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CrawlerWorkflow],
            activities=[parse_links_from_url],
            activity_executor=ThreadPoolExecutor(MAX_CRAWL_LIMIT),
        ):
            comprehensive_request = CrawlerWorkflowInput(
                start_url="https://enterprise-site.com",
                max_links=LARGE_SCALE_LIMIT,  # Large-scale discovery request
            )

            # When - The crawler is configured for extensive discovery
            crawling_result = await client.execute_workflow(
                CrawlerWorkflow.run,
                comprehensive_request,
                id=f"test-comprehensive-crawl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Then - Should efficiently discover content while respecting boundaries
            assert isinstance(crawling_result, CrawlerWorkflowOutput)
            # Should complete when no more content is available, not necessarily at max limit
            assert crawling_result.total_links_crawled <= LARGE_SCALE_LIMIT
            expected_minimum_discoveries = 0
            assert len(crawling_result.links_discovered) > expected_minimum_discoveries
            assert "enterprise-site.com" in crawling_result.domains_discovered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
