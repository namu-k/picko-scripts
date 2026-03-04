"""
Mastodon Discovery Adapter.

Implements source discovery via Mastodon's API.
"""

import os
from typing import Any

import httpx

from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate
from picko.logger import get_logger

logger = get_logger("discovery.adapters.mastodon")

# Rate limits: 30 requests/minute for authenticated requests
RATE_LIMIT_PER_MINUTE = 30
RATE_LIMIT_WINDOW = 60  # seconds


class MastodonDiscoveryAdapter(BaseDiscoveryCollector):
    """
    Mastodon API adapter for source discovery.

    Uses Mastodon's search API to find accounts.
    Rate limit: 30 requests/minute
    """

    def __init__(
        self,
        access_token: str | None = None,
        instance: str = "mastodon.social",
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize Mastodon adapter.

        Args:
            access_token: Mastodon access token (or MASTODON_ACCESS_TOKEN env var)
            instance: Mastodon instance URL (or MASTODON_INSTANCE env var)
            config: Additional configuration
        """
        super().__init__(platform="mastodon", config=config)

        self.access_token = access_token or os.getenv("MASTODON_ACCESS_TOKEN", "")
        self.instance = os.getenv("MASTODON_INSTANCE") or instance

        # Rate limiting
        self._request_timestamps: list[float] = []

        logger.debug(f"Mastodon adapter initialized: instance={self.instance}, " f"has_token={bool(self.access_token)}")

    def is_available(self) -> bool:
        """Check if Mastodon API credentials are configured."""
        return bool(self.access_token)

    async def search(self, keyword: str) -> list[SourceCandidate]:
        """
        Search for Mastodon accounts matching the keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of SourceCandidate objects for matching accounts
        """
        if not self.is_available():
            logger.warning("Mastodon adapter not configured (missing access token)")
            return []

        try:
            url = f"https://{self.instance}/api/v2/search"
            params: dict[str, str | int] = {
                "q": keyword,
                "type": "accounts",
                "limit": 40,
            }
            headers = {
                "Authorization": f"Bearer {self.access_token}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                data = response.json()
                return self._parse_search_results(data, keyword)

        except httpx.HTTPStatusError as e:
            logger.error(f"Mastodon API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Mastodon search failed: {e}")
            return []

    def _parse_search_results(self, data: dict[str, Any], keyword: str) -> list[SourceCandidate]:
        """Parse Mastodon search results into SourceCandidates."""
        candidates = []

        accounts = data.get("accounts", [])
        for account in accounts:
            # Skip bot accounts
            if account.get("bot", False):
                continue

            username = account.get("username", "")
            if not username:
                continue

            # Calculate relevance score based on followers
            followers = account.get("followers_count", 0)
            relevance = self._calculate_relevance(followers)

            handle = self._format_handle(username)
            url = account.get("url", f"https://{self.instance}/@{username}")

            candidate = self._create_candidate(
                handle=handle,
                url=url,
                relevance_score=relevance,
                display_name=account.get("display_name", username),
                description=self._clean_html(account.get("note", "")),
                followers=followers,
                verified=False,
                discovered_keyword=keyword,
                metadata={
                    "account_id": account.get("id"),
                    "following_count": account.get("following_count"),
                    "statuses_count": account.get("statuses_count"),
                },
            )
            candidates.append(candidate)

        # Sort by relevance score descending
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(f"Found {len(candidates)} Mastodon accounts for '{keyword}'")
        return candidates

    def _format_handle(self, username: str) -> str:
        """
        Format Mastodon handle with instance.

        Args:
            username: Account username

        Returns:
            Formatted handle (e.g., @user@mastodon.social)
        """
        return f"@{username}@{self.instance}"

    def _clean_html(self, html: str) -> str:
        """
        Strip HTML tags from Mastodon note.

        Args:
            html: HTML content

        Returns:
            Plain text
        """
        import re

        # Simple HTML tag removal
        clean = re.sub(r"<[^>]+>", "", html)
        return clean.strip()

    def _calculate_relevance(self, followers: int) -> float:
        """
        Calculate relevance score based on follower count.

        Uses logarithmic scale to handle large differences.

        Args:
            followers: Number of followers

        Returns:
            Relevance score (0.0-1.0)
        """
        if followers <= 0:
            return 0.1

        import math

        # Logarithmic scale: 1K -> ~0.4, 10K -> ~0.5, 100K -> ~0.6, 1M -> ~0.7
        log_score = math.log10(max(followers, 10)) / 8
        return min(0.9, max(0.1, log_score))

    def get_rate_limit_info(self) -> dict[str, Any]:
        """Get current rate limit status."""
        import time

        # Clean old timestamps
        now = time.time()
        self._request_timestamps = [ts for ts in self._request_timestamps if now - ts < RATE_LIMIT_WINDOW]

        remaining = RATE_LIMIT_PER_MINUTE - len(self._request_timestamps)

        return {
            "platform": self.platform,
            "available": self.is_available(),
            "remaining": max(0, remaining),
            "limit": RATE_LIMIT_PER_MINUTE,
            "window_seconds": RATE_LIMIT_WINDOW,
        }
