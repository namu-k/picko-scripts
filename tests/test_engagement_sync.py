"""
Tests for engagement_sync.py

Unit tests for the EngagementSyncer class covering:
- EngagementMetrics dataclass
- SyncResult dataclass
- sync_all and sync_single methods
- Platform-specific metric fetching (Twitter, LinkedIn)
- Log retrieval and updating
"""

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.vault.root = "/tmp/test_vault"
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    vault.list_notes.return_value = []
    vault.read_note.return_value = ({}, "Test content")
    vault.read_frontmatter.return_value = {}
    vault.update_frontmatter.return_value = None
    return vault


@pytest.fixture
def sample_published_log():
    """Sample published log entry"""
    return {
        "path": "/tmp/test_vault/Logs/Publish/test_log.md",
        "status": "published",
        "published_at": datetime.now().isoformat(),
        "platform": "twitter",
        "content_id": "test_123",
        "published_url": "https://twitter.com/user/status/1234567890",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────


class TestEngagementMetrics:
    """Tests for EngagementMetrics dataclass"""

    def test_default_values(self):
        """Test default values are all zero"""
        from scripts.engagement_sync import EngagementMetrics

        metrics = EngagementMetrics()

        assert metrics.views == 0
        assert metrics.likes == 0
        assert metrics.comments == 0
        assert metrics.shares == 0
        assert metrics.clicks == 0
        assert metrics.impressions == 0

    def test_custom_values(self):
        """Test custom values"""
        from scripts.engagement_sync import EngagementMetrics

        metrics = EngagementMetrics(views=100, likes=50, comments=10, shares=5, clicks=20, impressions=500)

        assert metrics.views == 100
        assert metrics.likes == 50
        assert metrics.comments == 10
        assert metrics.shares == 5
        assert metrics.clicks == 20
        assert metrics.impressions == 500

    def test_to_dict(self):
        """Test to_dict method"""
        from scripts.engagement_sync import EngagementMetrics

        metrics = EngagementMetrics(views=100, likes=50)
        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["views"] == 100
        assert result["likes"] == 50
        assert "comments" in result
        assert "shares" in result


class TestSyncResult:
    """Tests for SyncResult dataclass"""

    def test_success_result(self):
        """Test successful sync result"""
        from scripts.engagement_sync import EngagementMetrics, SyncResult

        metrics = EngagementMetrics(views=100)
        result = SyncResult(
            log_path="/test/log.md",
            platform="twitter",
            success=True,
            metrics=metrics,
            synced_at="2026-02-17T12:00:00",
        )

        assert result.success is True
        assert result.metrics is not None
        assert result.metrics.views == 100
        assert result.error == ""

    def test_failure_result(self):
        """Test failed sync result"""
        from scripts.engagement_sync import SyncResult

        result = SyncResult(
            log_path="/test/log.md",
            platform="twitter",
            success=False,
            error="API rate limit exceeded",
            synced_at="2026-02-17T12:00:00",
        )

        assert result.success is False
        assert result.metrics is None
        assert "rate limit" in result.error


class TestEngagementSyncerInit:
    """Tests for EngagementSyncer initialization"""

    @patch("scripts.engagement_sync.get_config")
    @patch("scripts.engagement_sync.VaultIO")
    def test_init(self, mock_vault_class, mock_get_config, mock_config):
        """Test initialization"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        syncer = EngagementSyncer()

        assert syncer.config is not None
        assert syncer.vault is not None
        assert syncer.logs_path == "Logs/Publish"
        assert syncer._twitter_client is None


class TestGetPublishedLogs:
    """Tests for _get_published_logs method"""

    @patch("scripts.engagement_sync.get_config")
    def test_get_published_logs_filters_by_status(self, mock_get_config, mock_config, mock_vault):
        """Test that only published logs are returned"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"

            # Setup mock - one published, one draft
            mock_vault.list_notes.return_value = [Path("/log1.md"), Path("/log2.md")]
            mock_vault.read_frontmatter.side_effect = [
                {"status": "published", "published_at": datetime.now().isoformat()},
                {"status": "draft"},
            ]

            result = syncer._get_published_logs(datetime.now() - timedelta(days=7))

        assert len(result) == 1
        assert result[0]["status"] == "published"

    @patch("scripts.engagement_sync.get_config")
    def test_get_published_logs_filters_by_date(self, mock_get_config, mock_config, mock_vault):
        """Test that only recent logs are returned"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"

            # One recent, one old
            recent_date = datetime.now() - timedelta(days=1)
            old_date = datetime.now() - timedelta(days=30)

            mock_vault.list_notes.return_value = [Path("/log1.md"), Path("/log2.md")]
            mock_vault.read_frontmatter.side_effect = [
                {"status": "published", "published_at": recent_date.isoformat()},
                {"status": "published", "published_at": old_date.isoformat()},
            ]

            result = syncer._get_published_logs(datetime.now() - timedelta(days=7))

        # Only the recent one should be returned
        assert len(result) == 1


class TestFetchMetrics:
    """Tests for _fetch_metrics method"""

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_metrics_twitter(self, mock_get_config, mock_config):
        """Test fetching Twitter metrics"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = None
            syncer._get_twitter_client = MagicMock(return_value=None)

            log_entry = {
                "content_id": "123",
                "published_url": "https://twitter.com/user/status/1234567890",
            }

            result = syncer._fetch_metrics(log_entry, "twitter")

        # Should return empty metrics when Twitter client is not available
        assert result is not None
        assert result.views == 0

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_metrics_linkedin(self, mock_get_config, mock_config):
        """Test fetching LinkedIn metrics"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            log_entry = {
                "content_id": "123",
                "published_url": "https://linkedin.com/posts/123",
            }

            result = syncer._fetch_metrics(log_entry, "linkedin")

        # LinkedIn not implemented, should return empty metrics
        assert result is not None

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_metrics_unknown_platform(self, mock_get_config, mock_config):
        """Test fetching metrics for unknown platform"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            log_entry = {"content_id": "123"}
            result = syncer._fetch_metrics(log_entry, "unknown_platform")

        # Unknown platform should return empty metrics
        assert result is not None


class TestExtractTweetId:
    """Tests for _extract_tweet_id method"""

    @patch("scripts.engagement_sync.get_config")
    def test_extract_from_twitter_url(self, mock_get_config, mock_config):
        """Test extracting ID from twitter.com URL"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            url = "https://twitter.com/elonmusk/status/1234567890123456789"
            result = syncer._extract_tweet_id(url)

        assert result == "1234567890123456789"

    @patch("scripts.engagement_sync.get_config")
    def test_extract_from_x_url(self, mock_get_config, mock_config):
        """Test extracting ID from x.com URL"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            url = "https://x.com/elonmusk/status/9876543210987654321"
            result = syncer._extract_tweet_id(url)

        assert result == "9876543210987654321"

    @patch("scripts.engagement_sync.get_config")
    def test_extract_from_invalid_url(self, mock_get_config, mock_config):
        """Test extracting ID from invalid URL"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            url = "https://example.com/something"
            result = syncer._extract_tweet_id(url)

        assert result is None

    @patch("scripts.engagement_sync.get_config")
    def test_extract_from_empty_url(self, mock_get_config, mock_config):
        """Test extracting ID from empty URL"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)

            result = syncer._extract_tweet_id("")

        assert result is None


class TestSyncAll:
    """Tests for sync_all method"""

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_empty_logs(self, mock_get_config, mock_config, mock_vault):
        """Test sync_all with no logs"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(return_value=[])

            result = syncer.sync_all(days=7)

        assert len(result) == 0

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_with_platforms_filter(self, mock_get_config, mock_config, mock_vault):
        """Test sync_all with platform filter"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(
                return_value=[
                    {"path": "/log1.md", "platform": "twitter"},
                    {"path": "/log2.md", "platform": "linkedin"},
                ]
            )
            syncer._fetch_metrics = MagicMock(return_value=None)

            # Filter to only twitter
            result = syncer.sync_all(days=7, platforms=["twitter"])

        # Should only process twitter
        assert all(r.platform == "twitter" for r in result)

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_dry_run(self, mock_get_config, mock_config, mock_vault):
        """Test sync_all in dry run mode"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(return_value=[{"path": "/log1.md", "platform": "twitter"}])
            syncer._fetch_metrics = MagicMock(return_value=EngagementMetrics(views=100))

            result = syncer.sync_all(days=7, dry_run=True)

        # Dry run should not update frontmatter
        mock_vault.update_frontmatter.assert_not_called()
        assert len(result) == 1


class TestSyncSingle:
    """Tests for sync_single method"""

    @patch("scripts.engagement_sync.get_config")
    def test_sync_single_success(self, mock_get_config, mock_config, mock_vault):
        """Test successful single log sync"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({"platform": "twitter"}, "content")

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer._twitter_client = None
            syncer._fetch_metrics = MagicMock(return_value=EngagementMetrics(views=100))

            result = syncer.sync_single("/test/log.md", dry_run=True)

        assert result.success is True
        assert result.metrics is not None
        assert result.metrics.views == 100

    @patch("scripts.engagement_sync.get_config")
    def test_sync_single_unsupported_platform(self, mock_get_config, mock_config, mock_vault):
        """Test sync with unsupported platform"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({"platform": "tiktok"}, "content")

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault

            result = syncer.sync_single("/test/log.md", dry_run=True)

        assert result.success is False
        assert "Unsupported platform" in result.error


class TestUpdateLogMetrics:
    """Tests for _update_log_metrics method"""

    @patch("scripts.engagement_sync.get_config")
    def test_update_log_metrics(self, mock_get_config, mock_config, mock_vault):
        """Test updating log metrics"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault

            metrics = EngagementMetrics(views=100, likes=50)
            syncer._update_log_metrics("/test/log.md", metrics)

        mock_vault.update_frontmatter.assert_called_once()
        call_args = mock_vault.update_frontmatter.call_args
        assert call_args[0][0] == "/test/log.md"
        assert "metrics" in call_args[0][1]
        assert "metrics_synced_at" in call_args[0][1]


