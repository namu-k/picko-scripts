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


class TestSupportedPlatforms:
    """Tests for supported platforms list"""

    def test_supported_platforms_constant(self):
        """Test SUPPORTED_PLATFORMS constant"""
        from scripts.engagement_sync import EngagementSyncer

        expected = ["twitter", "linkedin", "newsletter", "blog", "instagram", "youtube"]
        assert EngagementSyncer.SUPPORTED_PLATFORMS == expected
