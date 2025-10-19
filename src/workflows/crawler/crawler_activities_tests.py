"""Behavior tests for web crawler activities."""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl

from src.workflows.crawler.crawler_activities import (
    ParseLinksFromUrlInput,
    ParseLinksFromUrlOutput,
    UrlContent,
    fetch_url,
    parse_links,
    parse_links_from_url,
)


class TestWebContentFetcher:
    """Behavior tests for web content fetching functionality.

    Tests describe business scenarios for retrieving web page content
    from URLs, focusing on user-facing outcomes and business value.
    """

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_web_content_fetcher_should_retrieve_page_content_when_valid_url_provided(
        self, mock_request: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        """Scenario: Retrieving web page content from a valid URL.

        Given a user provides a valid website URL
        When the system fetches the web page content
        Then it should successfully retrieve the HTML content
        """
        # Given - A valid website URL is provided
        website_url = "https://example.com"
        expected_page_content = "<html><body><h1>Welcome to Example</h1></body></html>"
        expected_content_bytes = expected_page_content.encode("utf-8")

        # Mock successful web response
        mock_response = MagicMock()
        mock_response.read.return_value = expected_content_bytes
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.return_value = mock_response

        # When - The system fetches the web page content
        result = fetch_url(website_url)

        # Then - Should successfully retrieve the HTML content
        mock_request.assert_called_once_with(
            website_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TemporalCrawler/1.0)"},
        )
        mock_urlopen.assert_called_once()
        mock_response.read.assert_called_once()

        assert isinstance(result, UrlContent)
        assert result.url == website_url
        assert result.html_content == expected_page_content
        assert result.success is True

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_web_content_fetcher_should_handle_encoding_issues_when_page_has_invalid_characters(
        self,
        mock_request: MagicMock,  # noqa: ARG002
        mock_urlopen: MagicMock,
    ) -> None:
        """Scenario: Handling web pages with encoding issues.

        Given a web page contains characters with encoding problems
        When the system fetches the page content
        Then it should gracefully handle the encoding issues and return readable content
        """
        # Given - A web page with encoding issues
        website_url = "https://example.com"
        content_with_encoding_issues = (
            b"\xff\xfe<html><body>Content with encoding issues</body></html>"
        )

        # Mock response with encoding issues
        mock_response = MagicMock()
        mock_response.read.return_value = content_with_encoding_issues
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.return_value = mock_response

        # When - The system fetches the page content
        result = fetch_url(website_url)

        # Then - Should gracefully handle encoding issues and return readable content
        assert isinstance(result, UrlContent)
        assert result.url == website_url
        assert result.success is True
        # Content should be decoded with errors ignored, making it readable
        assert "<html><body>Content with encoding issues</body></html>" in result.html_content

    @pytest.mark.parametrize(
        ("business_scenario", "exception_class", "business_context"),
        [
            (
                "website_unavailable",
                urllib.error.URLError,
                "Website server is down or unreachable",
            ),
        ],
    )
    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_web_content_fetcher_should_handle_website_unavailable_when_connection_fails(
        self,
        mock_request: MagicMock,  # noqa: ARG002
        mock_urlopen: MagicMock,
        business_scenario: str,  # noqa: ARG002
        exception_class: type[Exception],
        business_context: str,  # noqa: ARG002
    ) -> None:
        """Scenario: Handling website unavailability.

        Given a user requests content from a website
        When the website is unavailable or connection fails
        Then the system should gracefully handle the failure and indicate unsuccessful retrieval
        """
        # Given - A user requests content from a website
        website_url = "https://unavailable-website.com"

        # Mock connection failure
        mock_urlopen.side_effect = exception_class("Website unavailable")

        # When - The website is unavailable or connection fails
        result = fetch_url(website_url)

        # Then - Should gracefully handle failure and indicate unsuccessful retrieval
        assert isinstance(result, UrlContent)
        assert result.url == website_url
        assert result.html_content == ""
        assert result.success is False


