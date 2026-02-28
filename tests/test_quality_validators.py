"""
Tests for Quality Validators - Primary and Cross-Check.

Tests JSON parsing, verdict normalization, and validation logic.
"""

from unittest.mock import MagicMock, patch

from picko.quality.validators.cross_check import CrossCheckValidator
from picko.quality.validators.cross_check import parse_json_response as cross_parse_json_response
from picko.quality.validators.primary import PrimaryValidator, _fallback_result, parse_json_response


class TestParseJsonResponse:
    """Tests for JSON parsing from LLM responses."""

    def test_parse_pure_json(self):
        """Should parse pure JSON response."""
        response = '{"verdict": "approved", "confidence": 0.9}'
        result = parse_json_response(response)

        assert result["verdict"] == "approved"
        assert result["confidence"] == 0.9

    def test_parse_json_with_markdown_block(self):
        """Should parse JSON from markdown code block."""
        response = """```json
{
  "verdict": "rejected",
  "confidence": 0.3,
  "reasoning": "Low quality"
}
```"""
        result = parse_json_response(response)

        assert result["verdict"] == "rejected"
        assert result["confidence"] == 0.3

    def test_parse_json_embedded_in_text(self):
        """Should extract JSON from surrounding text."""
        response = """Here is my evaluation:
{
  "verdict": "needs_review",
  "confidence": 0.6,
  "reasoning": "Needs checking"
}
That's my assessment."""
        result = parse_json_response(response)

        assert result["verdict"] == "needs_review"
        assert result["confidence"] == 0.6

    def test_parse_empty_response_returns_fallback(self):
        """Empty response should return fallback result."""
        result = parse_json_response("")

        assert result["verdict"] == "needs_review"
        assert result["confidence"] == 0.5
        assert "parse_error" in result["flags"]

    def test_parse_invalid_json_returns_fallback(self):
        """Invalid JSON should return fallback result."""
        result = parse_json_response("This is not JSON at all")

        assert result["verdict"] == "needs_review"
        assert result["confidence"] == 0.5


class TestFallbackResult:
    """Tests for fallback result generation."""

    def test_fallback_has_required_fields(self):
        """Fallback should have all required fields."""
        result = _fallback_result("Test error")

        assert "verdict" in result
        assert "confidence" in result
        assert "scores" in result
        assert "reasoning" in result
        assert "flags" in result

    def test_fallback_verdict_is_needs_review(self):
        """Fallback verdict should always be needs_review."""
        result = _fallback_result("Any error")

        assert result["verdict"] == "needs_review"


