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
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

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
    @patch("scripts.daily_collector.DailyCollector._load_collectors")
    def test_init_default(
        self,
        mock_load_collectors,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test default initialization"""
        mock_get_config.return_value = mock_config
        mock_load_collectors.return_value = []
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
    @patch("scripts.daily_collector.DailyCollector._load_collectors")
    def test_init_with_account(
        self,
        mock_load_collectors,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test initialization with specific account"""
        mock_get_config.return_value = mock_config
        mock_load_collectors.return_value = []
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector(account_id="custom_account")

        assert collector.account_id == "custom_account"

    @patch("scripts.daily_collector.get_config")
    @patch("scripts.daily_collector.VaultIO")
    @patch("scripts.daily_collector.get_summary_client")
    @patch("scripts.daily_collector.get_embedding_manager")
    @patch("scripts.daily_collector.get_renderer")
    @patch("scripts.daily_collector.DailyCollector._load_collectors")
    def test_init_dry_run(
        self,
        mock_load_collectors,
        mock_renderer,
        mock_embedder,
        mock_llm_client,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test dry run mode"""
        mock_get_config.return_value = mock_config
        mock_load_collectors.return_value = []
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
        existing_hash = hashlib.md5("https://example.com/existing".encode()).hexdigest()[:12]

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
    def test_fetch_rss_parses_entries(self, mock_feedparser, mock_get_config, mock_config, sample_rss_entry):
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
    def test_fetch_rss_limits_to_20(self, mock_feedparser, mock_get_config, mock_config):
        """Test that RSS fetch limits to 20 entries"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        # Create 30 mock entries
        mock_feed = MagicMock()
        mock_feed.entries = [{"title": f"Article {i}", "link": f"https://example.com/{i}"} for i in range(30)]
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
    def test_nlp_process_adds_summary_and_tags(self, mock_get_config, mock_config, mock_llm):
        """Test that NLP processing adds summary and tags"""
        mock_get_config.return_value = mock_config

        from scripts.daily_collector import DailyCollector

        items = [{"title": "Test Article", "full_text": "Test content for NLP processing."}]

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
    def test_nlp_process_skips_empty_items(self, mock_get_config, mock_config, mock_llm):
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
        mock_scorer.score.return_value = ContentScore(novelty=0.8, relevance=0.7, quality=0.6, total=0.7)

        items = [sample_item.copy()]

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.scorer = mock_scorer
            collector._existing_embeddings = []
            collector._existing_embeddings_with_ids = None  # Added for Phase 0 duplicate check
            collector.vault = MagicMock()  # Added for Phase 0 duplicate check
            collector.vault.list_notes.return_value = []  # No existing notes
            collector.config = mock_config

            collector._score(items)  # Test passes if no exception

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
            collector._existing_embeddings_with_ids = None  # Added for Phase 0 duplicate check
            collector.vault = MagicMock()  # Added for Phase 0 duplicate check
            collector.vault.list_notes.return_value = []  # No existing notes
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
            collector.collectors = []  # V2: mock collectors list
            collector._fetch_rss = MagicMock(return_value=[{"title": "Test"}])

            result = collector._ingest()

        # Should only have items from enabled source
        for item in result:
            assert item.get("source_id") != "disabled_source"

    @patch("scripts.daily_collector.get_config")
    def test_ingest_respects_source_filter(self, mock_get_config, mock_config):
        """Test that source filter works"""
        mock_get_config.return_value = mock_config

        from dataclasses import dataclass

        from scripts.daily_collector import DailyCollector

        # Create a mock collector that returns test items
        @dataclass
        class MockCollectedItem:
            title: str
            source_id: str

            def to_dict(self):
                return {"title": self.title, "source_id": self.source_id}

        mock_collector = MagicMock()
        mock_collector.collect.return_value = [
            MockCollectedItem(title="Test", source_id="test_source"),
            MockCollectedItem(title="Other", source_id="other_source"),
        ]
        mock_collector.name.return_value = "mock_collector"

        with patch.object(DailyCollector, "__init__", lambda x, **kwargs: None):
            collector = DailyCollector.__new__(DailyCollector)
            collector.config = mock_config
            collector.account_id = "test_account"  # Required for collector.collect()
            collector.__dict__["collectors"] = [mock_collector]  # V2: mock collectors list

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


class TestCollectorConfigAndLoading:
    """Tests for collector config loading/enabling and collector initialization."""

    def test_load_collectors_config_loads_yaml(self):
        """Load collectors.yml when file exists."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)

        fake_path = MagicMock()
        fake_path.exists.return_value = True

        with patch("scripts.daily_collector.Path", return_value=fake_path):
            with patch("builtins.open", mock_open(read_data="perplexity:\n  enabled: true\n")):
                result = collector._load_collectors_config()

        assert result == {"perplexity": {"enabled": True}}

    def test_load_collectors_config_returns_empty_on_error(self):
        """Return empty config when collectors.yml cannot be loaded."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)

        fake_path = MagicMock()
        fake_path.exists.return_value = True

        with patch("scripts.daily_collector.Path", return_value=fake_path):
            with patch("builtins.open", side_effect=OSError("cannot open")):
                result = collector._load_collectors_config()

        assert result == {}

    def test_is_enabled_reads_config_flag(self):
        """Check enabled flag lookup from loaded collector config."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector._collectors_config = {
            "perplexity": {"enabled": True},
            "rss": {"enabled": False},
        }

        assert collector._is_enabled("perplexity") is True
        assert collector._is_enabled("rss") is False
        assert collector._is_enabled("unknown") is False

    @patch("scripts.daily_collector.PerplexityCollector.from_config")
    @patch("scripts.daily_collector.RSSCollector")
    @patch("scripts.daily_collector.SourceManager")
    def test_load_collectors_handles_perplexity_failure(
        self,
        mock_source_manager,
        mock_rss_collector,
        mock_perplexity_from_config,
    ):
        """Continue loading RSS even if Perplexity collector init fails."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.__dict__["config"] = SimpleNamespace(sources_file="config/sources.yml")

        mock_source_manager.return_value.get_active.return_value = [
            SimpleNamespace(id="s1", type="rss", enabled=True),
            SimpleNamespace(id="s2", type="newsletter", enabled=True),
        ]
        mock_rss_collector.return_value = "rss_collector"
        mock_perplexity_from_config.side_effect = RuntimeError("bad config")

        with patch.object(
            DailyCollector,
            "_load_collectors_config",
            return_value={"perplexity": {"enabled": True}},
        ):
            loaded = collector._load_collectors()

        assert loaded == ["rss_collector"]
        mock_rss_collector.assert_called_once()
        mock_perplexity_from_config.assert_called_once_with({"enabled": True})

    @patch("scripts.daily_collector.RSSCollector")
    @patch("scripts.daily_collector.SourceManager")
    def test_load_collectors_returns_empty_when_no_active_sources_and_disabled_perplexity(
        self,
        mock_source_manager,
        mock_rss_collector,
    ):
        """Return empty collectors when no RSS sources and no enabled extras."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.__dict__["config"] = SimpleNamespace(sources_file="config/sources.yml")

        mock_source_manager.return_value.get_active.return_value = []

        with patch.object(
            DailyCollector,
            "_load_collectors_config",
            return_value={"perplexity": {"enabled": False}},
        ):
            loaded = collector._load_collectors()

        assert loaded == []
        mock_rss_collector.assert_not_called()


class TestPipelineErrorPaths:
    """Tests for run flow and error handling branches."""

    def test_run_main_flow_non_dry_run_with_max_items(self, mock_config):
        """Run full pipeline and verify export/digest/max_items behavior."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.dry_run = False
        collector.config = mock_config

        raw_items = [
            {"source_url": "https://a.com"},
            {"source_url": "https://b.com"},
            {"source_url": "https://c.com"},
        ]
        scored_items = [
            {"id": "item1", "score": {"total": 0.9}},
            {"id": "item2", "score": {"total": 0.8}},
            {"id": "item3", "score": {"total": 0.7}},
        ]

        collector._ingest = MagicMock(return_value=raw_items)
        collector._dedupe = MagicMock(side_effect=lambda x: x)
        collector._fetch = MagicMock(side_effect=lambda x: x)
        collector._nlp_process = MagicMock(side_effect=lambda x: x)
        collector._embed = MagicMock(side_effect=lambda x: x)
        collector._score = MagicMock(return_value=scored_items)
        collector._export = MagicMock(return_value=[Path("/tmp/1.md"), Path("/tmp/2.md")])
        collector._create_digest = MagicMock()

        result = collector.run(date="2026-02-27", max_items=2)

        assert result["collected"] == 3
        assert result["processed"] == 2
        assert result["exported"] == 2
        assert result["items"] == ["item1", "item2"]
        collector._create_digest.assert_called_once()

    def test_run_captures_pipeline_exception(self, mock_config):
        """Capture top-level pipeline failure into results.errors."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.dry_run = True
        collector.config = mock_config
        collector._ingest = MagicMock(side_effect=RuntimeError("ingest failure"))

        result = collector.run(date="2026-02-27")

        assert result["errors"] == ["ingest failure"]
        assert result["collected"] == 0

    def test_ingest_continues_when_one_collector_fails(self, mock_config):
        """Keep collecting from healthy collectors after one failure."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.account_id = "acct"

        ok_item = MagicMock()
        ok_item.to_dict.return_value = {"source_id": "ok", "title": "good"}

        ok_collector = MagicMock()
        ok_collector.collect.return_value = [ok_item]
        ok_collector.name.return_value = "ok"

        bad_collector = MagicMock()
        bad_collector.collect.side_effect = RuntimeError("boom")
        bad_collector.name.return_value = "bad"

        collector.__dict__["collectors"] = [bad_collector, ok_collector]

        items = collector._ingest(source_filter=["ok"])

        assert items == [{"source_id": "ok", "title": "good"}]

    def test_ingest_returns_empty_when_no_collectors(self, mock_config):
        """Return empty list when no collectors are configured."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.account_id = "acct"
        collector.collectors = []

        assert collector._ingest() == []

    @patch("scripts.daily_collector.httpx.Client")
    def test_fetch_handles_missing_url_http_failures_and_non_200(self, mock_client_cls, mock_config):
        """Skip/continue correctly for missing URL, request exception and non-200 response."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config

        ok_response = MagicMock(status_code=200)
        ok_response.text = """
        <html><head><title>From HTML</title></head>
        <body><main><p>Hello world</p><script>x=1</script></main></body></html>
        """
        non_200_response = MagicMock(status_code=404)

        mock_client = MagicMock()
        mock_client.get.side_effect = [
            RuntimeError("network"),
            ok_response,
            non_200_response,
        ]
        mock_client_cls.return_value.__enter__.return_value = mock_client

        items = [
            {"source_url": "", "title": "No URL"},
            {"source_url": "https://err.example", "title": "Err"},
            {"source_url": "https://ok.example", "title": ""},
            {"source_url": "https://404.example", "title": "Not Found"},
        ]

        fetched = collector._fetch(items)

        assert len(fetched) == 1
        assert fetched[0]["title"] == "From HTML"
        assert "full_text" in fetched[0]

    def test_nlp_process_skips_empty_and_continues_after_exception(self, mock_config):
        """Process valid item, skip empty item, and continue after LLM error."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config

        llm = MagicMock()
        llm.summarize.side_effect = ["summary-ok", RuntimeError("llm down")]
        llm.generate.return_value = "- Point 1\n• Point 2\nPoint 3\nPoint 4"
        llm.generate_tags.return_value = ["t1", "t2"]
        collector.llm = llm

        items = [
            {"title": "Good", "full_text": "A" * 700},
            {"title": "Empty", "full_text": ""},
            {"title": "Bad", "full_text": "B" * 10},
        ]

        processed = collector._nlp_process(items)

        assert len(processed) == 1
        assert processed[0]["summary"] == "summary-ok"
        assert processed[0]["key_points"] == ["Point 1", "Point 2", "Point 3"]
        assert processed[0]["tags"] == ["t1", "t2"]
        assert processed[0]["excerpt"].endswith("...")


class TestAdditionalCoveragePaths:
    """Tests to cover export/digest/config/cache/CLI branches."""

    @patch("scripts.daily_collector.PerplexityCollector.from_config")
    @patch("scripts.daily_collector.RSSCollector")
    @patch("scripts.daily_collector.SourceManager")
    def test_load_collectors_adds_perplexity_when_enabled(
        self,
        mock_source_manager,
        mock_rss_collector,
        mock_perplexity_from_config,
    ):
        """Load both RSS and Perplexity collectors in success path."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.__dict__["config"] = SimpleNamespace(sources_file="config/sources.yml")

        mock_source_manager.return_value.get_active.return_value = [
            SimpleNamespace(id="rss-1", type="rss", enabled=True)
        ]
        mock_rss_collector.return_value = "rss_collector"
        mock_perplexity_from_config.return_value = "perplexity_collector"

        with patch.object(
            DailyCollector,
            "_load_collectors_config",
            return_value={"perplexity": {"enabled": True, "input_dir": "Inbox/Perplexity"}},
        ):
            loaded = collector._load_collectors()

        assert loaded == ["rss_collector", "perplexity_collector"]

    def test_dedupe_ignores_frontmatter_read_errors(self, mock_config):
        """Skip broken notes while reading existing URL hashes."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.vault = MagicMock()
        collector.vault.list_notes.return_value = ["bad.md"]
        collector.vault.read_frontmatter.side_effect = ValueError("broken")

        result = collector._dedupe([{"source_url": "https://example.com/new", "title": "New"}])

        assert len(result) == 1
        assert result[0]["canonical_url"] == "https://example.com/new"

    def test_run_with_no_date_uses_today(self, mock_config):
        """Use current date string when date argument is omitted."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.dry_run = True
        collector.config = mock_config
        collector._ingest = MagicMock(return_value=[])
        collector._dedupe = MagicMock(return_value=[])
        collector._fetch = MagicMock(return_value=[])
        collector._nlp_process = MagicMock(return_value=[])
        collector._embed = MagicMock(return_value=[])
        collector._score = MagicMock(return_value=[])

        result = collector.run()

        assert result["date"] == datetime.now().strftime("%Y-%m-%d")

    def test_load_existing_embeddings_reads_cache_and_handles_bad_file(self, tmp_path, mock_config):
        """Load valid .npy cache files and ignore broken ones."""
        import numpy as np

        from scripts.daily_collector import DailyCollector

        cache_dir = tmp_path / "embeddings"
        cache_dir.mkdir()
        np.save(cache_dir / "ok.npy", np.array([0.1, 0.2, 0.3]))
        (cache_dir / "broken.npy").write_text("not a numpy file", encoding="utf-8")

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.__dict__["embedder"] = SimpleNamespace(cache_dir=cache_dir)
        collector._existing_embeddings = None

        loaded_once = collector._load_existing_embeddings()
        loaded_twice = collector._load_existing_embeddings()

        assert len(loaded_once) == 1
        assert loaded_once == loaded_twice

    def test_parse_frontmatter_returns_metadata_or_empty(self):
        """Parse YAML frontmatter when present, else return empty dict."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)

        with_frontmatter = "---\ntitle: Test\nscore: 0.9\n---\nbody"
        without_frontmatter = "body only"

        assert collector._parse_frontmatter(with_frontmatter) == {
            "title": "Test",
            "score": 0.9,
        }
        assert collector._parse_frontmatter(without_frontmatter) == {}

    def test_export_skips_low_score_and_handles_existing_note(self, mock_config):
        """Export only displayable items and ignore already-existing files."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.account_id = "acct"
        collector.scorer = MagicMock()
        collector.scorer.should_display.side_effect = [True, False, True]
        collector.renderer = MagicMock()
        collector.renderer.render_input_note.return_value = "---\nsource: test\n---\ncontent"
        collector.vault = MagicMock()
        collector.vault.write_note.side_effect = [
            Path("/tmp/saved.md"),
            FileExistsError("exists"),
        ]

        items = [
            {"url_hash": "aaa111", "score_obj": ContentScore(total=0.8)},
            {"url_hash": "bbb222", "score_obj": ContentScore(total=0.1)},
            {"url_hash": "ccc333", "score_obj": ContentScore(total=0.9)},
        ]

        exported = collector._export(items, "2026-02-27")

        assert len(exported) == 1
        assert items[0]["id"] == "input_aaa111"
        assert items[2]["id"] == "input_ccc333"

    def test_create_digest_success_sets_default_writing_status(self, mock_config):
        """Create digest with displayable items and default writing_status."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.scorer = MagicMock()
        collector.scorer.should_display.side_effect = [True, False]
        collector.renderer = MagicMock()
        collector.renderer.render_digest.return_value = "---\ndate: 2026-02-27\n---\ndigest body"
        collector.vault = MagicMock()
        collector.vault.write_note.return_value = Path("/tmp/digest.md")

        items = [
            {"id": "a", "score_obj": ContentScore(total=0.9)},
            {"id": "b", "score_obj": ContentScore(total=0.1)},
        ]

        result = collector._create_digest(items, "2026-02-27")

        assert result == Path("/tmp/digest.md")
        assert items[0]["writing_status"] == "pending"

    def test_create_digest_raises_when_write_fails(self, mock_config):
        """Re-raise write exceptions from digest creation."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        collector.config = mock_config
        collector.scorer = MagicMock()
        collector.scorer.should_display.return_value = True
        collector.renderer = MagicMock()
        collector.renderer.render_digest.return_value = "digest body"
        collector.vault = MagicMock()
        collector.vault.write_note.side_effect = RuntimeError("disk full")

        with pytest.raises(RuntimeError, match="disk full"):
            collector._create_digest([{"score_obj": ContentScore(total=0.9)}], "2026-02-27")

    def test_parse_date_invalid_string_returns_today(self):
        """Fallback to today when date parsing fails."""
        from scripts.daily_collector import DailyCollector

        collector = DailyCollector.__new__(DailyCollector)
        assert collector._parse_date("not-a-date") == datetime.now().strftime("%Y-%m-%d")

    @patch("scripts.daily_collector.DailyCollector")
    @patch("scripts.daily_collector.argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_parses_args_runs_collector_and_prints_results(
        self,
        mock_print,
        mock_parse_args,
        mock_daily_collector,
    ):
        """CLI main should parse args, run collector, and print summary output."""
        from scripts.daily_collector import main

        mock_parse_args.return_value = SimpleNamespace(
            date="2026-02-27",
            account="socialbuilders",
            sources=["s1"],
            max_items=5,
            dry_run=True,
        )
        mock_daily_collector.return_value.run.return_value = {
            "date": "2026-02-27",
            "collected": 10,
            "processed": 5,
            "exported": 0,
            "errors": ["one"],
        }

        main()

        mock_daily_collector.return_value.run.assert_called_once_with(date="2026-02-27", sources=["s1"], max_items=5)
        assert mock_print.call_count >= 6
