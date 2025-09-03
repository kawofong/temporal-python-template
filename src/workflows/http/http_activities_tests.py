"""Tests for HTTP activities."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from temporalio.testing import ActivityEnvironment

from src.workflows.http.http_activities import HttpGetActivityInput, http_get


class TestHttpGetActivity:
    """Test suite for the http_get activity.

    Tests cover successful HTTP requests, various error scenarios,
    and edge cases using ActivityEnvironment for isolation.
    """

    @pytest.mark.asyncio
    async def test_http_get_success(self) -> None:
        """Test successful HTTP GET request."""
        # Test data
        expected_response_text = '{"id": 1, "title": "Test Post", "userId": 1}'
        expected_status_code = 200
        test_url = "https://api.example.com/posts/1"

        # Create mock response that supports async context manager
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=expected_response_text)
        mock_response.status = expected_status_code
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create mock session that supports async context manager
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock the ClientSession constructor
        with patch("aiohttp.ClientSession", return_value=mock_session) as mock_client_session:
            # Execute the activity
            activity_environment = ActivityEnvironment()
            input_data = HttpGetActivityInput(url=test_url)
            result = await activity_environment.run(http_get, input_data)

            # Verify mocks were called correctly
            mock_client_session.assert_called_once()
            mock_session.get.assert_called_once_with(test_url)
            mock_response.text.assert_called_once()

            # Verify the result
            assert result is not None
            assert result.response_text == expected_response_text
            assert result.status_code == expected_status_code

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "not-a-valid-url",
            "",
            "https://",
        ],
    )
    @pytest.mark.asyncio
    async def test_http_get_invalid_url(self, invalid_url: str) -> None:
        """Test HTTP GET request with invalid URL format."""
        activity_environment = ActivityEnvironment()
        input_data = HttpGetActivityInput(url=invalid_url)

        with pytest.raises(aiohttp.client_exceptions.InvalidUrlClientError) as exc_info:
            await activity_environment.run(http_get, input_data)
        # Should raise an exception for invalid URL
        assert exc_info.value is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