class TestPrimaryValidator:
    """Tests for PrimaryValidator class."""

    def test_init_without_model(self):
        """PrimaryValidator should initialize without model override."""
        validator = PrimaryValidator()

        assert validator.model is None
        assert validator._llm is None

    def test_normalize_verdict_approved(self):
        """Should normalize approved verdicts."""
        validator = PrimaryValidator()

        result = validator._normalize_result({"verdict": "APPROVED", "confidence": 0.9})

        assert result["verdict"] == "approved"

    def test_normalize_verdict_rejected(self):
        """Should normalize rejected verdicts."""
        validator = PrimaryValidator()

        result = validator._normalize_result({"verdict": "REJECTED", "confidence": 0.3})

        assert result["verdict"] == "rejected"

    def test_normalize_verdict_unknown_becomes_needs_review(self):
        """Unknown verdicts should become needs_review."""
        validator = PrimaryValidator()

        result = validator._normalize_result({"verdict": "maybe", "confidence": 0.5})

        assert result["verdict"] == "needs_review"

    def test_normalize_confidence_clamped_to_range(self):
        """Confidence should be clamped to 0.0-1.0."""
        validator = PrimaryValidator()

        result_high = validator._normalize_result({"verdict": "approved", "confidence": 1.5})
        result_low = validator._normalize_result({"verdict": "approved", "confidence": -0.5})

        assert result_high["confidence"] == 1.0
        assert result_low["confidence"] == 0.0

    def test_normalize_ensures_scores(self):
        """Should ensure all score fields exist."""
        validator = PrimaryValidator()

        result = validator._normalize_result({"verdict": "approved", "confidence": 0.8})

        assert "factual" in result["scores"]
        assert "source_credibility" in result["scores"]
        assert "bias" in result["scores"]
        assert "value" in result["scores"]

    @patch("picko.quality.validators.primary.get_summary_client")
    def test_validate_calls_llm(self, mock_get_client):
        """validate() should call LLM with formatted prompt."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"verdict": "approved", "confidence": 0.9, '
            '{"scores": {"factual": 9, "source_credibility": 9, '
            '"bias": 8, "value": 9}, "reasoning": "Good", "flags": []}'
        )
        mock_get_client.return_value = mock_llm

        validator = PrimaryValidator()
        result = validator.validate(title="Test", content="Content")

        assert result["verdict"] == "approved"
        mock_llm.generate.assert_called_once()

    def test_validate_truncates_long_content(self):
        """validate() should truncate content to avoid token limits."""
        validator = PrimaryValidator()

        # Very long content
        long_content = "x" * 5000

        # Mock the internal _llm attribute directly
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"verdict": "approved", "confidence": 0.9, "scores": {}, "reasoning": "", "flags": []}'
        )
        validator._llm = mock_llm

        validator.validate(title="Test", content=long_content)

        # Check that the prompt contains truncated content
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        assert len(prompt) < 6000  # Should be truncated


class TestCrossCheckValidator:
    """Tests for CrossCheckValidator class."""

    def test_init_without_overrides(self):
        """CrossCheckValidator should initialize without overrides."""
        validator = CrossCheckValidator()

        assert validator.provider is None
        assert validator.model is None

    def test_init_with_overrides(self):
        """CrossCheckValidator should accept provider/model overrides."""
        validator = CrossCheckValidator(provider="anthropic", model="claude-3-opus")

        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-opus"

    @patch("picko.quality.validators.cross_check.LLMClient")
    def test_validate_calls_llm(self, mock_llm_class):
        """validate() should call LLM with cross-check prompt."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"verdict": "approved", "confidence": 0.85, "reasoning": "Agrees"}'
        mock_llm_class.return_value = mock_llm

        with patch("picko.quality.validators.cross_check.get_config") as mock_config:
            mock_config.return_value.summary_llm.provider = "openai"

            validator = CrossCheckValidator(provider="openai", model="gpt-4")
            result = validator.validate(
                title="Test",
                content="Content",
                primary_verdict="approved",
                primary_confidence=0.9,
            )

        assert result["verdict"] == "approved"
        assert "agreement" in result

    def test_validate_calculates_agreement_true(self):
        """validate() should calculate agreement when verdicts match."""
        validator = CrossCheckValidator()

        # Mock the internal _llm attribute directly
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"verdict": "approved", "confidence": 0.85, "reasoning": "Agrees"}'
        validator._llm = mock_llm

        result = validator.validate(
            title="Test",
            content="Content",
            primary_verdict="approved",
            primary_confidence=0.9,
        )

        assert result["agreement"] is True

    def test_validate_calculates_agreement_false(self):
        """validate() should calculate disagreement when verdicts differ."""
        validator = CrossCheckValidator()

        # Mock the internal _llm attribute directly
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"verdict": "rejected", "confidence": 0.7, "reasoning": "Disagrees"}'
        validator._llm = mock_llm

        result = validator.validate(
            title="Test",
            content="Content",
            primary_verdict="approved",
            primary_confidence=0.9,
        )

        assert result["agreement"] is False


class TestCrossCheckJsonParsing:
    """Tests for cross-check JSON parsing."""

    def test_parse_valid_json(self):
        """Should parse valid JSON response."""
        response = '{"verdict": "needs_review", "confidence": 0.6, "reasoning": "Check this"}'
        result = cross_parse_json_response(response)

        assert result["verdict"] == "needs_review"
        assert result["confidence"] == 0.6

    def test_parse_fallback_on_invalid(self):
        """Should return fallback on invalid JSON."""
        result = cross_parse_json_response("not json")

        assert result["verdict"] == "needs_review"
        assert result["confidence"] == 0.5
