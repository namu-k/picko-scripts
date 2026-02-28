"""
Tests for Reddit Discovery Adapter.

Tests search functionality, rate limiting, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from picko.discovery.adapters.reddit import RedditDiscoveryAdapter


class TestRedditAdapterInit:
    """Tests for RedditDiscoveryAdapter initialization."""

    def test_init_with_credentials(self):
        """Should initialize with provided credentials."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
            user_agent="test_agent",
        )

        assert adapter.client_id == "test_id"
        assert adapter.client_secret == "test_secret"
        assert adapter.user_agent == "test_agent"

    def test_init_from_env(self, monkeypatch):
        """Should load credentials from environment variables."""
        monkeypatch.setenv("REDDIT_CLIENT_ID", "env_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "env_secret")

        adapter = RedditDiscoveryAdapter()

        assert adapter.client_id == "env_id"
        assert adapter.client_secret == "env_secret"

    def test_is_available_with_credentials(self):
        """Should return True when credentials are set."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        assert adapter.is_available() is True

    def test_is_available_without_credentials(self):
        """Should return False when credentials are missing."""
        adapter = RedditDiscoveryAdapter(
            client_id="",
            client_secret="",
        )

        assert adapter.is_available() is False


class TestRedditAdapterSearch:
    """Tests for Reddit search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_candidates(self):
        """Should return list of SourceCandidates."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        # Mock the access token request
        with patch.object(adapter, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"

            # Mock the search response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {
                    "children": [
                        {
                            "data": {
                                "display_name": "MachineLearning",
                                "url": "/r/MachineLearning",
                                "public_description": "ML community",
                                "subscribers": 3000000,
                                "over18": False,
                            }
                        },
                        {
                            "data": {
                                "display_name": "artificial",
                                "url": "/r/artificial",
                                "public_description": "AI discussion",
                                "subscribers": 500000,
                                "over18": False,
                            }
                        },
                    ]
                }
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                results = await adapter.search("machine learning")

        assert len(results) == 2
        assert results[0].handle == "r/MachineLearning"
        assert results[0].platform == "reddit"
        assert results[0].followers == 3000000

    @pytest.mark.asyncio
    async def test_search_filters_nsfw(self):
        """Should filter out NSFW subreddits."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        with patch.object(adapter, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {
                    "children": [
                        {
                            "data": {
                                "display_name": "SafeSubreddit",
                                "url": "/r/SafeSubreddit",
                                "public_description": "Safe content",
                                "subscribers": 1000,
                                "over18": False,
                            }
                        },
                        {
                            "data": {
                                "display_name": "NSFWSubreddit",
                                "url": "/r/NSFWSubreddit",
                                "public_description": "Adult content",
                                "subscribers": 5000,
                                "over18": True,
                            }
                        },
                    ]
                }
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                results = await adapter.search("test")

        assert len(results) == 1
        assert results[0].handle == "r/SafeSubreddit"

    @pytest.mark.asyncio
    async def test_search_handles_api_error(self):
        """Should handle API errors gracefully."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        with patch.object(adapter, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "Error",
                        request=MagicMock(),
                        response=MagicMock(status_code=500),
                    )
                )

                results = await adapter.search("test")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_calculates_relevance_score(self):
        """Should calculate relevance score based on subscribers."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        with patch.object(adapter, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {
                    "children": [
                        {
                            "data": {
                                "display_name": "HugeSub",
                                "url": "/r/HugeSub",
                                "public_description": "Huge community",
                                "subscribers": 10000000,  # 10M
                                "over18": False,
                            }
                        },
                        {
                            "data": {
                                "display_name": "SmallSub",
                                "url": "/r/SmallSub",
                                "public_description": "Small community",
                                "subscribers": 1000,  # 1K
                                "over18": False,
                            }
                        },
                    ]
                }
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                results = await adapter.search("test")

        # Larger subreddit should have higher relevance
        assert results[0].relevance_score > results[1].relevance_score


class TestRedditAdapterRateLimit:
    """Tests for rate limiting."""

    def test_get_rate_limit_info(self):
        """Should return rate limit info."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        info = adapter.get_rate_limit_info()

        assert info["platform"] == "reddit"
        assert "remaining" in info


class TestRedditAdapterAuthentication:
    """Tests for OAuth authentication."""

    @pytest.mark.asyncio
    async def test_get_access_token_success(self):
        """Should obtain access token from Reddit OAuth."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = await adapter._get_access_token()

        assert token == "test_token_123"

    @pytest.mark.asyncio
    async def test_get_access_token_caches_token(self):
        """Should cache access token until expiry."""
        adapter = RedditDiscoveryAdapter(
            client_id="test_id",
            client_secret="test_secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "cached_token",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            # First call
            token1 = await adapter._get_access_token()
            # Second call
            token2 = await adapter._get_access_token()

        assert token1 == token2
        # Should only call API once due to caching
        assert mock_post.call_count == 1
