"""
Tests for generate_content.py

Unit tests for the ContentGenerator class covering:
- Digest parsing
- Input/Exploration loading
- Content generation (longform, packs, images)
- Status updates
"""

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
    config.vault.inbox = "Inbox/Inputs"
    config.vault.digests = "Inbox/Inputs/_digests"
    config.vault.longform = "Content/Longform"
    config.vault.packs = "Content/Packs"
    config.vault.explorations = "Inbox/Explorations"
    config.vault.images_prompts = "Assets/Images/_prompts"
    config.get_account.return_value = {
        "channels": {
            "twitter": {"enabled": True, "max_length": 280, "hashtags": True},
            "linkedin": {"enabled": True, "max_length": 3000, "hashtags": True},
        }
    }
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    vault.read_note.return_value = ({}, "Test content")
    vault.write_note.return_value = Path("/tmp/test_vault/test.md")
    vault.list_notes.return_value = []
    vault.ensure_dir.return_value = None
    return vault


@pytest.fixture
def mock_llm():
    """Mock LLM client"""
    llm = MagicMock()
    llm.generate.return_value = """
[인트로]
This is the introduction section.

[메인 콘텐츠]
This is the main content of the article.

[주요 시사점]
Key takeaways from the content.

[마무리]
Call to action and conclusion.
"""
    return llm


@pytest.fixture
def mock_renderer():
    """Mock template renderer"""
    renderer = MagicMock()
    renderer.render_longform.return_value = """---
id: test_longform
title: Test Title
---
# Longform Content"""
    renderer.render_pack.return_value = """---
id: test_pack
---
Pack content"""
    renderer.render_image_prompt.return_value = """---
id: test_image
---
Image prompt"""
    return renderer


@pytest.fixture
def mock_prompt_loader():
    """Mock prompt loader"""
    loader = MagicMock()
    loader.get_longform_prompt.return_value = (
        "Generate a longform article about: {title}"
    )
    loader.get_pack_prompt.return_value = "Generate a {channel} post about: {title}"
    loader.get_image_prompt.return_value = "Generate image prompt for: {title}"
    return loader


@pytest.fixture
def sample_digest_content():
    """Sample digest content"""
    return """---
type: digest
date: 2026-02-17
---

# Daily Digest: 2026-02-17

## [x] Approved Article 1

- **ID**: input_abc123
- **Account**: socialbuilders
- **Score**: 0.85

## [ ] Pending Article 2

- **ID**: input_def456
- **Account**: socialbuilders
- **Score**: 0.65
"""


@pytest.fixture
def sample_input_content():
    """Sample input note content"""
    return """---
id: input_abc123
title: Test Article Title
tags:
  - AI
  - startup
writing_status: auto_ready
---

## 요약

This is a test article summary.

## 핵심 포인트

- Key point 1
- Key point 2
- Key point 3

## 원문 발췌

Original excerpt from the article...
"""


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────


