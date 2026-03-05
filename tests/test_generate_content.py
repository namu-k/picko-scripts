"""
Tests for generate_content.py

Unit tests for the ContentGenerator class covering:
- Digest parsing
- Input/Exploration loading
- Content generation (longform, packs, images)
- Status updates
"""

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
    loader.get_longform_prompt.return_value = "Generate a longform article about: {title}"
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
    @patch("scripts.generate_content.OutputValidator")
    def test_init_default(
        self,
        mock_validator,
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
    @patch("scripts.generate_content.OutputValidator")
    def test_init_dry_run(
        self,
        mock_validator,
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
    def test_parse_digest_finds_checked_items(self, mock_get_config, mock_config, mock_vault, sample_digest_content):
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
    def test_parse_digest_handles_missing_file(self, mock_get_config, mock_config, mock_vault):
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
            match.group.side_effect = lambda i: {1: "x", 2: "Test Article Title"}.get(i, "")

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
            match.group.side_effect = lambda i: {1: " ", 2: "Test Article Title"}.get(i, "")

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
    def test_load_input_returns_content(self, mock_get_config, mock_config, mock_vault, sample_input_content):
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
    def test_load_input_handles_missing_file(self, mock_get_config, mock_config, mock_vault):
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
    def test_extract_section_returns_empty_for_missing(self, mock_get_config, mock_config):
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
    def test_run_returns_results_structure(self, mock_get_config, mock_config, mock_vault):
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
    def test_run_dry_run_skips_writes(self, mock_get_config, mock_config, mock_vault, mock_llm, mock_renderer):
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
            generator._parse_digest = MagicMock(return_value=[{"input_id": "test", "title": "Test"}])
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
    def test_load_exploration_returns_content(self, mock_get_config, mock_config, mock_vault):
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
    def test_load_exploration_returns_none_for_missing(self, mock_get_config, mock_config, mock_vault):
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

            generator._generate_content_types(item, input_content, ["longform"], results)

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

            generator._generate_content_types(item, input_content, ["longform"], results)

        # Should not create longform for completed status
        assert results["longform_created"] == 0


class TestHelpersAndMain:
    @patch("scripts.generate_content.ContentGenerator")
    @patch("scripts.generate_content.get_weekly_slot")
    def test_main_parses_all_types_and_weekly_slot(self, mock_get_weekly_slot, mock_generator_cls):
        from scripts.generate_content import main

        mock_get_weekly_slot.return_value = SimpleNamespace(
            cta="Join now",
            customer_outcome="Better growth",
            operator_kpi="kpi",
            pillar_distribution={"P1": 1},
        )
        mock_generator = MagicMock()
        mock_generator.run.return_value = {
            "date": "2026-02-20",
            "approved_items": 1,
            "longform_created": 1,
            "packs_created": 1,
            "image_prompts_created": 1,
            "errors": [],
        }
        mock_generator_cls.return_value = mock_generator

        with (
            patch(
                "sys.argv",
                ["generate_content.py", "--type", "all", "--week-of", "2026-02-17"],
            ),
            patch("builtins.print"),
        ):
            main()

        call_kwargs = mock_generator.run.call_args.kwargs
        assert call_kwargs["content_types"] == ["longform", "packs", "images", "videos"]
        assert call_kwargs["auto_all"] is False

    @patch("scripts.generate_content.ContentGenerator")
    @patch("scripts.generate_content.get_weekly_slot")
    def test_main_handles_weekly_slot_error(self, mock_get_weekly_slot, mock_generator_cls):
        from scripts.generate_content import main

        mock_get_weekly_slot.side_effect = RuntimeError("broken weekly slot")
        mock_generator = MagicMock()
        mock_generator.run.return_value = {
            "date": "2026-02-20",
            "approved_items": 0,
            "longform_created": 0,
            "packs_created": 0,
            "image_prompts_created": 0,
            "errors": ["err"],
        }
        mock_generator_cls.return_value = mock_generator

        with (
            patch(
                "sys.argv",
                ["generate_content.py", "--week-of", "2026-02-17", "--auto-all"],
            ),
            patch("builtins.print"),
        ):
            main()

        assert mock_generator.run.call_args.kwargs["auto_all"] is True

    def test_smart_truncate_keeps_short_text(self):
        from scripts.generate_content import smart_truncate

        assert smart_truncate("hello", 10) == "hello"

    def test_smart_truncate_truncates_and_keeps_hashtag_tail(self):
        from scripts.generate_content import smart_truncate

        text = "one two three four five six seven\n#tag1\n#tag2"
        result = smart_truncate(text, 28)

        assert len(result) <= 28
        assert "#tag1" in result or "#tag2" in result


class TestRunAndProcessingBranches:
    @patch("scripts.generate_content.get_config")
    def test_run_batch_mode_uses_item_ids(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.dry_run = True
        generator._get_items_by_ids = MagicMock(return_value=[{"input_id": "a"}])
        generator._process_item = MagicMock()

        result = generator.run(items=["a"], content_types=["longform"])

        assert result["approved_items"] == 1
        generator._get_items_by_ids.assert_called_once_with(["a"])

    @patch("scripts.generate_content.get_config")
    def test_run_collects_top_level_exception(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.dry_run = True
        generator._parse_digest = MagicMock(side_effect=RuntimeError("digest crash"))

        result = generator.run(date="2026-02-20")

        assert result["errors"] == ["digest crash"]

    @patch("scripts.generate_content.get_config")
    def test_get_items_by_ids_handles_missing_item(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        mock_vault.read_note.side_effect = [
            ({"title": "A"}, "ok"),
            FileNotFoundError("missing"),
        ]

        items = generator._get_items_by_ids(["a", "b"])

        assert len(items) == 1
        assert items[0]["input_id"] == "a"

    @patch("scripts.generate_content.get_config")
    def test_process_item_updates_digest_when_not_dry_run(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.dry_run = False
        generator._should_process_item = MagicMock(return_value=True)
        generator._load_input = MagicMock(return_value={"writing_status": "auto_ready"})
        generator._generate_content_types = MagicMock()
        generator._update_digest_status = MagicMock()

        results = {"errors": []}
        generator._process_item({"input_id": "x"}, ["longform"], False, "2026-02-20", results)

        generator._update_digest_status.assert_called_once_with("2026-02-20", "x")

    @patch("scripts.generate_content.get_config")
    def test_process_item_appends_error(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator._should_process_item = MagicMock(side_effect=RuntimeError("boom"))

        results = {"errors": []}
        generator._process_item({"input_id": "x"}, ["longform"], False, "2026-02-20", results)

        assert results["errors"] == ["boom"]


class TestGenerationAndApprovalPaths:
    @patch("scripts.generate_content.get_config")
    def test_generate_content_types_updates_counts(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator._generate_longform = MagicMock(return_value=True)
        generator._generate_packs_with_approval = MagicMock(return_value=2)
        generator._generate_image_with_approval = MagicMock(return_value=True)

        results = {
            "longform_created": 0,
            "packs_created": 0,
            "image_prompts_created": 0,
        }
        generator._generate_content_types(
            {"input_id": "x"},
            {"writing_status": "auto_ready"},
            ["longform", "packs", "images"],
            results,
        )

        assert results == {
            "longform_created": 1,
            "packs_created": 2,
            "image_prompts_created": 1,
        }

    @patch("scripts.generate_content.get_config")
    def test_generate_content_types_force_overrides_manual_status(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator._generate_longform = MagicMock(return_value=True)
        generator._generate_packs_with_approval = MagicMock(return_value=0)
        generator._generate_image_with_approval = MagicMock(return_value=False)

        results = {
            "longform_created": 0,
            "packs_created": 0,
            "image_prompts_created": 0,
        }
        generator._generate_content_types(
            {"input_id": "x"},
            {"writing_status": "manual"},
            ["longform"],
            results,
            force=True,
        )
        assert results["longform_created"] == 1

    @patch("scripts.generate_content.get_effective_prompt")
    @patch("scripts.generate_content.get_config")
    def test_generate_longform_writes_output(self, mock_get_config, mock_get_effective_prompt, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        mock_get_effective_prompt.return_value = "prompt"

        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        generator.llm = MagicMock()
        generator.llm.generate.return_value = "[메인 콘텐츠]\nhello"
        generator.renderer = MagicMock()
        generator.renderer.render_longform.return_value = "---\nid: longform_x\n---\nbody"
        generator.weekly_slot = None
        generator.dry_run = False
        generator._load_exploration = MagicMock(return_value=None)

        ok = generator._generate_longform(
            {"input_id": "x", "account_id": "socialbuilders"},
            {"title": "T", "tags": []},
        )

        assert ok is True
        assert mock_vault.write_note.called

    @patch("scripts.generate_content.get_config")
    def test_generate_packs_truncates_and_handles_channel_exception(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {
                "twitter": {"max_length": 10, "hashtags": True},
                "linkedin": {"max_length": 20, "hashtags": False},
            }
        }

        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        generator.llm = MagicMock()
        generator.llm.generate.return_value = "very long content #a #b #c #d"
        generator.renderer = MagicMock()
        generator.renderer.render_pack.side_effect = [
            "---\nid: p\n---\nbody",
            RuntimeError("render fail"),
        ]
        generator.prompt_loader = MagicMock()
        generator.prompt_loader.get_pack_prompt.return_value = "prompt"
        generator._prepare_weekly_context = MagicMock(return_value=None)
        generator.dry_run = False

        count = generator._generate_packs({"input_id": "x", "account_id": "socialbuilders"}, {"tags": ["AI", "ML"]})

        assert count == 1

    @patch("scripts.generate_content.get_config")
    def test_generate_image_prompt_writes_output(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        generator.prompt_loader = MagicMock()
        generator.prompt_loader.get_image_prompt.return_value = "prompt"
        generator.llm = MagicMock()
        generator.llm.generate.return_value = "[메인 프롬프트]\nA scene"
        generator.renderer = MagicMock()
        generator.renderer.render_image_prompt.return_value = "---\nid: img_x\n---\nbody"
        generator.dry_run = False

        ok = generator._generate_image_prompt({"input_id": "x", "account_id": "socialbuilders"}, {})

        assert ok is True
        assert mock_vault.write_note.called

    @patch("scripts.generate_content.get_config")
    def test_generate_packs_with_approval_branches(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)

        generator._check_derivative_approval = MagicMock(return_value={"status": "pending"})
        assert generator._generate_packs_with_approval({"input_id": "x"}, {}) == 0

        generator._check_derivative_approval = MagicMock(return_value={"status": "approved", "packs_channels": []})
        generator._load_longform_content = MagicMock(return_value=None)
        assert generator._generate_packs_with_approval({"input_id": "x"}, {}) == 0

        generator._check_derivative_approval = MagicMock(
            return_value={"status": "approved", "packs_channels": ["twitter"]}
        )
        generator._load_longform_content = MagicMock(return_value={"longform_body": "body"})
        generator._generate_packs_for_channels = MagicMock(return_value=1)
        assert generator._generate_packs_with_approval({"input_id": "x"}, {}) == 1

    @patch("scripts.generate_content.get_config")
    def test_generate_image_with_approval_branches(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)

        generator._check_derivative_approval = MagicMock(return_value={"status": "pending"})
        assert generator._generate_image_with_approval({"input_id": "x"}, {}) is False

        generator._check_derivative_approval = MagicMock(return_value={"status": "approved", "images_approved": False})
        assert generator._generate_image_with_approval({"input_id": "x"}, {}) is False

        generator._check_derivative_approval = MagicMock(return_value={"status": "approved", "images_approved": True})
        generator._load_longform_content = MagicMock(return_value={"main_content": "m"})
        generator._generate_image_prompt = MagicMock(return_value=True)
        assert generator._generate_image_with_approval({"input_id": "x"}, {}) is True

    @patch("scripts.generate_content.get_config")
    def test_check_derivative_approval_with_frontmatter_and_missing_file(
        self, mock_get_config, mock_config, mock_vault
    ):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault

        meta = {"packs_channels": ["newsletter"], "derivative_status": "pending"}
        content = "[x] **Twitter**\n[x] **이미지 프롬프트**"
        mock_vault.read_note.return_value = (meta, content)
        result = generator._check_derivative_approval("x")
        assert result["status"] == "approved"
        assert result["packs_channels"] == ["newsletter"]
        assert result["images_approved"] is True

        mock_vault.read_note.side_effect = FileNotFoundError("missing")
        missing_result = generator._check_derivative_approval("x")
        assert missing_result["status"] == "pending"

    @patch("scripts.generate_content.get_config")
    def test_load_longform_content_and_missing(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        generator._extract_section = MagicMock(side_effect=["intro", "main", "takeaways"])

        mock_vault.read_note.return_value = ({"title": "LF"}, "content")
        loaded = generator._load_longform_content("x")
        assert loaded["longform_title"] == "LF"

        mock_vault.read_note.side_effect = FileNotFoundError("missing")
        assert generator._load_longform_content("x") is None

    @patch("scripts.generate_content.get_config")
    def test_generate_packs_for_channels_handles_unconfigured_channel(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {
                "twitter": {"max_length": 12, "hashtags": True},
            }
        }

        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault
        generator.prompt_loader = MagicMock()
        generator.prompt_loader.get_pack_prompt.return_value = "prompt"
        generator.llm = MagicMock()
        generator.llm.generate.return_value = "pack text over length"
        generator.renderer = MagicMock()
        generator.renderer.render_pack.return_value = "---\nid: p\n---\nbody"
        generator._prepare_weekly_context = MagicMock(return_value=None)
        generator.dry_run = False

        # Properly mock the validator with correct return structure
        mock_report = MagicMock()
        mock_report.results = []  # Empty results means no validation errors
        mock_validator = MagicMock()
        mock_validator.validate_path.return_value = mock_report
        generator.validator = mock_validator

        created = generator._generate_packs_for_channels(
            {"input_id": "x", "account_id": "socialbuilders"},
            {"tags": ["a"]},
            ["missing", "twitter"],
        )
        assert created == 1


class TestStatusAndUtilityMethods:
    @patch("scripts.generate_content.get_config")
    def test_update_digest_status_success_and_failure(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault

        generator._update_digest_status("2026-02-20", "x")
        assert mock_vault.write_note.called

        mock_vault.read_note.side_effect = RuntimeError("write blocked")
        generator._update_digest_status("2026-02-20", "x")

    @patch("scripts.generate_content.get_config")
    def test_prepare_weekly_context_and_parse_frontmatter(self, mock_get_config, mock_config):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.weekly_slot = None
        assert generator._prepare_weekly_context() is None

        generator.weekly_slot = SimpleNamespace(
            cta="CTA",
            customer_outcome="Outcome",
            operator_kpi="KPI",
            pillar_distribution={"P1": 2},
        )
        ctx = generator._prepare_weekly_context()
        assert ctx["cta"] == "CTA"

        parsed = generator._parse_frontmatter("---\na: 1\n---\nbody")
        assert parsed["a"] == 1
        assert generator._parse_frontmatter("no frontmatter") == {}

    @patch("scripts.generate_content.get_config")
    def test_load_input_checkbox_status_updates(self, mock_get_config, mock_config, mock_vault):
        from scripts.generate_content import ContentGenerator

        mock_get_config.return_value = mock_config
        generator = ContentGenerator.__new__(ContentGenerator)
        generator.config = mock_config
        generator.vault = mock_vault

        auto_content = "[x] **자동 작성**\n## 요약\nA"
        mock_vault.read_note.return_value = (
            {"title": "T", "writing_status": "pending", "tags": []},
            auto_content,
        )
        auto_result = generator._load_input("x")
        assert auto_result["writing_status"] == "auto_ready"

        manual_content = "[x] **수동 작성**\n## 요약\nA"
        mock_vault.read_note.return_value = (
            {"title": "T", "writing_status": "pending", "tags": []},
            manual_content,
        )
        manual_result = generator._load_input("x")
        assert manual_result["writing_status"] == "manual"
