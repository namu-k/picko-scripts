"""
Threads Discovery Adapter.

Implements source discovery via Meta's Threads API.

NOTE: This adapter requires Meta App Review approval for /keyword_search endpoint.
If not available, the adapter will return empty results.
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

    NOTE: Requires Meta App Review approval for /keyword_search endpoint.
    """

    def __init__(
        self,
        access_token: str | None = None,
        api_version: str = "v1.0",
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize Threads adapter.

        Args:
            access_token: Threads access token (or THREADS_ACCESS_TOKEN env var)
            api_version: Meta API version
            config: Additional configuration
        """
        super().__init__(platform="threads", config=config)

        self.access_token = access_token or os.getenv("THREADS_ACCESS_TOKEN", "")
        self.api_version = api_version
        self.base_url = f"https://graph.threads.net/{api_version}"

        logger.debug(f"Threads adapter initialized: has_token={bool(self.access_token)}, " f"api_version={api_version}")

    def is_available(self) -> bool:
        """
        Check if Threads API is available.

        Note: Even with credentials, /keyword_search requires App Review approval.
        """
        return bool(self.access_token)

    async def search(self, keyword: str) -> list[SourceCandidate]:
        """
        Search for Threads accounts matching the keyword.

        NOTE: This endpoint requires Meta App Review approval.
        If not approved, returns empty list.

        Args:
            keyword: Search keyword

        Returns:
            List of SourceCandidate objects for matching accounts
        """
        if not self.is_available():
            logger.warning("Threads adapter not configured (missing access token)")
            return []

        # TODO: Implement actual API call once App Review is approved
        # Current limitation: /keyword_search requires App Review
        logger.warning("Threads API /keyword_search requires Meta App Review approval. " "Returning empty results.")

        return []

    def get_rate_limit_info(self) -> dict[str, Any]:
        """Get current rate limit status."""
        return {
            "platform": self.platform,
            "available": self.is_available(),
            "remaining": RATE_LIMIT_PER_7_DAYS,  # Would track actual usage
            "limit": RATE_LIMIT_PER_7_DAYS,
            "window_days": 7,
            "note": "/keyword_search requires Meta App Review approval",
        }
