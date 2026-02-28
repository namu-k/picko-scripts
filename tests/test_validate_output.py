"""
Tests for validate_output.py

Unit tests for the OutputValidator class covering:
- Content type detection
- Required field validation
- Recommended field validation
- Required section validation
- Wikilink validation
- Content quality validation
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
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    vault.get_path = lambda p: Path(f"/tmp/test_vault/{p}")
    vault.read_note.return_value = ({}, "Test content")
    vault.list_notes.return_value = []
    vault.extract_wikilinks.return_value = []
    return vault


@pytest.fixture
def sample_input_meta():
    """Sample input metadata"""
    return {
        "id": "input_abc123",
        "title": "Test Article",
        "source": "Test Source",
        "source_url": "https://example.com/test",
        "status": "inbox",
    }


@pytest.fixture
def sample_longform_meta():
    """Sample longform metadata"""
    return {
        "id": "longform_abc123",
        "title": "Test Longform",
        "type": "longform",
        "status": "draft",
        "source_input": "input_abc123",
        "derivative_status": "pending",
    }


@pytest.fixture
def sample_digest_meta():
    """Sample digest metadata"""
    return {
        "type": "digest",
        "date": "2026-02-17",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_validation_result_defaults(self):
        """Test default values"""
        from scripts.validate_output import ValidationResult

        result = ValidationResult(path="/test/path.md", valid=True)

        assert result.path == "/test/path.md"
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_with_errors(self):
        """Test result with errors"""
        from scripts.validate_output import ValidationResult

        result = ValidationResult(path="/test/path.md", valid=False, errors=["Error 1", "Error 2"])

        assert result.valid is False
        assert len(result.errors) == 2


class TestValidationReport:
    """Tests for ValidationReport dataclass"""

    def test_validation_report_defaults(self):
        """Test default values"""
        from scripts.validate_output import ValidationReport

        report = ValidationReport()

        assert report.total_files == 0
        assert report.valid_files == 0
        assert report.invalid_files == 0
        assert report.results == []

    def test_add_result_valid(self):
        """Test adding valid result"""
        from scripts.validate_output import ValidationReport, ValidationResult

        report = ValidationReport()
        result = ValidationResult(path="/test.md", valid=True)

        report.add_result(result)

        assert report.total_files == 1
        assert report.valid_files == 1
        assert report.invalid_files == 0

    def test_add_result_invalid(self):
        """Test adding invalid result"""
        from scripts.validate_output import ValidationReport, ValidationResult

        report = ValidationReport()
        result = ValidationResult(path="/test.md", valid=False, errors=["Error"])

        report.add_result(result)

        assert report.total_files == 1
        assert report.valid_files == 0
        assert report.invalid_files == 1


class TestOutputValidatorInit:
    """Tests for OutputValidator initialization"""

    @patch("scripts.validate_output.get_config")
    @patch("scripts.validate_output.VaultIO")
    def test_init(self, mock_vault_class, mock_get_config, mock_config):
        """Test initialization"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        validator = OutputValidator()

        assert validator.config is not None
        assert validator.vault is not None


