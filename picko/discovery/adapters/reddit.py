"""
Reddit Discovery Adapter.

Implements source discovery via Reddit's OAuth API.
"""

import os
from typing import Any

import httpx

from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate
from picko.logger import get_logger

logger = get_logger("discovery.adapters.reddit")

# Rate limits: 60 requests/minute for OAuth
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_WINDOW = 60  # seconds


class RedditDiscoveryAdapter(BaseDiscoveryCollector):
    """
    Reddit API adapter for source discovery.

    Uses Reddit's OAuth API to search for subreddits.
    Rate limit: 60 requests/minute
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str = "picko-discovery/1.0",
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize Reddit adapter.

        Args:
            client_id: Reddit app client ID (or REDDIT_CLIENT_ID env var)
            client_secret: Reddit app client secret (or REDDIT_CLIENT_SECRET env var)
            user_agent: User agent string for API requests
            config: Additional configuration
        """
        super().__init__(platform="reddit", config=config)

        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.user_agent = user_agent

        # Token caching
        self._access_token: str | None = None
        self._token_expires_at: float = 0

        # Rate limiting
        self._request_timestamps: list[float] = []

        logger.debug(
            f"Reddit adapter initialized: client_id={self.client_id[:8]}..."
            if self.client_id
            else "Reddit adapter initialized: no credentials"
        )

    def is_available(self) -> bool:
        """Check if Reddit API credentials are configured."""
        return bool(self.client_id and self.client_secret)

    async def _get_access_token(self) -> str:
        """
        Obtain OAuth access token from Reddit.

        Tokens are cached until expiry.

        Returns:
            Access token string

        Raises:
            httpx.HTTPStatusError: If authentication fails
        """
        import time

        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        url = "https://www.reddit.com/api/v1/access_token"
        # Type guard - credentials checked by is_available()
        assert self.client_id and self.client_secret, "Credentials required"
        auth = httpx.BasicAuth(self.client_id, self.client_secret)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=auth,
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()

            data = response.json()
            token: str = data["access_token"]
            self._access_token = token
            # Set expiry with 60 second buffer
            self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60

            logger.info("Obtained Reddit access token")
            return token

    async def search(self, keyword: str) -> list[SourceCandidate]:
        """
        Search for subreddits matching the keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of SourceCandidate objects for matching subreddits
        """
        if not self.is_available():
            logger.warning("Reddit adapter not configured (missing credentials)")
            return []

        try:
            token = await self._get_access_token()

            url = "https://oauth.reddit.com/subreddits/search"
            params = {
                "q": keyword,
                "limit": 25,
                "sort": "relevance",
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                data = response.json()
                return self._parse_search_results(data, keyword)

        except httpx.HTTPStatusError as e:
            logger.error(f"Reddit API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            return []

    def _parse_search_results(self, data: dict[str, Any], keyword: str) -> list[SourceCandidate]:
        """Parse Reddit search results into SourceCandidates."""
        candidates = []

        children = data.get("data", {}).get("children", [])
        for child in children:
            subreddit = child.get("data", {})

            # Skip NSFW subreddits
            if subreddit.get("over18", False):
                continue

            handle = subreddit.get("display_name", "")
            if not handle:
                continue

            # Calculate relevance score based on subscribers
            subscribers = subreddit.get("subscribers", 0)
            relevance = self._calculate_relevance(subscribers)

            candidate = self._create_candidate(
                handle=f"r/{handle}",
                url=f"https://reddit.com/r/{handle}",
                relevance_score=relevance,
                display_name=subreddit.get("title", handle),
                description=subreddit.get("public_description", ""),
                followers=subscribers,
                verified=False,
                discovered_keyword=keyword,
                metadata={
                    "subreddit_type": subreddit.get("subreddit_type"),
                    "created_utc": subreddit.get("created_utc"),
                },
            )
            candidates.append(candidate)

        # Sort by relevance score descending
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(f"Found {len(candidates)} Reddit subreddits for '{keyword}'")
        return candidates

    def _calculate_relevance(self, subscribers: int) -> float:
        """
        Calculate relevance score based on subscriber count.

        Uses logarithmic scale to handle large differences.

        Args:
            subscribers: Number of subscribers

        Returns:
            Relevance score (0.0-1.0)
        """
        if subscribers <= 0:
            return 0.1

        import math

        # Logarithmic scale: 1K -> ~0.4, 10K -> ~0.5, 100K -> ~0.6, 1M -> ~0.7, 10M -> ~0.8
        log_score = math.log10(max(subscribers, 10)) / 8  # Max at ~100M
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
