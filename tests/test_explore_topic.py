"""
Unit tests for scripts/explore_topic.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from explore_topic import TopicExplorer  # noqa: E402


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.vault.inbox = "/vault/Inbox/Inputs"
    config.vault.digests = "/vault/Inbox/Inputs/_digests"
    config.vault.explorations = "/vault/Explorations"
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    return vault


@pytest.fixture
def mock_llm():
    """Mock LLM client"""
    llm = MagicMock()
    llm.generate.return_value = """[주제 확장]
Extended topic analysis content here.

[관련 논의와 반론]
Related discussions and counterarguments.

[독자 인사이트]
Reader insights and perspectives.

[롱폼 작성 가이드]
Writing guide for longform content."""
    return llm


@pytest.fixture
def mock_prompt_loader():
    """Mock prompt loader"""
    loader = MagicMock()
    loader.get_exploration_prompt.return_value = "Exploration prompt for: {title}"
    return loader


@pytest.fixture
def mock_renderer():
    """Mock template renderer"""
    renderer = MagicMock()
    renderer.render_exploration.return_value = """---
id: explore_test123
source_input_id: test123
title: Test Title
tags: [AI, ML]
---
# Exploration Content"""
    return renderer


@pytest.fixture
def sample_digest_content():
    """Sample digest markdown content"""
    return """---
date: "2026-02-15"
---

## [x] Approved Item 1

**ID**: input_abc123
**Score**: 0.85

Summary of the first approved item.

## [ ] Pending Item 2

**ID**: input_def456
**Score**: 0.75

This item is not checked.

## [x] Approved Item 2

**ID**: input_xyz789
**Score**: 0.90

Another approved item.
"""


@pytest.fixture
def sample_input_note():
    """Sample input note content"""
    return """---
title: AI Trends 2026
tags: [AI, ML, Tech]
writing_status: auto_ready
score: 0.85
---

## 요약

This is a summary of AI trends.

## 핵심 포인트

- LLM 모델의 성능 향상
- 멀티모달 AI의 등장
- 에너지 효율성 개선

## 원문 발췌

Original excerpt from the article.
"""


