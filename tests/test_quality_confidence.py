"""
Tests for Quality Confidence Calculator.

Tests weight normalization, agreement penalty, and verdict determination.
"""

import pytest

from picko.quality.confidence import calculate_final_confidence, determine_verdict, get_verdict_thresholds


class TestCalculateFinalConfidence:
    """Tests for confidence calculation with automatic weight normalization."""

    def test_primary_only_100_percent(self):
        """Primary only should use 100% weight."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.9},
        )

        # Should be exactly the primary confidence
        assert result == 0.9

    def test_primary_cross_check_62_37_split(self):
        """Primary + cross-check should use 62.5%/37.5% weights."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.8},
            cross_check={"verdict": "approved", "confidence": 0.8, "agreement": True},
        )

        # 0.8 * 0.625 + 0.8 * 0.375 = 0.5 + 0.3 = 0.8
        assert result == pytest.approx(0.8, rel=0.01)

    def test_primary_cross_external_50_30_20_split(self):
        """Primary + cross-check + external should use 50%/30%/20% weights."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.9},
            cross_check={"verdict": "approved", "confidence": 0.9, "agreement": True},
            external={"confidence": 0.9},
        )

        # 0.9 * 0.5 + 0.9 * 0.3 + 0.9 * 0.2 = 0.45 + 0.27 + 0.18 = 0.9
        assert result == pytest.approx(0.9, rel=0.01)

    def test_disagreement_applies_penalty(self):
        """Cross-check disagreement should apply 50% penalty to cross-check contribution."""
        result_agree = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.8},
            cross_check={"verdict": "approved", "confidence": 0.8, "agreement": True},
        )

        result_disagree = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.8},
            cross_check={"verdict": "rejected", "confidence": 0.8, "agreement": False},
        )

        # Disagreement should reduce confidence
        assert result_disagree < result_agree

        # Calculate expected: 0.8 * 0.625 + (0.8 * 0.375 * 0.5) = 0.5 + 0.15 = 0.65
        assert result_disagree == pytest.approx(0.65, rel=0.01)

    def test_confidence_clamped_to_range(self):
        """Confidence should be clamped to 0.0-1.0."""
        # Very high values
        result_high = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 1.5},
        )
        assert result_high == 1.0

        # Negative values
        result_low = calculate_final_confidence(
            primary={"verdict": "rejected", "confidence": -0.5},
        )
        assert result_low == 0.0

    def test_invalid_confidence_uses_default(self):
        """Invalid confidence values should use default 0.5."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": "invalid"},
        )

        # Should use 0.5 as default
        assert result == 0.5

    def test_missing_confidence_uses_default(self):
        """Missing confidence should use default 0.5."""
        result = calculate_final_confidence(
            primary={"verdict": "approved"},
        )

        assert result == 0.5


class TestDetermineVerdict:
    """Tests for verdict determination from confidence."""

    def test_high_confidence_approved(self):
        """High confidence (>= 0.85) should be approved."""
        assert determine_verdict(0.85) == "approved"
        assert determine_verdict(0.95) == "approved"
        assert determine_verdict(1.0) == "approved"

    def test_medium_confidence_needs_review(self):
        """Medium confidence (0.60-0.85) should need review."""
        assert determine_verdict(0.60) == "needs_review"
        assert determine_verdict(0.70) == "needs_review"
        assert determine_verdict(0.84) == "needs_review"

    def test_low_confidence_rejected(self):
        """Low confidence (< 0.60) should be rejected."""
        assert determine_verdict(0.59) == "rejected"
        assert determine_verdict(0.40) == "rejected"
        assert determine_verdict(0.0) == "rejected"

    def test_enhanced_mode_stricter_thresholds(self):
        """Enhanced mode should use stricter thresholds."""
        # 0.90 would be approved in normal mode, but needs_review in enhanced
        assert determine_verdict(0.90, enhanced_mode=True) == "needs_review"

        # 0.92 should be approved in enhanced mode
        assert determine_verdict(0.92, enhanced_mode=True) == "approved"

        # 0.65 would be needs_review in normal mode, but rejected in enhanced
        assert determine_verdict(0.65, enhanced_mode=True) == "rejected"

        # 0.70 should be needs_review in enhanced mode
        assert determine_verdict(0.70, enhanced_mode=True) == "needs_review"

    def test_boundary_values_normal_mode(self):
        """Test exact boundary values in normal mode."""
        assert determine_verdict(0.85) == "approved"  # Exact boundary
        assert determine_verdict(0.60) == "needs_review"  # Exact boundary
        assert determine_verdict(0.5999) == "rejected"  # Just below

    def test_boundary_values_enhanced_mode(self):
        """Test exact boundary values in enhanced mode."""
        assert determine_verdict(0.92, enhanced_mode=True) == "approved"  # Exact boundary
        assert determine_verdict(0.70, enhanced_mode=True) == "needs_review"  # Exact boundary
        assert determine_verdict(0.6999, enhanced_mode=True) == "rejected"  # Just below


class TestGetVerdictThresholds:
    """Tests for threshold retrieval."""

    def test_normal_thresholds(self):
        """Should return normal thresholds by default."""
        thresholds = get_verdict_thresholds()

        assert thresholds["approved"] == 0.85
        assert thresholds["needs_review"] == 0.60

    def test_enhanced_thresholds(self):
        """Should return stricter thresholds in enhanced mode."""
        thresholds = get_verdict_thresholds(enhanced_mode=True)

        assert thresholds["approved"] == 0.92
        assert thresholds["needs_review"] == 0.70


class TestConfidenceCalculationIntegration:
    """Integration tests for confidence calculation scenarios."""

    def test_scenario_high_quality_agreement(self):
        """High quality content with agreement should have high confidence."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.95},
            cross_check={"verdict": "approved", "confidence": 0.92, "agreement": True},
        )

        verdict = determine_verdict(result)

        assert result > 0.9
        assert verdict == "approved"

    def test_scenario_medium_quality_disagreement(self):
        """Medium quality with disagreement should reduce confidence."""
        result = calculate_final_confidence(
            primary={"verdict": "needs_review", "confidence": 0.75},
            cross_check={"verdict": "approved", "confidence": 0.80, "agreement": False},
        )

        verdict = determine_verdict(result)

        # Disagreement penalty should push it down
        assert result < 0.75
        assert verdict in ("needs_review", "rejected")

    def test_scenario_low_quality(self):
        """Low quality content should be rejected."""
        result = calculate_final_confidence(
            primary={"verdict": "rejected", "confidence": 0.45},
        )

        verdict = determine_verdict(result)

        assert result == 0.45
        assert verdict == "rejected"

    def test_scenario_enhanced_mode_with_cross_check(self):
        """Enhanced mode should require higher confidence."""
        # In enhanced mode, even with agreement, need higher threshold
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.88},
            cross_check={"verdict": "approved", "confidence": 0.85, "agreement": True},
        )

        verdict_normal = determine_verdict(result, enhanced_mode=False)
        verdict_enhanced = determine_verdict(result, enhanced_mode=True)

        # Should be approved in normal mode, needs_review in enhanced
        assert verdict_normal == "approved"
        assert verdict_enhanced == "needs_review"
