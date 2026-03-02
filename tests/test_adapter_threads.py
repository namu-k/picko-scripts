"""
Tests for Threads Discovery Adapter.

Threads search is currently a placeholder because Meta App Review is required
for /keyword_search.
"""

import pytest

from picko.discovery.adapters.threads import RATE_LIMIT_PER_7_DAYS, ThreadsDiscoveryAdapter


class TestThreadsAdapterInit:
    """Tests for ThreadsDiscoveryAdapter initialization."""

    def test_init_with_credentials(self):
        """Should initialize with provided access token and api version."""
        adapter = ThreadsDiscoveryAdapter(
            access_token="test_token",
            api_version="v1.0",
        )

        assert adapter.access_token == "test_token"
        assert adapter.api_version == "v1.0"
        assert adapter.base_url == "https://graph.threads.net/v1.0"

    def test_init_from_env(self, monkeypatch):
        """Should load access token from THREADS_ACCESS_TOKEN env var."""
        monkeypatch.setenv("THREADS_ACCESS_TOKEN", "env_token")

        adapter = ThreadsDiscoveryAdapter()

        assert adapter.access_token == "env_token"

    def test_is_available_requires_both_token_and_app_review(self):
        """Should return True only when both access token and App Review approval are set."""
        # Token only - not available
        adapter_token_only = ThreadsDiscoveryAdapter(access_token="test_token")
        assert adapter_token_only.is_available() is False

        # Both token and App Review - available
        adapter_approved = ThreadsDiscoveryAdapter(
            access_token="test_token",
            app_review_approved=True,
        )
        assert adapter_approved.is_available() is True

    def test_is_available_without_token(self):
        """Should return False when access token is missing."""
        adapter = ThreadsDiscoveryAdapter(access_token="")

        assert adapter.is_available() is False

    def test_app_review_approved_from_env(self, monkeypatch):
        """Should load app_review_approved from THREADS_APP_REVIEW_APPROVED env var."""
        monkeypatch.setenv("THREADS_ACCESS_TOKEN", "test_token")
        monkeypatch.setenv("THREADS_APP_REVIEW_APPROVED", "true")

        adapter = ThreadsDiscoveryAdapter()

        assert adapter.is_available() is True

    def test_get_availability_status(self):
        """Should return detailed availability status."""
        adapter = ThreadsDiscoveryAdapter(access_token="test_token")
        status = adapter.get_availability_status()

        assert status["has_token"] is True
        assert status["app_review_approved"] is False
        assert status["available"] is False
        assert "App Review" in status["reason"]


class TestThreadsAdapterSearch:
    """Tests for Threads search behavior."""

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_not_configured(self):
        """Should return empty list when adapter is not configured."""
        adapter = ThreadsDiscoveryAdapter(access_token="")

        results = await adapter.search("ai")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_without_app_review(self):
        """Should return empty list when App Review is not approved."""
        adapter = ThreadsDiscoveryAdapter(access_token="test_token")

        results = await adapter.search("ai")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_placeholder_when_approved(self):
        """Should return empty list while /keyword_search API is not yet implemented."""
        adapter = ThreadsDiscoveryAdapter(
            access_token="test_token",
            app_review_approved=True,
        )

        results = await adapter.search("ai")

        # Still empty because actual API call is not implemented
        assert results == []


class TestThreadsAdapterRateLimit:
    """Tests for rate limit info shape."""

    def test_get_rate_limit_info_shape(self):
        """Should expose expected rate limit metadata keys and values."""
        adapter = ThreadsDiscoveryAdapter(
            access_token="test_token",
            app_review_approved=True,
        )

        info = adapter.get_rate_limit_info()

        assert info["platform"] == "threads"
        assert info["available"] is True
        assert info["has_token"] is True
        assert info["app_review_approved"] is True
        assert info["remaining"] == RATE_LIMIT_PER_7_DAYS
        assert info["limit"] == RATE_LIMIT_PER_7_DAYS
        assert info["window_days"] == 7
        assert "App Review" in info["note"]

    def test_get_rate_limit_info_without_app_review(self):
        """Should show available=False when App Review not approved."""
        adapter = ThreadsDiscoveryAdapter(access_token="test_token")

        info = adapter.get_rate_limit_info()

        assert info["available"] is False
        assert info["has_token"] is True
        assert info["app_review_approved"] is False