class TestTopicExplorerInit:
    """Test TopicExplorer initialization"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_init_default(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test default initialization"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()

        assert explorer.config == mock_config
        assert explorer.dry_run is False

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_init_dry_run(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test initialization with dry_run"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer(dry_run=True)

        assert explorer.dry_run is True


class TestTopicExplorerCollectTargets:
    """Test _collect_targets method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_collect_targets_with_input_id(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test collecting targets with specific input_id"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        targets = explorer._collect_targets("2026-02-15", "input_abc123")

        assert len(targets) == 1
        assert targets[0]["input_id"] == "input_abc123"
        assert targets[0]["account_id"] is None


class TestTopicExplorerParseDigest:
    """Test _parse_digest_for_exploration method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_digest_extracts_checked_items(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
        sample_digest_content,
    ):
        """Test parsing digest extracts only checked items"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = ({}, sample_digest_content)
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        targets = explorer._parse_digest_for_exploration("2026-02-15")

        # Should extract 2 checked items (input_abc123 and input_xyz789)
        assert len(targets) == 2
        input_ids = [t["input_id"] for t in targets]
        assert "input_abc123" in input_ids
        assert "input_xyz789" in input_ids
        assert "input_def456" not in input_ids  # Not checked

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_digest_file_not_found(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing when digest file not found"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.side_effect = FileNotFoundError("Not found")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        targets = explorer._parse_digest_for_exploration("2026-02-15")

        assert targets == []

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_digest_empty(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing empty digest"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = ({}, "---\ndate: '2026-02-15'\n---\n")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        targets = explorer._parse_digest_for_exploration("2026-02-15")

        assert targets == []


class TestTopicExplorerLoadInput:
    """Test _load_input method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_load_input_success(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
        sample_input_note,
    ):
        """Test loading input note successfully"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = (
            {"title": "AI Trends 2026", "tags": ["AI", "ML"], "writing_status": "auto_ready"},
            sample_input_note.split("---\n")[2],  # Body content
        )
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        result = explorer._load_input("test123")

        assert result is not None
        assert result["id"] == "test123"
        assert result["title"] == "AI Trends 2026"
        assert result["writing_status"] == "auto_ready"
        assert "AI" in result["tags"]

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_load_input_not_found(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test loading nonexistent input"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.side_effect = FileNotFoundError("Not found")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        result = explorer._load_input("nonexistent")

        assert result is None


class TestTopicExplorerExtractSection:
    """Test _extract_section method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_extract_section_found(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test extracting existing section"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = """## 요약
This is the summary section.

## 핵심 포인트
- Point 1
- Point 2
"""

        explorer = TopicExplorer()
        result = explorer._extract_section(content, "요약")

        assert "This is the summary section" in result
        assert "핵심 포인트" not in result

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_extract_section_not_found(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test extracting nonexistent section"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = "## Other Section\nContent here."

        explorer = TopicExplorer()
        result = explorer._extract_section(content, "nonexistent")

        assert result == ""


class TestTopicExplorerExtractList:
    """Test _extract_list method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_extract_list_dash_items(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test extracting list with dash items"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = """## 핵심 포인트

- Point one
- Point two
- Point three
"""

        explorer = TopicExplorer()
        result = explorer._extract_list(content, "핵심 포인트")

        assert len(result) == 3
        assert "Point one" in result
        assert "Point two" in result

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_extract_list_asterisk_items(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test extracting list with asterisk items"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = """## Items

* First item
* Second item
"""

        explorer = TopicExplorer()
        result = explorer._extract_list(content, "Items")

        assert len(result) == 2
        assert "First item" in result


class TestTopicExplorerParseExplorationSections:
    """Test _parse_exploration_sections method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_sections_bracket_format(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing sections in [section name] format"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        text = """[주제 확장]
This is the topic expansion content.
Multiple lines here.

[관련 논의와 반론]
Discussion content.

[독자 인사이트]
Insights content.

[롱폼 작성 가이드]
Writing guide content.
"""

        explorer = TopicExplorer()
        result = explorer._parse_exploration_sections(text)

        assert "주제 확장" in result
        assert "관련 논의와 반론" in result
        assert "독자 인사이트" in result
        assert "롱폼 작성 가이드" in result
        assert "topic expansion content" in result["주제 확장"]

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_sections_empty(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing empty text"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        result = explorer._parse_exploration_sections("")

        assert result == {}


class TestTopicExplorerExplorationExists:
    """Test _exploration_exists method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_exploration_exists_true(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test when exploration exists"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = ({}, "content")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        result = explorer._exploration_exists("/path/to/exploration.md")

        assert result is True

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_exploration_exists_false(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test when exploration does not exist"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.side_effect = FileNotFoundError("Not found")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        result = explorer._exploration_exists("/path/to/exploration.md")

        assert result is False


class TestTopicExplorerParseFrontmatter:
    """Test _parse_frontmatter method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_frontmatter_valid(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing valid frontmatter"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = """---
id: explore_test
title: Test Title
tags:
  - AI
  - ML
---

# Content here"""

        explorer = TopicExplorer()
        result = explorer._parse_frontmatter(content)

        assert result["id"] == "explore_test"
        assert result["title"] == "Test Title"
        assert "AI" in result["tags"]

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_parse_frontmatter_no_frontmatter(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test parsing content without frontmatter"""
        mock_get_config.return_value = mock_config
        mock_vault_io.return_value = MagicMock()
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        content = "# Just content\n\nNo frontmatter here."

        explorer = TopicExplorer()
        result = explorer._parse_frontmatter(content)

        assert result == {}


class TestTopicExplorerProcessTarget:
    """Test _process_target method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_process_target_skips_manual_status(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test that manual writing_status items are skipped"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = (
            {"title": "Test", "writing_status": "manual"},
            "content",
        )
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer(dry_run=True)
        results = {"explored_count": 0, "skipped_count": 0, "errors": []}

        explorer._process_target(
            {"input_id": "test123", "account_id": None},
            force=False,
            results=results,
        )

        assert results["skipped_count"] == 1
        assert results["explored_count"] == 0

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_process_target_skips_completed_status(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test that completed writing_status items are skipped"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = (
            {"title": "Test", "writing_status": "completed"},
            "content",
        )
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer(dry_run=True)
        results = {"explored_count": 0, "skipped_count": 0, "errors": []}

        explorer._process_target(
            {"input_id": "test123", "account_id": None},
            force=False,
            results=results,
        )

        assert results["skipped_count"] == 1

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_process_target_skips_existing_exploration(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test that existing explorations are skipped (unless forced)"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        # First call checks exploration exists, second loads input
        mock_vault.read_note.side_effect = [
            ({}, "existing exploration"),  # Exploration exists
        ]
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer(dry_run=True)
        results = {"explored_count": 0, "skipped_count": 0, "errors": []}

        explorer._process_target(
            {"input_id": "test123", "account_id": None},
            force=False,
            results=results,
        )

        assert results["skipped_count"] == 1


class TestTopicExplorerRun:
    """Test run method"""

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_run_with_date(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test run with specific date"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = ({}, "")  # Empty digest
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        results = explorer.run(date="2026-02-15")

        assert results["date"] == "2026-02-15"
        assert "explored_count" in results
        assert "skipped_count" in results
        assert "errors" in results

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_run_with_input_id(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
        mock_llm,
    ):
        """Test run with specific input_id"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.return_value = (
            {"title": "Test", "writing_status": "auto_ready", "tags": []},
            "## 요약\nSummary\n## 핵심 포인트\n- Point 1",
        )
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = mock_llm
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer(dry_run=True)
        results = explorer.run(input_id="test123")

        assert results["date"] is not None  # Should have today's date

    @patch("explore_topic.get_config")
    @patch("explore_topic.VaultIO")
    @patch("explore_topic.get_summary_client")
    @patch("explore_topic.get_prompt_loader")
    @patch("explore_topic.get_renderer")
    def test_run_handles_exception(
        self,
        mock_get_renderer,
        mock_get_prompt_loader,
        mock_get_summary_client,
        mock_vault_io,
        mock_get_config,
        mock_config,
    ):
        """Test run handles exceptions gracefully"""
        mock_get_config.return_value = mock_config
        mock_vault = MagicMock()
        mock_vault.read_note.side_effect = Exception("Unexpected error")
        mock_vault_io.return_value = mock_vault
        mock_get_summary_client.return_value = MagicMock()
        mock_get_prompt_loader.return_value = MagicMock()
        mock_get_renderer.return_value = MagicMock()

        explorer = TopicExplorer()
        results = explorer.run(date="2026-02-15", input_id="test123")

        assert len(results["errors"]) > 0