class TestLinkExtractor:
    """Behavior tests for link extraction from web pages.

    Tests describe business scenarios for discovering and extracting
    hyperlinks from web page content for crawling purposes.
    """

    def test_link_extractor_should_discover_all_links_when_page_contains_standard_hyperlinks(
        self,
    ) -> None:
        """Scenario: Discovering links from a standard web page.

        Given a web page contains standard hyperlinks
        When the system extracts links from the page
        Then it should discover all valid hyperlinks including relative paths
        """
        # Given - A web page contains standard hyperlinks
        web_page_content = """
        <html>
        <body>
            <a href="https://example.com/products">Products</a>
            <a href="https://example.com/about">About Us</a>
            <a href="/contact">Contact</a>
        </body>
        </html>
        """
        base_website_url = "https://example.com"

        # When - The system extracts links from the page
        discovered_links = parse_links(web_page_content, base_website_url)

        # Then - Should discover all valid hyperlinks including relative paths
        expected_business_links = [
            "https://example.com/products",
            "https://example.com/about",
            "https://example.com/contact",
        ]
        expected_link_count = 3

        assert len(discovered_links) == expected_link_count
        for business_link in expected_business_links:
            assert business_link in discovered_links

    def test_link_extractor_should_handle_various_link_formats_when_page_uses_different_html_styles(
        self,
    ) -> None:
        """Scenario: Handling different HTML link formats.

        Given a web page uses various HTML link formatting styles
        When the system extracts links from the page
        Then it should successfully parse all link formats regardless of quote style
        """
        # Given - A web page uses various HTML link formatting styles
        web_page_content = """
        <html>
        <body>
            <a href="https://example.com/style1">Double Quotes</a>
            <a href='https://example.com/style2'>Single Quotes</a>
            <a href=https://example.com/style3>No Quotes</a>
            <a class="nav-link" href="https://example.com/style4">With CSS Class</a>
        </body>
        </html>
        """
        base_website_url = "https://example.com"

        # When - The system extracts links from the page
        discovered_links = parse_links(web_page_content, base_website_url)

        # Then - Should successfully parse all link formats regardless of quote style
        expected_business_links = [
            "https://example.com/style1",
            "https://example.com/style2",
            "https://example.com/style3",
            "https://example.com/style4",
        ]
        expected_link_count = 4

        assert len(discovered_links) == expected_link_count
        for business_link in expected_business_links:
            assert business_link in discovered_links

    def test_link_extractor_should_filter_non_web_links_when_page_contains_mixed_link_types(
        self,
    ) -> None:
        """Scenario: Filtering out non-web links from mixed content.

        Given a web page contains various types of links including non-web links
        When the system extracts links for web crawling
        Then it should only include valid web links and exclude email, javascript,
        and other non-web links
        """
        # Given - A web page contains various types of links including non-web links
        web_page_content = """
        <html>
        <body>
            <a href="https://example.com/valid">Valid Web Link</a>
            <a href="#section1">Page Fragment</a>
            <a href="javascript:void(0)">JavaScript Action</a>
            <a href="mailto:contact@example.com">Email Link</a>
            <a href="ftp://files.example.com/download">FTP Link</a>
            <a href="">Empty Link</a>
        </body>
        </html>
        """
        base_website_url = "https://example.com"

        # When - The system extracts links for web crawling
        discovered_links = parse_links(web_page_content, base_website_url)

        # Then - Should only include valid web links and exclude non-web links
        expected_valid_count = 1
        assert len(discovered_links) == expected_valid_count
        assert "https://example.com/valid" in discovered_links

    def test_link_extractor_should_convert_relative_paths_when_page_uses_relative_navigation(
        self,
    ) -> None:
        """Scenario: Converting relative paths to absolute URLs.

        Given a web page uses relative paths for navigation
        When the system extracts links for crawling other sites
        Then it should convert all relative paths to absolute URLs based on the
        current page location
        """
        # Given - A web page uses relative paths for navigation
        web_page_content = """
        <html>
        <body>
            <a href="/services">Services (Root Relative)</a>
            <a href="products/catalog">Products (Relative)</a>
            <a href="../company/history">Company History (Parent)</a>
            <a href="./team/members">Team Members (Current)</a>
        </body>
        </html>
        """
        current_page_location = "https://example.com/current/page"

        # When - The system extracts links for crawling other sites
        discovered_links = parse_links(web_page_content, current_page_location)

        # Then - Should convert all relative paths to absolute URLs
        expected_absolute_urls = [
            "https://example.com/services",
            "https://example.com/current/products/catalog",
            "https://example.com/company/history",
            "https://example.com/current/team/members",
        ]
        expected_link_count = 4

        assert len(discovered_links) == expected_link_count
        for absolute_url in expected_absolute_urls:
            assert absolute_url in discovered_links

    def test_link_extractor_should_remove_duplicate_links_when_page_has_repeated_navigation(
        self,
    ) -> None:
        """Scenario: Handling duplicate links in navigation.

        Given a web page has duplicate links in different navigation sections
        When the system extracts links for efficient crawling
        Then it should remove duplicates and return only unique links
        """
        # Given - A web page has duplicate links in different navigation sections
        web_page_content = """
        <html>
        <body>
            <nav>
                <a href="https://example.com/products">Products (Header)</a>
                <a href="https://example.com/products">Products (Duplicate)</a>
                <a href="/products">Products (Relative)</a>
            </nav>
        </body>
        </html>
        """
        base_website_url = "https://example.com"

        # When - The system extracts links for efficient crawling
        discovered_links = parse_links(web_page_content, base_website_url)

        # Then - Should remove duplicates and return only unique links
        expected_unique_count = 1
        assert len(discovered_links) == expected_unique_count
        assert "https://example.com/products" in discovered_links

    def test_link_extractor_should_handle_empty_content_when_page_has_no_links(
        self,
    ) -> None:
        """Scenario: Handling pages without any links.

        Given a web page contains no hyperlinks
        When the system attempts to extract links
        Then it should return an empty result without errors
        """
        # Given - A web page contains no hyperlinks
        empty_page_content = ""
        base_website_url = "https://example.com"

        # When - The system attempts to extract links
        discovered_links = parse_links(empty_page_content, base_website_url)

        # Then - Should return an empty result without errors
        expected_empty_count = 0
        assert len(discovered_links) == expected_empty_count
        assert discovered_links == []

    def test_link_extractor_should_handle_content_without_links_when_page_has_only_text(
        self,
    ) -> None:
        """Scenario: Handling text-only pages.

        Given a web page contains only text content without any links
        When the system searches for links to crawl
        Then it should return no links without causing errors
        """
        # Given - A web page contains only text content without any links
        text_only_content = """
        <html>
        <body>
            <h1>Welcome to Our Site</h1>
            <p>This page contains only informational text.</p>
        </body>
        </html>
        """
        base_website_url = "https://example.com"

        # When - The system searches for links to crawl
        discovered_links = parse_links(text_only_content, base_website_url)

        # Then - Should return no links without causing errors
        expected_empty_count = 0
        assert len(discovered_links) == expected_empty_count
        assert discovered_links == []