class TestContentTypeDetection:
    """Tests for content type detection"""

    @patch("scripts.validate_output.get_config")
    def test_detect_from_metadata(self, mock_get_config, mock_config):
        """Test detecting type from frontmatter"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_FIELDS = OutputValidator.REQUIRED_FIELDS

            meta = {"type": "longform"}
            path = Path("/unknown/path.md")

            result = validator._detect_content_type(meta, path)

        assert result == "longform"

    @patch("scripts.validate_output.get_config")
    def test_detect_from_path_longform(self, mock_get_config, mock_config):
        """Test detecting longform from path"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Content/Longform/test.md")

            result = validator._detect_content_type(meta, path)

        assert result == "longform"

    @patch("scripts.validate_output.get_config")
    def test_detect_from_path_digest(self, mock_get_config, mock_config):
        """Test detecting digest from path"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Inbox/Inputs/_digests/2026-02-17.md")

            result = validator._detect_content_type(meta, path)

        assert result == "digest"

    @patch("scripts.validate_output.get_config")
    def test_detect_from_path_input(self, mock_get_config, mock_config):
        """Test detecting input from path"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Inbox/Inputs/test.md")

            result = validator._detect_content_type(meta, path)

        assert result == "input"

    @patch("scripts.validate_output.get_config")
    def test_detect_unknown_type(self, mock_get_config, mock_config):
        """Test unknown type detection"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Unknown/test.md")

            result = validator._detect_content_type(meta, path)

        assert result == "unknown"

    @patch("scripts.validate_output.get_config")
    def test_detect_from_path_pack(self, mock_get_config, mock_config):
        """Test detecting pack from /Packs/ path (covers line 157)"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Content/Packs/twitter_pack.md")

            result = validator._detect_content_type(meta, path)

        assert result == "pack"

    @patch("scripts.validate_output.get_config")
    def test_detect_from_path_image_prompt(self, mock_get_config, mock_config):
        """Test detecting image_prompt from /_prompts/ path (covers line 159)"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            meta = {}
            path = Path("/tmp/vault/Assets/Images/_prompts/prompt.md")

            result = validator._detect_content_type(meta, path)

        assert result == "image_prompt"


class TestRequiredFieldValidation:
    """Tests for required field validation"""

    @patch("scripts.validate_output.get_config")
    def test_validate_all_required_present(self, mock_get_config, mock_config):
        """Test when all required fields are present"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_FIELDS = {
                "input": ["id", "title", "source"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"id": "123", "title": "Test", "source": "Test Source"}

            validator._validate_required_fields(meta, "input", result)

        assert result.valid is True
        assert len(result.errors) == 0

    @patch("scripts.validate_output.get_config")
    def test_validate_missing_required(self, mock_get_config, mock_config):
        """Test when required field is missing"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_FIELDS = {
                "input": ["id", "title", "source"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"id": "123", "title": "Test"}  # Missing source

            validator._validate_required_fields(meta, "input", result)

        assert result.valid is False
        assert any("Missing required field" in e for e in result.errors)

    @patch("scripts.validate_output.get_config")
    def test_validate_empty_required(self, mock_get_config, mock_config):
        """Test when required field is empty"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_FIELDS = {
                "input": ["id", "title"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"id": "123", "title": ""}  # Empty title

            validator._validate_required_fields(meta, "input", result)

        assert len(result.warnings) > 0


