"""
Tests for daily_collector.py

Unit tests for the DailyCollector class covering:
- RSS fetch and parsing
- URL canonicalization and deduplication
- Content fetching
- NLP processing
- Embedding generation
- Score calculation
- Export and digest creation
"""

import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from picko.scoring import ContentScore

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.vault.root = "/tmp/test_vault"
    config.vault.inbox = "Inbox/Inputs"
    config.vault.digests = "Inbox/Inputs/_digests"
    config.scoring.weights = {"novelty": 0.3, "relevance": 0.4, "quality": 0.3}
    config.scoring.thresholds = {
        "auto_approve": 0.85,
        "auto_reject": 0.3,
        "minimum_display": 0.4,
    }
    config.sources = {
        "sources": [
            {
                "id": "test_source",
                "url": "https://example.com/feed",
                "type": "rss",
                "enabled": True,
                "category": "tech",
            }
        ]
    }
    config.get_account.return_value = {
        "interests": {"primary": ["AI", "startup"], "secondary": ["tech"]},
        "keywords": {"high_relevance": ["founder"], "medium_relevance": ["growth"]},
    }
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    vault.list_notes.return_value = []
    vault.read_frontmatter.return_value = {}
    vault.write_note.return_value = Path("/tmp/test_vault/Inbox/Inputs/test.md")
    return vault


@pytest.fixture
def mock_llm():
    """Mock LLM client"""
    llm = MagicMock()
    llm.summarize.return_value = "Test summary"
    llm.generate.return_value = "Point 1\nPoint 2\nPoint 3"
    llm.generate_tags.return_value = ["tag1", "tag2", "tag3"]
    return llm


@pytest.fixture
def mock_embedder():
    """Mock embedding manager"""
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 1024  # Mock embedding vector
    return embedder


@pytest.fixture
def sample_rss_entry():
    """Sample RSS entry"""
    return {
        "title": "Test Article Title",
        "link": "https://example.com/article?utm_source=test",
        "summary": "This is a test article summary.",
        "published": "Mon, 17 Feb 2026 10:00:00 +0000",
    }


