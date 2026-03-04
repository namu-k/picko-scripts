"""
Tests for Mastodon Discovery Adapter.

Tests search functionality, rate limiting, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from picko.discovery.adapters.mastodon import MastodonDiscoveryAdapter


class TestMastodonAdapterInit:
    """Tests for MastodonDiscoveryAdapter initialization."""

    def test_init_with_credentials(self):
        """Should initialize with provided credentials."""
        adapter = MastodonDiscoveryAdapter(
            access_token="test_token",
            instance="mastodon.social",
        )

        assert adapter.access_token == "test_token"
        assert adapter.instance == "mastodon.social"

    def test_init_from_env(self, monkeypatch):
        """Should load credentials from environment variables."""
        monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "env_token")
        monkeypatch.setenv("MASTODON_INSTANCE", "fosstodon.org")

        adapter = MastodonDiscoveryAdapter()

        assert adapter.access_token == "env_token"
        assert adapter.instance == "fosstodon.org"

    def test_default_instance(self):
        """Should use mastodon.social as default instance."""
        adapter = MastodonDiscoveryAdapter(access_token="test")

        assert adapter.instance == "mastodon.social"

    def test_is_available_with_credentials(self):
        """Should return True when credentials are set."""
        adapter = MastodonDiscoveryAdapter(access_token="test_token")

        assert adapter.is_available() is True

    def test_is_available_without_credentials(self):
        """Should return False when credentials are missing."""
        adapter = MastodonDiscoveryAdapter(access_token="")

        assert adapter.is_available() is False


class TestMastodonAdapterSearch:
    """Tests for Mastodon search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_candidates(self):
        """Should return list of SourceCandidates."""
        adapter = MastodonDiscoveryAdapter(
            access_token="test_token",
            instance="mastodon.social",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accounts": [
                {
                    "id": "1",
                    "username": "ai_news",
                    "display_name": "AI News",
                    "url": "https://mastodon.social/@ai_news",
                    "note": "AI news and updates",
                    "followers_count": 50000,
                    "following_count": 100,
                    "bot": False,
                },
                {
                    "id": "2",
                    "username": "ml_daily",
                    "display_name": "ML Daily",
                    "url": "https://mastodon.social/@ml_daily",
                    "note": "Machine learning daily",
                    "followers_count": 25000,
                    "following_count": 50,
                    "bot": False,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("AI")

        assert len(results) == 2
        assert results[0].handle == "@ai_news@mastodon.social"
        assert results[0].platform == "mastodon"
        assert results[0].followers == 50000

    @pytest.mark.asyncio
    async def test_search_filters_bots(self):
        """Should filter out bot accounts."""
        adapter = MastodonDiscoveryAdapter(
            access_token="test_token",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accounts": [
                {
                    "id": "1",
                    "username": "human_user",
                    "display_name": "Human User",
                    "url": "https://mastodon.social/@human_user",
                    "note": "Real person",
                    "followers_count": 1000,
                    "bot": False,
                },
                {
                    "id": "2",
                    "username": "news_bot",
                    "display_name": "News Bot",
                    "url": "https://mastodon.social/@news_bot",
                    "note": "Automated news",
                    "followers_count": 10000,
                    "bot": True,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test")

        assert len(results) == 1
        assert results[0].handle == "@human_user@mastodon.social"

    @pytest.mark.asyncio
    async def test_search_handles_api_error(self):
        """Should handle API errors gracefully."""
        adapter = MastodonDiscoveryAdapter(access_token="test_token")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))
            )

            results = await adapter.search("test")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_calculates_relevance_score(self):
        """Should calculate relevance score based on followers."""
        adapter = MastodonDiscoveryAdapter(access_token="test_token")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accounts": [
                {
                    "id": "1",
                    "username": "influencer",
                    "display_name": "Big Influencer",
                    "url": "https://mastodon.social/@influencer",
                    "note": "Popular account",
                    "followers_count": 100000,
                    "bot": False,
                },
                {
                    "id": "2",
                    "username": "small_account",
                    "display_name": "Small Account",
                    "url": "https://mastodon.social/@small_account",
                    "note": "Small account",
                    "followers_count": 100,
                    "bot": False,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test")

        # Larger account should have higher relevance
        assert results[0].relevance_score > results[1].relevance_score


class TestMastodonAdapterRateLimit:
    """Tests for rate limiting."""

    def test_get_rate_limit_info(self):
        """Should return rate limit info."""
        adapter = MastodonDiscoveryAdapter(access_token="test_token")

        info = adapter.get_rate_limit_info()

        assert info["platform"] == "mastodon"
        assert "remaining" in info


class TestMastodonAdapterInstance:
    """Tests for instance handling."""

    @pytest.mark.asyncio
    async def test_custom_instance_url(self):
        """Should use custom instance URL."""
        adapter = MastodonDiscoveryAdapter(
            access_token="test_token",
            instance="fosstodon.org",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"accounts": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await adapter.search("test")

            # Check that correct URL was called
            call_args = mock_get.call_args
            assert "fosstodon.org" in str(call_args[0][0])

    def test_handle_format(self):
        """Should format handle with instance."""
        adapter = MastodonDiscoveryAdapter(
            access_token="test_token",
            instance="fosstodon.org",
        )

        # Test internal handle formatting
        handle = adapter._format_handle("user123")
        assert handle == "@user123@fosstodon.org"