class TestTwitterClientAuthentication:
    """Tests for Twitter client auth and initialization paths"""

    @patch("scripts.engagement_sync.get_config")
    def test_get_twitter_client_returns_none_when_tweepy_missing(self, mock_get_config, mock_config):
        """Twitter client is unavailable when tweepy is not installed"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = None

            with patch("scripts.engagement_sync.tweepy", None):
                result = syncer._get_twitter_client()

        assert result is None

    @patch("scripts.engagement_sync.get_config")
    def test_get_twitter_client_returns_none_without_bearer_token(self, mock_get_config, mock_config):
        """Bearer token is required for Twitter API authentication"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        tweepy_module = SimpleNamespace(Client=MagicMock())
        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = None

            with patch.dict("os.environ", {}, clear=True):
                with patch("scripts.engagement_sync.tweepy", tweepy_module):
                    result = syncer._get_twitter_client()

        assert result is None
        tweepy_module.Client.assert_not_called()

    @patch("scripts.engagement_sync.get_config")
    def test_get_twitter_client_initializes_with_env_credentials(self, mock_get_config, mock_config):
        """Twitter client is created using environment credentials"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        client_instance = MagicMock()
        client_ctor = MagicMock(return_value=client_instance)
        tweepy_module = SimpleNamespace(Client=client_ctor)

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = None

            env = {
                "TWITTER_BEARER_TOKEN": "bearer",
                "TWITTER_API_KEY": "api-key",
                "TWITTER_API_SECRET": "api-secret",
                "TWITTER_ACCESS_TOKEN": "access-token",
                "TWITTER_ACCESS_TOKEN_SECRET": "access-secret",
            }

            with patch.dict("os.environ", env, clear=True):
                with patch("scripts.engagement_sync.tweepy", tweepy_module):
                    result = syncer._get_twitter_client()

        assert result is client_instance
        client_ctor.assert_called_once_with(
            bearer_token="bearer",
            consumer_key="api-key",
            consumer_secret="api-secret",
            access_token="access-token",
            access_token_secret="access-secret",
        )

    @patch("scripts.engagement_sync.get_config")
    def test_get_twitter_client_returns_cached_instance(self, mock_get_config, mock_config):
        """Cached client should be returned without re-initialization"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = MagicMock()

            with patch("scripts.engagement_sync.tweepy", SimpleNamespace(Client=MagicMock())):
                result = syncer._get_twitter_client()

        assert result is syncer._twitter_client

    @patch("scripts.engagement_sync.get_config")
    def test_get_twitter_client_handles_constructor_error(self, mock_get_config, mock_config):
        """Initialization errors should be handled and return None"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        ctor = MagicMock(side_effect=RuntimeError("auth failed"))
        tweepy_module = SimpleNamespace(Client=ctor)

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._twitter_client = None

            with patch.dict("os.environ", {"TWITTER_BEARER_TOKEN": "bearer"}, clear=True):
                with patch("scripts.engagement_sync.tweepy", tweepy_module):
                    result = syncer._get_twitter_client()

        assert result is None


class TestTwitterMetricsFetch:
    """Tests for detailed Twitter metric sync behavior"""

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_twitter_metrics_uses_content_id_when_url_has_no_id(self, mock_get_config, mock_config):
        """Fallback to content_id when URL parsing fails"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        metric_obj = SimpleNamespace(
            impression_count=120,
            like_count=20,
            reply_count=3,
            retweet_count=4,
            quote_count=1,
        )
        response = SimpleNamespace(data=SimpleNamespace(public_metrics=metric_obj))
        client = MagicMock()
        client.get_tweet.return_value = response

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._get_twitter_client = MagicMock(return_value=client)
            syncer._extract_tweet_id = MagicMock(return_value=None)

            metrics = syncer._fetch_twitter_metrics("fallback-id", "https://example.com/no-status")

        assert metrics.views == 120
        assert metrics.shares == 5
        client.get_tweet.assert_called_once_with("fallback-id", tweet_fields=["public_metrics", "non_public_metrics"])

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_twitter_metrics_returns_empty_without_tweet_identifier(self, mock_get_config, mock_config):
        """Returns empty metrics when both URL and content_id are missing"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        client = MagicMock()

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._get_twitter_client = MagicMock(return_value=client)
            syncer._extract_tweet_id = MagicMock(return_value=None)

            metrics = syncer._fetch_twitter_metrics("", "")

        assert metrics.to_dict() == {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "clicks": 0,
            "impressions": 0,
        }
        client.get_tweet.assert_not_called()

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_twitter_metrics_returns_empty_on_missing_response_data(self, mock_get_config, mock_config):
        """Handles API success response without data payload"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        client = MagicMock()
        client.get_tweet.return_value = SimpleNamespace(data=None)

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._get_twitter_client = MagicMock(return_value=client)
            syncer._extract_tweet_id = MagicMock(return_value="123")

            metrics = syncer._fetch_twitter_metrics("123", "https://x.com/user/status/123")

        assert metrics.views == 0
        assert metrics.likes == 0

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_twitter_metrics_handles_rate_limit_error(self, mock_get_config, mock_config):
        """Rate-limit style API errors return empty metrics"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        client = MagicMock()
        client.get_tweet.side_effect = RuntimeError("429 Too Many Requests")

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._get_twitter_client = MagicMock(return_value=client)
            syncer._extract_tweet_id = MagicMock(return_value="123")

            metrics = syncer._fetch_twitter_metrics("123", "https://x.com/user/status/123")

        assert metrics.views == 0
        assert metrics.impressions == 0

    @patch("scripts.engagement_sync.get_config")
    def test_fetch_twitter_metrics_handles_timeout_error(self, mock_get_config, mock_config):
        """Timeout-like API errors return empty metrics without raising"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        client = MagicMock()
        client.get_tweet.side_effect = TimeoutError("request timed out")

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer._get_twitter_client = MagicMock(return_value=client)
            syncer._extract_tweet_id = MagicMock(return_value="123")

            metrics = syncer._fetch_twitter_metrics("123", "https://x.com/user/status/123")

        assert metrics.to_dict()["views"] == 0