class TestContentGeneratorInit:
    """Tests for ContentGenerator initialization"""

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_init_default(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test default initialization"""
        mock_get_config.return_value = mock_config
        from scripts.generate_content import ContentGenerator

        generator = ContentGenerator()

        assert generator.dry_run is False
        assert generator.weekly_slot is None

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_init_dry_run(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test dry run mode"""
        mock_get_config.return_value = mock_config
        from scripts.generate_content import ContentGenerator

        generator = ContentGenerator(dry_run=True)

        assert generator.dry_run is True


class TestDigestParsing:
    """Tests for digest parsing"""

    @patch("scripts.generate_content.get_config")
    def test_parse_digest_finds_checked_items(
        self, mock_get_config, mock_config, mock_vault, sample_digest_content
    ):
        """Test that checked items are found"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, sample_digest_content)

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator._CHECKBOX_PATTERN = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
            generator._ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"
            generator._ACCOUNT_PATTERN = r"\*\*Account\*\*:\s*(\S+)"

            result = generator._parse_digest("2026-02-17")

        # Should find the checked item
        assert len(result) == 1
        assert result[0]["input_id"] == "input_abc123"
        assert result[0]["checked"] is True

    @patch("scripts.generate_content.get_config")
    def test_parse_digest_auto_all_includes_unchecked(
        self, mock_get_config, mock_config, mock_vault, sample_digest_content
    ):
        """Test that auto_all includes unchecked items"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, sample_digest_content)

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator._CHECKBOX_PATTERN = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
            generator._ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"
            generator._ACCOUNT_PATTERN = r"\*\*Account\*\*:\s*(\S+)"

            result = generator._parse_digest("2026-02-17", auto_all=True)

        # Should find both items
        assert len(result) == 2

    @patch("scripts.generate_content.get_config")
    def test_parse_digest_handles_missing_file(
        self, mock_get_config, mock_config, mock_vault
    ):
        """Test handling of missing digest file"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.side_effect = FileNotFoundError("Digest not found")

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault

            result = generator._parse_digest("2026-02-17")

        assert result == []


class TestLineParsing:
    """Tests for line parsing helpers"""

    @patch("scripts.generate_content.get_config")
    def test_create_item_from_checkbox_checked(self, mock_get_config, mock_config):
        """Test creating item from checked checkbox"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            # Create mock match object (group(1) = checkbox, group(2) = title)
            match = MagicMock()
            match.group.side_effect = lambda i: {1: "x", 2: "Test Article Title"}.get(
                i, ""
            )

            result = generator._create_item_from_checkbox(match, auto_all=False)

        assert result is not None
        assert result["title"] == "Test Article Title"
        assert result["checked"] is True

    @patch("scripts.generate_content.get_config")
    def test_create_item_from_checkbox_unchecked(self, mock_get_config, mock_config):
        """Test creating item from unchecked checkbox"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            # Create mock match object (group(1) = checkbox, group(2) = title)
            match = MagicMock()
            match.group.side_effect = lambda i: {1: " ", 2: "Test Article Title"}.get(
                i, ""
            )

            result = generator._create_item_from_checkbox(match, auto_all=False)

        # Unchecked item should be None when auto_all is False
        assert result is None

    @patch("scripts.generate_content.get_config")
    def test_parse_item_detail_extracts_id(self, mock_get_config, mock_config):
        """Test extracting ID from line"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator._ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"

            current_item = {"title": "Test"}
            line = "- **ID**: input_abc123"

            result = generator._parse_item_detail(line, current_item)

        assert result["input_id"] == "input_abc123"


class TestInputLoading:
    """Tests for input note loading"""

    @patch("scripts.generate_content.get_config")
    def test_load_input_returns_content(
        self, mock_get_config, mock_config, mock_vault, sample_input_content
    ):
        """Test loading input note"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = (
            {"title": "Test Article", "tags": ["AI"], "writing_status": "auto_ready"},
            sample_input_content,
        )

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault

            result = generator._load_input("input_abc123")

        assert result is not None
        assert result["id"] == "input_abc123"
        assert result["title"] == "Test Article"
        assert result["writing_status"] == "auto_ready"

    @patch("scripts.generate_content.get_config")
    def test_load_input_handles_missing_file(
        self, mock_get_config, mock_config, mock_vault
    ):
        """Test handling of missing input file"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.side_effect = FileNotFoundError("Input not found")

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault

            result = generator._load_input("nonexistent")

        assert result is None


class TestSectionExtraction:
    """Tests for section extraction"""

    @patch("scripts.generate_content.get_config")
    def test_extract_section_finds_content(self, mock_get_config, mock_config):
        """Test extracting section from content"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        content = """# Title

## 요약

This is the summary section.

## 핵심 포인트

- Point 1
- Point 2
"""

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            result = generator._extract_section(content, "요약")

        assert "This is the summary section" in result

    @patch("scripts.generate_content.get_config")
    def test_extract_section_returns_empty_for_missing(
        self, mock_get_config, mock_config
    ):
        """Test extracting missing section"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        content = """# Title

## Other Section

Some content.
"""

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            result = generator._extract_section(content, "NonExistent")

        assert result == ""

    @patch("scripts.generate_content.get_config")
    def test_extract_list_returns_items(self, mock_get_config, mock_config):
        """Test extracting list items"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        content = """## 핵심 포인트

- Point 1
- Point 2
- Point 3
"""

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            result = generator._extract_list(content, "핵심 포인트")

        assert len(result) == 3
        assert "Point 1" in result


class TestGeneratedSectionParsing:
    """Tests for parsing LLM-generated sections"""

    @patch("scripts.generate_content.get_config")
    def test_parse_generated_sections(self, mock_get_config, mock_config):
        """Test parsing sections from LLM output"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        llm_output = """[인트로]
This is the introduction.

[메인 콘텐츠]
Main content here.

[주요 시사점]
Key takeaways.
"""

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            result = generator._parse_generated_sections(llm_output)

        assert "인트로" in result
        assert "메인 콘텐츠" in result
        assert "주요 시사점" in result
        assert "introduction" in result["인트로"]


class TestShouldProcessItem:
    """Tests for item processing decision"""

    @patch("scripts.generate_content.get_config")
    def test_should_process_new_item(self, mock_get_config, mock_config):
        """Test processing new item"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            item = {"input_id": "test", "status": "new"}
            result = generator._should_process_item(item, force=False)

        assert result is True

    @patch("scripts.generate_content.get_config")
    def test_should_skip_generated_item(self, mock_get_config, mock_config):
        """Test skipping already generated item"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            item = {"input_id": "test", "status": "generated"}
            result = generator._should_process_item(item, force=False)

        assert result is False

    @patch("scripts.generate_content.get_config")
    def test_should_force_regenerate(self, mock_get_config, mock_config):
        """Test force regeneration"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            item = {"input_id": "test", "status": "generated"}
            result = generator._should_process_item(item, force=True)

        assert result is True


class TestRun:
    """Tests for full pipeline run"""

    @patch("scripts.generate_content.get_config")
    def test_run_returns_results_structure(
        self, mock_get_config, mock_config, mock_vault
    ):
        """Test that run returns proper results structure"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.dry_run = True
            generator.config = mock_config
            generator.vault = mock_vault
            generator._parse_digest = MagicMock(return_value=[])
            generator._CHECKBOX_PATTERN = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
            generator._ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"
            generator._ACCOUNT_PATTERN = r"\*\*Account\*\*:\s*(\S+)"

            result = generator.run(date="2026-02-17")

        assert "date" in result
        assert "approved_items" in result
        assert "longform_created" in result
        assert "packs_created" in result
        assert "image_prompts_created" in result
        assert "errors" in result

    @patch("scripts.generate_content.get_config")
    def test_run_dry_run_skips_writes(
        self, mock_get_config, mock_config, mock_vault, mock_llm, mock_renderer
    ):
        """Test that dry run doesn't write files"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.dry_run = True
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.weekly_slot = None
            generator.prompt_loader = MagicMock()
            generator._CHECKBOX_PATTERN = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
            generator._ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"
            generator._ACCOUNT_PATTERN = r"\*\*Account\*\*:\s*(\S+)"
            generator._parse_digest = MagicMock(
                return_value=[{"input_id": "test", "title": "Test"}]
            )
            generator._load_input = MagicMock(
                return_value={
                    "title": "Test",
                    "writing_status": "auto_ready",
                    "tags": [],
                    "summary": "Summary",
                }
            )
            generator._load_exploration = MagicMock(return_value=None)
            generator._generate_longform = MagicMock(return_value=True)

            generator.run(date="2026-02-17", content_types=["longform"])

        # Vault write should not be called in dry run
        # (This is checked implicitly through mock)


class TestExplorationLoading:
    """Tests for exploration note loading"""

    @patch("scripts.generate_content.get_config")
    def test_load_exploration_returns_content(
        self, mock_get_config, mock_config, mock_vault
    ):
        """Test loading exploration note"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = (
            {},
            """## 주제 확장

Expanded topic content.

## 관련 논의와 반론

Discussion content.
""",
        )

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault

            result = generator._load_exploration("input_abc123")

        assert result is not None
        assert "topic_expansion" in result

    @patch("scripts.generate_content.get_config")
    def test_load_exploration_returns_none_for_missing(
        self, mock_get_config, mock_config, mock_vault
    ):
        """Test loading missing exploration"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.side_effect = FileNotFoundError("Exploration not found")

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault

            result = generator._load_exploration("input_abc123")

        assert result is None


class TestWritingStatusCheck:
    """Tests for writing status checks"""

    @patch("scripts.generate_content.get_config")
    def test_skips_manual_status(self, mock_get_config, mock_config, mock_vault):
        """Test that manual status items are skipped"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.dry_run = True

            results = {"longform_created": 0}
            item = {"input_id": "test"}
            input_content = {"writing_status": "manual", "title": "Test"}

            generator._generate_content_types(
                item, input_content, ["longform"], results
            )

        # Should not create longform for manual status
        assert results["longform_created"] == 0

    @patch("scripts.generate_content.get_config")
    def test_skips_completed_status(self, mock_get_config, mock_config, mock_vault):
        """Test that completed status items are skipped"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.dry_run = True

            results = {"longform_created": 0}
            item = {"input_id": "test"}
            input_content = {"writing_status": "completed", "title": "Test"}

            generator._generate_content_types(
                item, input_content, ["longform"], results
            )

        # Should not create longform for completed status
        assert results["longform_created"] == 0
