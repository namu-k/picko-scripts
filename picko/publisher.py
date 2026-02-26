import os
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from picko.logger import setup_logger

logger = setup_logger("publisher")


@dataclass
class PublishResult:
    success: bool
    tweet_id: str | None = None
    tweet_url: str | None = None
    error: str = ""


class TwitterPublisher:
    def __init__(self, username: str = "user"):
        self.username = username
        self._client: Any | None = None

    def _load_tweepy(self) -> Any | None:
        """Lazy load tweepy module."""
        try:
            return import_module("tweepy")
        except ImportError:
            return None

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client

        tweepy = self._load_tweepy()
        if tweepy is None:
            return None

        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        api_key = os.environ.get("TWITTER_API_KEY")
        api_secret = os.environ.get("TWITTER_API_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

        required = {
            "TWITTER_BEARER_TOKEN": bearer_token,
            "TWITTER_API_KEY": api_key,
            "TWITTER_API_SECRET": api_secret,
            "TWITTER_ACCESS_TOKEN": access_token,
            "TWITTER_ACCESS_TOKEN_SECRET": access_token_secret,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            return None

        try:
            self._client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            return self._client
        except Exception as exc:
            logger.error(f"Failed to initialize Twitter client: {exc}")
            return None

    def publish(self, text: str) -> PublishResult:
        client = self._get_client()
        if client is None:
            return PublishResult(success=False, error="Twitter client is not available")

        try:
            response = client.create_tweet(text=text)
            data = getattr(response, "data", None) or {}
            tweet_id = data.get("id")
            if tweet_id is None:
                return PublishResult(success=False, error="Twitter API response did not contain tweet id")

            tweet_id_str = str(tweet_id)
            tweet_url = f"https://twitter.com/{self.username}/status/{tweet_id_str}"
            return PublishResult(success=True, tweet_id=tweet_id_str, tweet_url=tweet_url)
        except Exception as exc:
            logger.error(f"Failed to publish tweet: {exc}")
            return PublishResult(success=False, error=str(exc))