class TestSyncBehaviorAndErrors:
    """Tests for batch sync flows and error handling"""

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_processes_multiple_items_in_batch(self, mock_get_config, mock_config, mock_vault):
        """Batch sync processes multiple published logs"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(
                return_value=[
                    {
                        "path": "/log1.md",
                        "platform": "twitter",
                        "content_id": "111",
                        "published_url": "",
                    },
                    {
                        "path": "/log2.md",
                        "platform": "linkedin",
                        "content_id": "222",
                        "published_url": "",
                    },
                ]
            )
            syncer._fetch_metrics = MagicMock(side_effect=[EngagementMetrics(views=10), EngagementMetrics(views=20)])

            results = syncer.sync_all(days=7)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True
        assert mock_vault.update_frontmatter.call_count == 2

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_marks_partial_failures_and_continues(self, mock_get_config, mock_config, mock_vault):
        """One failing item should not block the rest of batch sync"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(
                return_value=[
                    {"path": "/ok.md", "platform": "twitter"},
                    {"path": "/bad.md", "platform": "twitter"},
                    {"path": "/ok2.md", "platform": "twitter"},
                ]
            )
            syncer._fetch_metrics = MagicMock(
                side_effect=[
                    EngagementMetrics(views=1),
                    RuntimeError("rate limited"),
                    EngagementMetrics(views=2),
                ]
            )

            results = syncer.sync_all(days=7)

        assert len(results) == 3
        assert [r.success for r in results] == [True, False, True]
        assert "rate limited" in results[1].error

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_records_write_error_as_failure(self, mock_get_config, mock_config, mock_vault):
        """Vault write failures are captured as failed sync results"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(return_value=[{"path": "/log1.md", "platform": "twitter"}])
            syncer._fetch_metrics = MagicMock(return_value=EngagementMetrics(views=100))
            mock_vault.update_frontmatter.side_effect = OSError("disk write error")

            results = syncer.sync_all(days=7)

        assert len(results) == 1
        assert results[0].success is False
        assert "disk write error" in results[0].error

    @patch("scripts.engagement_sync.get_config")
    def test_sync_all_filters_invalid_platforms_from_request(self, mock_get_config, mock_config, mock_vault):
        """Only supported requested platforms should be synced"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            syncer._twitter_client = None
            syncer._get_published_logs = MagicMock(
                return_value=[
                    {"path": "/twitter.md", "platform": "twitter"},
                    {"path": "/linkedin.md", "platform": "linkedin"},
                ]
            )
            syncer._fetch_metrics = MagicMock(return_value=EngagementMetrics(views=1))

            results = syncer.sync_all(days=7, platforms=["twitter", "not-a-platform"])

        assert len(results) == 1
        assert results[0].platform == "twitter"

    @patch("scripts.engagement_sync.get_config")
    def test_sync_single_returns_failure_on_vault_read_error(self, mock_get_config, mock_config, mock_vault):
        """sync_single returns failed result when vault read raises"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.side_effect = FileNotFoundError("missing note")

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault

            result = syncer.sync_single("/missing.md")

        assert result.success is False
        assert result.platform == "unknown"
        assert "missing note" in result.error

    @patch("scripts.engagement_sync.get_config")
    def test_sync_single_returns_failure_on_vault_write_error(self, mock_get_config, mock_config, mock_vault):
        """sync_single captures write failures when updating metrics"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({"platform": "twitter"}, "content")
        mock_vault.update_frontmatter.side_effect = PermissionError("write denied")

        from scripts.engagement_sync import EngagementMetrics, EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer._fetch_metrics = MagicMock(return_value=EngagementMetrics(views=3))

            result = syncer.sync_single("/test/log.md", dry_run=False)

        assert result.success is False
        assert "write denied" in result.error


