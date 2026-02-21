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

    @patch("scripts.generate_content.get_config")
    def test_parse_generated_sections_handles_missing_sections(self, mock_get_config, mock_config):
        """Test parsing sections when some are missing (backward compatibility)"""
        mock_get_config.return_value = mock_config

        from scripts.generate_content import ContentGenerator

        llm_output = """[메인 프롬프트]
Main prompt content.

[스타일]
Modern style.
"""

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config

            result = generator._parse_generated_sections(llm_output)

        # Should still parse existing sections
        assert "메인 프롬프트" in result
        assert "스타일" in result
        # Missing sections should return empty strings
        assert result.get("네거티브 프롬프트", "") == ""
        assert result.get("참고 이미지", "") == ""


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


class TestImagePromptGeneration:
    """Tests for image prompt generation with new fields"""

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_generate_image_prompt_parses_negative_prompt(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that negative_prompt is parsed from [네거티브 프롬프트] section"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = """[메인 프롬프트]
A beautiful sunset over mountains.

[스타일]
Photorealistic, 8K.

[분위기]
Peaceful.

[색상]
Orange, purple, blue.

[네거티브 프롬프트]
Blurry, low quality, distorted, ugly, deformed, bad anatomy.

[참고 이미지]
없음
"""

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title"}

            generator._generate_image_prompt(item, input_content)

        # Verify prompt_loader.get_image_prompt was called
        mock_loader.get_image_prompt.assert_called_once()

        # Verify renderer.render_image_prompt was called with correct data
        mock_renderer.render_image_prompt.assert_called_once()
        call_args = mock_renderer.render_image_prompt.call_args
        prompt_data = call_args[0][0]

        # Check that negative_prompt is in the data
        assert "negative_prompt" in prompt_data
        assert "Blurry, low quality" in prompt_data["negative_prompt"]

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_generate_image_prompt_parses_reference_images(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that reference_images is parsed from [참고 이미지] section"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = """[메인 프롬프트]
A modern office workspace.

[스타일]
Minimalist, clean.

[분위기]
Professional.

[색상]
White, gray, blue.

[네거티브 프롬프트]
Cluttered, messy.

[참고 이미지]
- Reference image 1: https://example.com/image1.jpg
- Reference image 2: https://example.com/image2.png
- Reference image 3: https://example.com/image3.webp
"""

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title"}

            generator._generate_image_prompt(item, input_content)

        # Verify renderer.render_image_prompt was called with correct data
        mock_renderer.render_image_prompt.assert_called_once()
        call_args = mock_renderer.render_image_prompt.call_args
        prompt_data = call_args[0][0]

        # Check that reference_images is in the data
        assert "reference_images" in prompt_data
        assert len(prompt_data["reference_images"]) == 3
        assert "https://example.com/image1.jpg" in prompt_data["reference_images"]
        assert "https://example.com/image2.png" in prompt_data["reference_images"]
        assert "https://example.com/image3.webp" in prompt_data["reference_images"]

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_generate_image_prompt_handles_empty_reference_images(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that empty reference_images (없음) is handled correctly"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = """[메인 프롬프트]
A simple landscape.

[스타일]
Realistic.

[분위기]
Calm.

[색상]
Green, blue.

[네거티브 프롬프트]
No specific negatives.

[참고 이미지]
없음
"""

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title"}

            generator._generate_image_prompt(item, input_content)

        # Verify renderer.render_image_prompt was called with correct data
        mock_renderer.render_image_prompt.assert_called_once()
        call_args = mock_renderer.render_image_prompt.call_args
        prompt_data = call_args[0][0]

        # Check that reference_images is an empty list when value is "없음"
        assert "reference_images" in prompt_data
        assert prompt_data["reference_images"] == []

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_generate_image_prompt_backward_compatibility(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test backward compatibility when new sections are missing"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = """[메인 프롬프트]
A beautiful scene.

[스타일]
Modern.

[분위기]
Happy.

[색상]
Red, yellow.
"""

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title"}

            generator._generate_image_prompt(item, input_content)

        # Verify renderer.render_image_prompt was called with correct data
        mock_renderer.render_image_prompt.assert_called_once()
        call_args = mock_renderer.render_image_prompt.call_args
        prompt_data = call_args[0][0]

        # Check that old fields are still present
        assert "prompt" in prompt_data
        assert "style" in prompt_data
        assert "mood" in prompt_data
        assert "colors" in prompt_data

        # Check that new fields have safe defaults
        assert prompt_data.get("negative_prompt", "") == ""
        assert prompt_data.get("reference_images", []) == []

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_generate_image_with_approval_uses_channel_specific_prompt(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that channel-specific prompt is used when packs_channels is non-empty"""
        mock_get_config.return_value = mock_config
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = """[메인 프롬프트]
Test image.

[스타일]
Modern.

[분위기]
Professional.

[색상]
Blue.

[네거티브 프롬프트]
None.

[참고 이미지]
없음
"""
        mock_renderer.render_image_prompt.return_value = "---\nid: test_image\n---\nImage prompt"

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True

            # Mock _check_derivative_approval to return approved with channels
            with patch.object(
                generator,
                "_check_derivative_approval",
                return_value={
                    "status": "approved",
                    "images_approved": True,
                    "packs_channels": ["twitter"],
                },
            ):
                # Mock _load_longform_content
                with patch.object(
                    generator,
                    "_load_longform_content",
                    return_value={"longform_title": "Test", "longform_body": "Body"},
                ):
                    item = {"input_id": "test_input", "account_id": "socialbuilders"}
                    input_content = {"title": "Test Title"}

                    generator._generate_image_with_approval(item, input_content)

        # Verify get_channel_image_prompt was called with twitter channel
        mock_loader.get_channel_image_prompt.assert_called_once()
        call_kwargs = mock_loader.get_channel_image_prompt.call_args[1]
        assert call_kwargs["channel"] == "twitter"


class TestHashtagHandling:
    """Tests for pack hashtag configuration handling"""

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_hashtags_false_renders_empty_list(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that hashtags=False results in empty list passed to renderer"""
        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {"twitter": {"enabled": True, "max_length": 280, "hashtags": False}}
        }
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = "Test pack content"
        mock_renderer.render_pack.return_value = "---\nid: test_pack\n---\nPack content"

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True
            generator.weekly_slot = None

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title", "tags": ["AI", "startup", "tech"]}

            generator._generate_packs(item, input_content)

        # Verify renderer.render_pack was called with empty hashtags list
        mock_renderer.render_pack.assert_called_once()
        call_args = mock_renderer.render_pack.call_args[0][0]
        assert call_args["hashtags"] == []

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_hashtags_true_auto_generates_from_tags(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that hashtags=True auto-generates hashtags from input_content tags"""
        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {"twitter": {"enabled": True, "max_length": 280, "hashtags": True}}
        }
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = "Test pack content"
        mock_renderer.render_pack.return_value = "---\nid: test_pack\n---\nPack content"

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True
            generator.weekly_slot = None

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title", "tags": ["AI", "startup", "tech"]}

            generator._generate_packs(item, input_content)

        # Verify renderer.render_pack was called with auto-generated hashtags
        mock_renderer.render_pack.assert_called_once()
        call_args = mock_renderer.render_pack.call_args[0][0]
        assert call_args["hashtags"] == ["#AI", "#startup", "#tech"]

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_hashtags_list_uses_verbatim(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test that hashtags=[list] uses the list verbatim (assume already prefixed)"""
        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {
                "twitter": {
                    "enabled": True,
                    "max_length": 280,
                    "hashtags": ["#창업", "#스타트업", "#빌더스소셜클럽"],
                }
            }
        }
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = "Test pack content"
        mock_renderer.render_pack.return_value = "---\nid: test_pack\n---\nPack content"

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True
            generator.weekly_slot = None

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title", "tags": ["AI", "startup", "tech"]}

            generator._generate_packs(item, input_content)

        # Verify renderer.render_pack was called with the provided hashtag list verbatim
        mock_renderer.render_pack.assert_called_once()
        call_args = mock_renderer.render_pack.call_args[0][0]
        assert call_args["hashtags"] == ["#창업", "#스타트업", "#빌더스소셜클럽"]

    @patch("scripts.generate_content.get_config")
    @patch("scripts.generate_content.VaultIO")
    @patch("scripts.generate_content.get_writer_client")
    @patch("scripts.generate_content.get_renderer")
    @patch("scripts.generate_content.get_prompt_loader")
    def test_hashtags_for_channels_false_renders_empty_list(
        self,
        mock_loader,
        mock_renderer,
        mock_llm,
        mock_vault,
        mock_get_config,
        mock_config,
    ):
        """Test _generate_packs_for_channels with hashtags=False"""
        mock_get_config.return_value = mock_config
        mock_config.get_account.return_value = {
            "channels": {"twitter": {"enabled": True, "max_length": 280, "hashtags": False}}
        }
        mock_vault.read_note.return_value = ({}, "content")
        mock_llm.generate.return_value = "Test pack content"
        mock_renderer.render_pack.return_value = "---\nid: test_pack\n---\nPack content"

        from scripts.generate_content import ContentGenerator

        with patch.object(ContentGenerator, "__init__", lambda x, **kwargs: None):
            generator = ContentGenerator.__new__(ContentGenerator)
            generator.config = mock_config
            generator.vault = mock_vault
            generator.llm = mock_llm
            generator.renderer = mock_renderer
            generator.prompt_loader = mock_loader
            generator.dry_run = True
            generator.weekly_slot = None

            item = {"input_id": "test_input", "account_id": "socialbuilders"}
            input_content = {"title": "Test Title", "tags": ["AI", "startup", "tech"]}

            generator._generate_packs_for_channels(item, input_content, ["twitter"])

        # Verify renderer.render_pack was called with empty hashtags list
        mock_renderer.render_pack.assert_called_once()
        call_args = mock_renderer.render_pack.call_args[0][0]
        assert call_args["hashtags"] == []
