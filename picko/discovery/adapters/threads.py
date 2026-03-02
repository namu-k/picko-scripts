"""
Threads Discovery Adapter.

Implements source discovery via Meta's Threads API.

IMPORTANT: This adapter requires Meta App Review approval for /keyword_search endpoint.
Without App Review approval, the adapter will return empty results even with valid credentials.

To enable:
1. Submit your app for Meta App Review
2. Request 'threads_basic' and 'threads_content_publish' permissions
3. Set THREADS_APP_REVIEW_APPROVED=true in environment after approval
"""

import os
from typing import Any

from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate
from picko.logger import get_logger

logger = get_logger("discovery.adapters.threads")

# Rate limits: 500 queries/7 days for /keyword_search
RATE_LIMIT_PER_7_DAYS = 500


class ThreadsDiscoveryAdapter(BaseDiscoveryCollector):
    """
    Threads API adapter for source discovery.

    Uses Meta's Threads API to search for accounts.
    Rate limit: 500 queries/7 days

    IMPORTANT: Requires Meta App Review approval for /keyword_search endpoint.
    Set THREADS_APP_REVIEW_APPROVED=true after getting approval.
    """

    def __init__(
        self,
        access_token: str | None = None,
        api_version: str = "v1.0",
        config: dict[str, Any] | None = None,
        app_review_approved: bool | None = None,
    ):
        """
        Initialize Threads adapter.

        Args:
            access_token: Threads access token (or THREADS_ACCESS_TOKEN env var)
            api_version: Meta API version
            config: Additional configuration
            app_review_approved: Whether App Review is approved (or THREADS_APP_REVIEW_APPROVED env)
        """
        super().__init__(platform="threads", config=config)

        self.access_token = access_token or os.getenv("THREADS_ACCESS_TOKEN", "")
        self.api_version = api_version
        self.base_url = f"https://graph.threads.net/{api_version}"

        # App Review status - must be explicitly set after approval
        self._app_review_approved = app_review_approved or os.getenv("THREADS_APP_REVIEW_APPROVED", "").lower() in ("true", "1", "yes")

        logger.debug(
            f"Threads adapter initialized: has_token={bool(self.access_token)}, "
            f"api_version={api_version}, app_review_approved={self._app_review_approved}"
        )

    def is_available(self) -> bool:
        """
        Check if Threads API is available for searching.

        Returns True only if:
        1. Access token is configured
        2. Meta App Review has been approved

        Note: Even with credentials, /keyword_search requires App Review approval.
        """
        return bool(self.access_token) and self._app_review_approved

    def get_availability_status(self) -> dict[str, Any]:
        """
        Get detailed availability status for diagnostics.

        Returns a dict with:
        - has_token: Whether access token is configured
        - app_review_approved: Whether App Review is approved
        - available: Whether the adapter can perform searches
        - reason: Human-readable reason if not available
        """
        has_token = bool(self.access_token)

        if not has_token:
            return {
                "has_token": False,
                "app_review_approved": self._app_review_approved,
                "available": False,
                "reason": "THREADS_ACCESS_TOKEN not configured",
            }

        if not self._app_review_approved:
            return {
                "has_token": True,
                "app_review_approved": False,
                "available": False,
                "reason": "Meta App Review not approved. Set THREADS_APP_REVIEW_APPROVED=true after approval.",
            }

        return {
            "has_token": True,
            "app_review_approved": True,
            "available": True,
            "reason": "Ready to search",
        }

    async def search(self, keyword: str) -> list[SourceCandidate]:
        """
        Search for Threads accounts matching the keyword.

        NOTE: This endpoint requires Meta App Review approval.
        If not approved, returns empty list with a clear warning.

        Args:
            keyword: Search keyword

        Returns:
            List of SourceCandidate objects for matching accounts
        """
        status = self.get_availability_status()

        if not status["available"]:
            logger.warning(f"Threads adapter not available: {status['reason']}")
            return []

        # TODO: Implement actual API call once App Review is approved
        # Current limitation: This code path is reached only when app_review_approved=True
        # but the actual /keyword_search API call needs to be implemented
        logger.info(f"Threads search for '{keyword}' - API call not yet implemented")

        # Placeholder: Return empty until actual API is implemented
        # After App Review approval, implement:
        #   async with httpx.AsyncClient() as client:
        #       response = await client.get(f"{self.base_url}/keyword_search", ...)
        return []

    def get_rate_limit_info(self) -> dict[str, Any]:
        """Get current rate limit status."""
        status = self.get_availability_status()
        return {
            "platform": self.platform,
            "available": status["available"],
            "has_token": status["has_token"],
            "app_review_approved": status["app_review_approved"],
            "remaining": RATE_LIMIT_PER_7_DAYS,  # Would track actual usage
            "limit": RATE_LIMIT_PER_7_DAYS,
            "window_days": 7,
            "note": "Requires Meta App Review approval. Set THREADS_APP_REVIEW_APPROVED=true after approval.",
        }