class TestPublishedStatusTransitions:
    """Tests for status filtering in published log retrieval"""

    @patch("scripts.engagement_sync.get_config")
    def test_get_published_logs_only_includes_published_status(self, mock_get_config, mock_config, mock_vault):
        """Draft and archived logs are excluded from sync targets"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        recent = datetime.now().isoformat()
        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            mock_vault.list_notes.return_value = [
                Path("/draft.md"),
                Path("/published.md"),
                Path("/archived.md"),
            ]
            mock_vault.read_frontmatter.side_effect = [
                {"status": "draft", "published_at": recent},
                {"status": "published", "published_at": recent, "platform": "twitter"},
                {"status": "archived", "published_at": recent},
            ]

            logs = syncer._get_published_logs(datetime.now() - timedelta(days=2))

        assert len(logs) == 1
        assert logs[0]["status"] == "published"

    @patch("scripts.engagement_sync.get_config")
    def test_get_published_logs_skips_notes_with_frontmatter_read_error(self, mock_get_config, mock_config, mock_vault):
        """Frontmatter read errors are skipped without stopping list processing"""
        mock_get_config.return_value = mock_config

        from scripts.engagement_sync import EngagementSyncer

        with patch.object(EngagementSyncer, "__init__", lambda x: None):
            syncer = EngagementSyncer.__new__(EngagementSyncer)
            syncer.vault = mock_vault
            syncer.logs_path = "Logs/Publish"
            mock_vault.list_notes.return_value = [Path("/bad.md"), Path("/good.md")]
            mock_vault.read_frontmatter.side_effect = [
                ValueError("invalid frontmatter"),
                {"status": "published", "published_at": datetime.now().isoformat()},
            ]

            logs = syncer._get_published_logs(datetime.now() - timedelta(days=3))

        assert len(logs) == 1


class TestSupportedPlatforms:
    """Tests for supported platforms list"""

    def test_supported_platforms_constant(self):
        """Test SUPPORTED_PLATFORMS constant"""
        from scripts.engagement_sync import EngagementSyncer

        expected = ["twitter", "linkedin", "newsletter", "blog", "instagram", "youtube"]
        assert EngagementSyncer.SUPPORTED_PLATFORMS == expected