@pytest.fixture
def sample_item():
    """Sample processed item"""
    return {
        "source_id": "test_source",
        "source": "test_source",
        "source_url": "https://example.com/article",
        "title": "Test Article",
        "text": "Test content for the article.",
        "publish_date": "2026-02-17",
        "category": "tech",
        "url_hash": "abc123def456",
        "canonical_url": "https://example.com/article",
        "full_text": "Full article text content here.",
        "summary": "AI-generated summary",
        "key_points": ["Point 1", "Point 2", "Point 3"],
        "tags": ["AI", "tech"],
        "embedding": [0.1] * 1024,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────


class TestDailyCollectorInit:
    """Tests for DailyCollector initialization"""

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.VaultIO")
    @patch("scripts.daily_collector.get_summary_client")
    @patch("scripts.daily_collector.get_embedding_manager")
    @patch("scripts.daily_collector.get_renderer")
    def test_init_default(
        self,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test default initialization"""
        mock_get_config.return_value = mock_config
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector()

        assert collector.account_id == "socialbuilders"
        assert collector.dry_run is False
        assert collector.account_profile is not None

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.VaultIO")
    @patch("scripts.daily_collector.get_summary_client")
    @patch("scripts.daily_collector.get_embedding_manager")
    @patch("scripts.daily_collector.get_renderer")
    def test_init_with_account(
        self,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test initialization with specific account"""
        mock_get_config.return_value = mock_config
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector(account_id="custom_account")

        assert collector.account_id == "custom_account"

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.VaultIO")
    @patch("scripts.daily_collector.get_summary_client")
    @patch("scripts.daily_collector.get_embedding_manager")
    @patch("scripts.daily_collector.get_renderer")
    def test_init_dry_run(
        self,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test dry run mode"""
        mock_get_config.return_value = mock_config
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector(dry_run=True)

        assert collector.dry_run is True


class TestURLCanonicalization:
    """Tests for URL canonicalization"""

    def test_canonicalize_basic_url(self):
        """Test basic URL canonicalization"""
        from scripts.daily_collector import DailyCollector

        url = "https://example.com/article/"
        expected = "https://example.com/article"

        # Access private method through instance
        with patch("scripts.daily_collector.get_config"):
            collector = DailyCollector.__new__(DailyCollector)
            result = collector._canonicalize_url(url)

        assert result == expected

    def test_canonicalize_url_with_query_params(self):
        """Test URL with query parameters"""
        from scripts.daily_collector import DailyCollector

        url = "https://example.com/article?utm_source=test&id=123"
        expected = "https://example.com/article"

        with patch("scripts.daily_collector.get_config"):
            collector = DailyCollector.__new__(DailyCollector)
            result = collector._canonicalize_url(url)

        assert result == expected

    def test_canonicalize_url_with_fragment(self):
        """Test URL with fragment"""
        from scripts.daily_collector import DailyCollector

        url = "https://example.com/article#section1"

        with patch("scripts.daily_collector.get_config"):
            collector = DailyCollector.__new__(DailyCollector)
            result = collector._canonicalize_url(url)

        # Fragment is included in path
        assert "example.com/article" in result


class TestDeduplication:
    """Tests for deduplication logic"""

    @patch("scripts.daily_collector.get_config")
    def test_dedupe_empty_list(self, mock_get_config, mock_config):
        """Test deduplication with empty list"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.vault = MagicMock()
            collector.vault.list_notes.return_value = []
            collector.config = mock_config

            result = collector._dedupe([])

        assert result == []

    @patch("scripts.daily_collector.get_config")
    def test_dedupe_removes_duplicates(self, mock_get_config, mock_config, sample_item):
        """Test that duplicates are removed"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Create duplicate items (same URL)
        items = [
            {"source_url": "https://example.com/article1", "title": "Article 1"},
            {
                "source_url": "https://example.com/article1",
                "title": "Article 1 Duplicate",
            },
            {"source_url": "https://example.com/article2", "title": "Article 2"},
        ]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.vault = MagicMock()
            collector.vault.list_notes.return_value = []
            collector.vault.read_frontmatter.return_value = {}
            collector.config = mock_config

            result = collector._dedupe(items)

        # Should have 2 unique items
        assert len(result) == 2

    @patch("scripts.daily_collector.get_config")
    def test_dedupe_respects_existing_notes(self, mock_get_config, mock_config):
        """Test that existing notes are not duplicated"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Existing note with url_hash
        existing_hash = hashlib.md5(
            "https://example.com/existing".encode()
        ).hexdigest()[:12]

        items = [
            {"source_url": "https://example.com/existing", "title": "Existing Article"},
            {"source_url": "https://example.com/new", "title": "New Article"},
        ]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.vault = MagicMock()
            collector.vault.list_notes.return_value = ["existing_note.md"]
            collector.vault.read_frontmatter.return_value = {"url_hash": existing_hash}
            collector.config = mock_config

            result = collector._dedupe(items)

        # Only new article should remain
        assert len(result) == 1
        assert result[0]["source_url"] == "https://example.com/new"


class TestRSSFetch:
    """Tests for RSS feed fetching"""

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.feedparser")
    def test_fetch_rss_parses_entries(
        self, mock_feedparser, mock_get_config, mock_config, sample_rss_entry
    ):
        """Test RSS feed parsing"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Mock feedparser response
        mock_feed = MagicMock()
        mock_feed.entries = [sample_rss_entry]
        mock_feedparser.parse.return_value = mock_feed

        source = {
            "id": "test_source",
            "url": "https://example.com/feed",
            "category": "tech",
        }

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config

            result = collector._fetch_rss(source)

        assert len(result) == 1
        assert result[0]["title"] == "Test Article Title"
        assert result[0]["source_id"] == "test_source"

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.feedparser")
    def test_fetch_rss_limits_to_20(
        self, mock_feedparser, mock_get_config, mock_config
    ):
        """Test that RSS fetch limits to 20 entries"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Create 30 mock entries
        mock_feed = MagicMock()
        mock_feed.entries = [
            {"title": f"Article {i}", "link": f"https://example.com/{i}"}
            for i in range(30)
        ]
        mock_feedparser.parse.return_value = mock_feed

        source = {"id": "test_source", "url": "https://example.com/feed"}

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config

            result = collector._fetch_rss(source)

        assert len(result) == 20


class TestNLPProcessing:
    """Tests for NLP processing"""

    @patch("scripts.daily_collector.get_config")
    def test_nlp_process_adds_summary_and_tags(
        self, mock_get_config, mock_config, mock_llm
    ):
        """Test that NLP processing adds summary and tags"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        items = [
            {"title": "Test Article", "full_text": "Test content for NLP processing."}
        ]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.llm = mock_llm
            collector.config = mock_config

            result = collector._nlp_process(items)

        assert len(result) == 1
        assert "summary" in result[0]
        assert "tags" in result[0]
        assert "key_points" in result[0]

    @patch("scripts.daily_collector.get_config")
    def test_nlp_process_skips_empty_items(
        self, mock_get_config, mock_config, mock_llm
    ):
        """Test that empty items are skipped"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        items = [{"title": "Empty Article", "full_text": ""}]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.llm = mock_llm
            collector.config = mock_config

            result = collector._nlp_process(items)

        assert len(result) == 0


class TestEmbedding:
    """Tests for embedding generation"""

    @patch("scripts.daily_collector.get_config")
    def test_embed_adds_embedding(self, mock_get_config, mock_config, mock_embedder):
        """Test that embedding is added to items"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        items = [{"title": "Test Article", "summary": "Test summary"}]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.embedder = mock_embedder
            collector.config = mock_config

            result = collector._embed(items)

        assert len(result) == 1
        assert "embedding" in result[0]
        assert result[0]["embedding"] is not None

    @patch("scripts.daily_collector.get_config")
    def test_embed_handles_failure(self, mock_get_config, mock_config):
        """Test handling of embedding failure"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        mock_embedder_fail = MagicMock()
        mock_embedder_fail.embed.side_effect = Exception("Embedding failed")

        items = [{"title": "Test Article", "summary": "Test summary"}]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.embedder = mock_embedder_fail
            collector.config = mock_config

            result = collector._embed(items)

        # Item should still be present but with None embedding
        assert len(result) == 1
        assert result[0]["embedding"] is None


class TestScoring:
    """Tests for score calculation"""

    @patch("scripts.daily_collector.get_config")
    def test_score_adds_score_to_items(self, mock_get_config, mock_config, sample_item):
        """Test that score is added to items"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        mock_scorer = MagicMock()
        mock_scorer.score.return_value = ContentScore(
            novelty=0.8, relevance=0.7, quality=0.6, total=0.7
        )

        items = [sample_item.copy()]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.scorer = mock_scorer
            collector._existing_embeddings = []
            collector.config = mock_config

            result = collector._score(items)

        assert len(result) == 1
        assert "score" in result[0]
        assert "total" in result[0]["score"]

    @patch("scripts.daily_collector.get_config")
    def test_score_sorts_by_total(self, mock_get_config, mock_config):
        """Test that items are sorted by total score"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        mock_scorer = MagicMock()

        # Create items with different scores
        items = [
            {"title": "Low Score", "embedding": [0.1] * 1024},
            {"title": "High Score", "embedding": [0.2] * 1024},
        ]

        # Mock scorer to return different scores
        mock_scorer.score.side_effect = [
            ContentScore(novelty=0.5, relevance=0.5, quality=0.5, total=0.5),
            ContentScore(novelty=0.9, relevance=0.9, quality=0.9, total=0.9),
        ]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.scorer = mock_scorer
            collector._existing_embeddings = []
            collector.config = mock_config

            result = collector._score(items)

        # Higher score should be first
        assert result[0]["score"]["total"] >= result[1]["score"]["total"]


class TestDateParsing:
    """Tests for date parsing"""

    @patch("scripts.daily_collector.get_config")
    def test_parse_date_valid_rfc2822(self, mock_get_config, mock_config):
        """Test parsing RFC2822 date format"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        date_str = "Mon, 17 Feb 2026 10:00:00 +0000"

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config

            result = collector._parse_date(date_str)

        assert result == "2026-02-17"

    @patch("scripts.daily_collector.get_config")
    def test_parse_date_empty(self, mock_get_config, mock_config):
        """Test parsing empty date string"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config

            result = collector._parse_date("")

        # Should return today's date
        assert result == datetime.now().strftime("%Y-%m-%d")


class TestIngest:
    """Tests for source ingestion"""

    @patch("scripts.daily_collector.get_config")
    def test_ingest_filters_disabled_sources(self, mock_get_config, mock_config):
        """Test that disabled sources are skipped"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Add disabled source
        mock_config.sources["sources"].append(
            {
                "id": "disabled_source",
                "url": "https://disabled.com/feed",
                "enabled": False,
            }
        )

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config
            collector._fetch_rss = MagicMock(return_value=[{"title": "Test"}])

            result = collector._ingest()

        # Should only have items from enabled source
        for item in result:
            assert item.get("source_id") != "disabled_source"

    @patch("scripts.daily_collector.get_config")
    def test_ingest_respects_source_filter(self, mock_get_config, mock_config):
        """Test that source filter works"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config
            collector._fetch_rss = MagicMock(
                return_value=[{"title": "Test", "source_id": "test_source"}]
            )

            result = collector._ingest(source_filter=["test_source"])

        # Should have processed items (only filtered source)
        assert len(result) > 0
        # Should only contain items from filtered source
        for item in result:
            assert item.get("source_id") in ["test_source", None]  # source_id from mock


class TestRun:
    """Tests for full pipeline run"""

    @patch("scripts.daily_collector.get_config")
    def test_run_dry_run_skips_export(self, mock_get_config, mock_config):
        """Test that dry run skips export"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.dry_run = True
            collector.config = mock_config
            collector._ingest = MagicMock(return_value=[{"title": "Test"}])
            collector._dedupe = MagicMock(side_effect=lambda x: x)
            collector._fetch = MagicMock(side_effect=lambda x: x)
            collector._nlp_process = MagicMock(side_effect=lambda x: x)
            collector._embed = MagicMock(side_effect=lambda x: x)
            collector._score = MagicMock(side_effect=lambda x: x)
            collector._export = MagicMock()
            collector._create_digest = MagicMock()

            result = collector.run(date="2026-02-17")

        # Export should not be called in dry run
        collector._export.assert_not_called()
        assert result["date"] == "2026-02-17"

    @patch("scripts.daily_collector.get_config")
    def test_run_returns_results(self, mock_get_config, mock_config):
        """Test that run returns proper results"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.dry_run = True
            collector.config = mock_config
            collector._ingest = MagicMock(return_value=[{"title": "Test"}])
            collector._dedupe = MagicMock(side_effect=lambda x: x)
            collector._fetch = MagicMock(side_effect=lambda x: x)
            collector._nlp_process = MagicMock(side_effect=lambda x: x)
            collector._embed = MagicMock(side_effect=lambda x: x)
            collector._score = MagicMock(side_effect=lambda x: x)

            result = collector.run(date="2026-02-17")

        assert "date" in result
        assert "collected" in result
        assert "processed" in result
        assert "exported" in result
        assert "errors" in result
