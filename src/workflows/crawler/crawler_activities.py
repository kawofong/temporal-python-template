"""Web crawler activities for fetching URLs and parsing links."""

import re
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, HttpUrl
from temporalio import activity


class UrlContent(BaseModel):
    """Output model for fetching a URL."""

    url: str
    """The URL that was fetched."""

    html_content: str
    """The HTML content retrieved from the URL."""

    success: bool = True
    """Whether the fetch was successful."""


class ParseLinksFromUrlInput(BaseModel):
    """Input model for parsing links from a URL."""

    url: HttpUrl
    """The URL to parse links from."""


class ParseLinksFromUrlOutput(BaseModel):
    """Output model for parsing links from a URL."""

    links: list[str]
    """The links parsed from the URL."""


@activity.defn
def parse_links_from_url(input: ParseLinksFromUrlInput) -> ParseLinksFromUrlOutput:
    """Parse links from a URL."""
    content: UrlContent = fetch_url(input.url)
    return ParseLinksFromUrlOutput(links=parse_links(content.html_content, input.url))


def fetch_url(url: HttpUrl) -> UrlContent:
    """Fetch HTML content from a URL using urllib."""
    activity.logger.info("Fetching URL: %s", url)

    try:
        # Create a request with a user agent to avoid being blocked
        req = urllib.request.Request(  # noqa: S310
            str(url),
            headers={"User-Agent": "Mozilla/5.0 (compatible; TemporalCrawler/1.0)"},
        )

        with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310 # nosec
            # Read and decode the content
            content = response.read()
            html_content = content.decode("utf-8", errors="ignore")

            activity.logger.info("Successfully fetched %d bytes from %s", len(content), url)

            return UrlContent(url=str(url), html_content=html_content, success=True)

    except urllib.error.URLError as e:
        error_msg = f"Failed to fetch {url}: {e!s}"
        activity.logger.error(error_msg)

        return UrlContent(url=str(url), html_content="", success=False)


def parse_links(html_content: str, base_url: HttpUrl) -> list[str]:
    """Parse all links from HTML content."""
    activity.logger.info("Parsing links from HTML content (base URL: %s)", base_url)

    # Regular expression to find href attributes in anchor tags
    # This handles various formats: href="url", href='url', href=url
    href_pattern = re.compile(r'<a[^>]+href\s*=\s*["\']?([^"\'>\s]+)["\']?[^>]*>', re.IGNORECASE)

    # Find all href attributes
    matches = href_pattern.findall(html_content)

    # Convert relative URLs to absolute URLs and filter valid ones
    absolute_links: set[str] = set()

    for link in matches:
        # Join with base URL to handle relative links
        absolute_url = urljoin(str(base_url), link.strip())

        # Parse the URL to validate it
        parsed = urlparse(absolute_url)

        # Only include HTTP/HTTPS URLs and exclude fragment-only links
        if (
            parsed.scheme in ("http", "https")
            and parsed.netloc
            and not link.strip().startswith("#")
        ):
            absolute_links.add(absolute_url)

    links_list = list(absolute_links)
    activity.logger.info("Found %d unique links", len(links_list))
    return links_list