class TestWebPageLinkDiscovery:
    """Behavior tests for complete web page link discovery process.

    Tests describe end-to-end business scenarios for discovering links
    from web pages, combining content fetching and link extraction.
    """

    def test_web_page_link_discovery_should_find_all_links_when_page_loads_successfully(
        self,
    ) -> None:
        """Scenario: Discovering links from a successfully loaded web page.

        Given a user wants to discover links from a specific web page
        When the system loads the page and extracts its links
        Then it should return all discoverable links from that page
        """
        # Given - A user wants to discover links from a specific web page
        target_website = "https://example.com"
        page_with_links = """
        <html>
        <body>
            <a href="https://example.com/products">Our Products</a>
            <a href="https://example.com/services">Our Services</a>
        </body>
        </html>
        """

        with patch("src.workflows.crawler.crawler_activities.fetch_url") as mock_fetch:
            # Mock successful page loading
            mock_fetch.return_value = UrlContent(
                url=target_website, html_content=page_with_links, success=True
            )

            # When - The system loads the page and extracts its links
            discovery_request = ParseLinksFromUrlInput(url=target_website)
            result = parse_links_from_url(discovery_request)

            # Then - Should return all discoverable links from that page
            mock_fetch.assert_called_once_with(HttpUrl(target_website))

            assert isinstance(result, ParseLinksFromUrlOutput)
            expected_link_count = 2
            assert len(result.links) == expected_link_count
            assert "https://example.com/products" in result.links
            assert "https://example.com/services" in result.links

    def test_web_page_link_discovery_should_return_empty_results_when_page_fails_to_load(
        self,
    ) -> None:
        """Scenario: Handling failed page loading during link discovery.

        Given a user requests link discovery from a web page
        When the page fails to load due to network or server issues
        Then the system should return empty results gracefully without crashing
        """
        # Given - A user requests link discovery from a web page
        problematic_website = "https://broken-website.com"

        with patch("src.workflows.crawler.crawler_activities.fetch_url") as mock_fetch:
            # Mock failed page loading
            mock_fetch.return_value = UrlContent(
                url=problematic_website, html_content="", success=False
            )

            # When - The page fails to load due to network or server issues
            discovery_request = ParseLinksFromUrlInput(url=problematic_website)
            result = parse_links_from_url(discovery_request)

            # Then - Should return empty results gracefully without crashing
            mock_fetch.assert_called_once_with(HttpUrl(problematic_website))

            assert isinstance(result, ParseLinksFromUrlOutput)
            expected_empty_count = 0
            assert len(result.links) == expected_empty_count
            assert result.links == []

    def test_web_page_link_discovery_should_handle_malformed_content_when_page_has_broken_html(
        self,
    ) -> None:
        """Scenario: Handling malformed HTML during link discovery.

        Given a web page contains malformed or broken HTML
        When the system attempts to discover links from the page
        Then it should handle the malformed content gracefully and extract what links it can
        """
        # Given - A web page contains malformed or broken HTML
        target_website = "https://example.com"
        broken_html_content = "<html><body><a href='incomplete-link"  # Intentionally malformed

        with patch("src.workflows.crawler.crawler_activities.fetch_url") as mock_fetch:
            # Mock page with broken HTML
            mock_fetch.return_value = UrlContent(
                url=target_website, html_content=broken_html_content, success=True
            )

            # When - The system attempts to discover links from the page
            discovery_request = ParseLinksFromUrlInput(url=target_website)
            result = parse_links_from_url(discovery_request)

            # Then - Should handle malformed content gracefully and extract what links it can
            assert isinstance(result, ParseLinksFromUrlOutput)
            # Should handle malformed HTML without crashing, even if no valid links found
            expected_empty_count = 0
            assert len(result.links) == expected_empty_count  # No valid links in malformed HTML


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