class TestRecommendedFieldValidation:
    """Tests for recommended field validation"""

    @patch("scripts.validate_output.get_config")
    def test_validate_missing_recommended(self, mock_get_config, mock_config):
        """Test warning for missing recommended field"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.RECOMMENDED_FIELDS = {
                "longform": ["packs_channels"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"type": "longform"}  # Missing packs_channels

            validator._validate_recommended_fields(meta, "longform", result)

        # Should not make valid False, just add warning
        assert result.valid is True
        assert any("Missing recommended field" in w for w in result.warnings)


class TestRequiredSectionValidation:
    """Tests for required section validation"""

    @patch("scripts.validate_output.get_config")
    def test_validate_section_present(self, mock_get_config, mock_config):
        """Test when required section is present"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_SECTIONS = {
                "input": ["요약"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            content = """## 요약

This is the summary section.
"""

            validator._validate_required_sections(content, "input", result)

        assert result.valid is True

    @patch("scripts.validate_output.get_config")
    def test_validate_section_missing(self, mock_get_config, mock_config):
        """Test when required section is missing"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.REQUIRED_SECTIONS = {
                "input": ["요약"],
            }

            result = ValidationResult(path="/test.md", valid=True)
            content = """## Other Section

No summary here.
"""

            validator._validate_required_sections(content, "input", result)

        assert result.valid is False
        assert any("Missing required section" in e for e in result.errors)


class TestWikilinkValidation:
    """Tests for wikilink validation"""

    @patch("scripts.validate_output.get_config")
    def test_validate_valid_wikilink(self, mock_get_config, mock_config, mock_vault):
        """Test valid wikilink"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.vault = mock_vault
            validator.vault.extract_wikilinks.return_value = ["valid_link"]
            validator.vault.resolve_wikilink.return_value = Path("/exists.md")

            result = ValidationResult(path="/test.md", valid=True)
            content = "Check [[valid_link]]"

            validator._validate_wikilinks(content, result)

        assert len(result.warnings) == 0

    @patch("scripts.validate_output.get_config")
    def test_validate_broken_wikilink(self, mock_get_config, mock_config, mock_vault):
        """Test broken wikilink warning"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)
            validator.vault = mock_vault
            validator.vault.extract_wikilinks.return_value = ["broken_link"]
            validator.vault.resolve_wikilink.return_value = None

            result = ValidationResult(path="/test.md", valid=True)
            content = "Check [[broken_link]]"

            validator._validate_wikilinks(content, result)

        assert any("Broken wikilink" in w for w in result.warnings)


class TestContentQualityValidation:
    """Tests for content quality validation"""

    @patch("scripts.validate_output.get_config")
    def test_validate_title_too_long(self, mock_get_config, mock_config):
        """Test warning for long title"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"title": "A" * 250}  # Too long
            content = "Content"

            validator._validate_content_quality(meta, content, "longform", result)

        assert any("Title too long" in w for w in result.warnings)

    @patch("scripts.validate_output.get_config")
    def test_validate_content_too_short(self, mock_get_config, mock_config):
        """Test warning for short content"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"title": "Test"}
            content = "Short"  # Too short for longform

            validator._validate_content_quality(meta, content, "longform", result)

        assert any("Content too short" in w for w in result.warnings)

    @patch("scripts.validate_output.get_config")
    def test_validate_invalid_status(self, mock_get_config, mock_config):
        """Test warning for invalid status"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"status": "invalid_status"}
            content = "Content"

            validator._validate_content_quality(meta, content, "longform", result)

        assert any("Unknown status" in w for w in result.warnings)

    @patch("scripts.validate_output.get_config")
    def test_validate_invalid_date_format(self, mock_get_config, mock_config):
        """Test warning for invalid date format"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        with patch.object(OutputValidator, "__init__", lambda x: None):
            validator = OutputValidator.__new__(OutputValidator)

            result = ValidationResult(path="/test.md", valid=True)
            meta = {"created_at": "not-a-date"}
            content = "Content"

            validator._validate_content_quality(meta, content, "input", result)

        assert any("Invalid date format" in w for w in result.warnings)


class TestValidatePath:
    """Tests for validate_path method"""

    @patch("scripts.validate_output.get_config")
    def test_validate_single_file(self, mock_get_config, mock_config, mock_vault):
        """Test validating single file"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        validator = OutputValidator.__new__(OutputValidator)
        validator.config = mock_config
        validator.vault = mock_vault

        # Create a mock Path that returns is_file=True
        mock_path = MagicMock()
        mock_path.is_file.return_value = True
        mock_path.is_dir.return_value = False
        validator.vault.get_path = MagicMock(return_value=mock_path)

        # Mock file validation
        with patch.object(validator, "_validate_file") as mock_validate:
            mock_validate.return_value = ValidationResult(path="/test.md", valid=True)

            validator.validate_path("test.md")

    @patch("scripts.validate_output.get_config")
    def test_validate_directory(self, mock_get_config, mock_config, mock_vault):
        """Test validating directory"""
        mock_get_config.return_value = mock_config

        from scripts.validate_output import OutputValidator, ValidationResult

        validator = OutputValidator.__new__(OutputValidator)
        validator.config = mock_config
        validator.vault = mock_vault

        # Create a mock Path that returns is_dir=True
        mock_path = MagicMock()
        mock_path.is_file.return_value = False
        mock_path.is_dir.return_value = True
        validator.vault.get_path = MagicMock(return_value=mock_path)
        validator.vault.list_notes.return_value = [Path("/test1.md"), Path("/test2.md")]

        # Mock file validation
        with patch.object(validator, "_validate_file") as mock_validate:
            mock_validate.return_value = ValidationResult(path="/test.md", valid=True)

            report = validator.validate_path("Content/", recursive=True)

        assert report.total_files == 2
