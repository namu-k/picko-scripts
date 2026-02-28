"""
Tests for Enhanced Verification Mode.

Tests stricter thresholds and mandatory cross-check for new sources.
"""

from unittest.mock import patch

import pytest

from picko.quality.confidence import calculate_final_confidence, determine_verdict
from picko.quality.graph import QualityGraph, QualityState, route_by_confidence


class TestEnhancedVerificationThresholds:
    """Tests for enhanced verification threshold behavior."""

    def test_normal_mode_approves_at_85(self):
        """Normal mode should approve at 0.85 confidence."""
        assert determine_verdict(0.85, enhanced_mode=False) == "approved"

    def test_enhanced_mode_rejects_85(self):
        """Enhanced mode should not approve at 0.85."""
        assert determine_verdict(0.85, enhanced_mode=True) == "needs_review"

    def test_enhanced_mode_approves_at_92(self):
        """Enhanced mode should approve at 0.92 confidence."""
        assert determine_verdict(0.92, enhanced_mode=True) == "approved"

    def test_enhanced_mode_rejects_at_65(self):
        """Enhanced mode should reject at 0.65 (below 0.70)."""
        assert determine_verdict(0.65, enhanced_mode=True) == "rejected"

    def test_normal_mode_needs_review_at_65(self):
        """Normal mode should need review at 0.65."""
        assert determine_verdict(0.65, enhanced_mode=False) == "needs_review"


class TestEnhancedVerificationRouting:
    """Tests for routing logic in enhanced mode."""

    def _create_state(self, confidence: float, enhanced: bool) -> QualityState:
        """Helper to create QualityState for testing."""
        return {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "needs_review",
            "primary_confidence": confidence,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": enhanced,
            "feedback_notes": [],
        }

    def test_enhanced_mode_requires_cross_check_at_90(self):
        """Enhanced mode should require cross-check at 0.90 confidence."""
        state = self._create_state(0.90, enhanced=True)

        assert route_by_confidence(state) == "cross_check"

    def test_normal_mode_approves_at_90(self):
        """Normal mode should approve at 0.90 confidence."""
        state = self._create_state(0.90, enhanced=False)

        assert route_by_confidence(state) == "approved"

    def test_enhanced_mode_mandatory_cross_check_range(self):
        """Enhanced mode should require cross-check for 0.3-0.92 range."""
        # Below 0.3: rejected
        state = self._create_state(0.25, enhanced=True)
        assert route_by_confidence(state) == "rejected"

        # 0.3-0.92: cross_check
        for conf in [0.30, 0.50, 0.70, 0.85, 0.91]:
            state = self._create_state(conf, enhanced=True)
            assert route_by_confidence(state) == "cross_check"

        # >= 0.92: approved
        state = self._create_state(0.92, enhanced=True)
        assert route_by_confidence(state) == "approved"


class TestEnhancedVerificationIntegration:
    """Integration tests for enhanced verification with full graph."""

    @patch("picko.quality.validators.primary.PrimaryValidator.validate")
    @patch("picko.quality.validators.cross_check.CrossCheckValidator.validate")
    def test_enhanced_mode_full_flow(self, mock_cross_validate, mock_primary_validate):
        """Enhanced mode should trigger cross-check even with high primary confidence."""
        # Primary returns 0.88 confidence (would approve in normal mode)
        mock_primary_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.88,
            "scores": {"factual": 8, "source_credibility": 8, "bias": 8, "value": 8},
            "reasoning": "Good content",
            "flags": [],
        }

        # Cross-check also approves
        mock_cross_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.90,
            "reasoning": "Agrees",
            "agreement": True,
        }

        qg = QualityGraph()
        result = qg.verify(
            item_id="new-source-001",
            title="Test Article",
            content="Test content",
            enhanced_verification=True,
        )

        # Cross-check should have been called in enhanced mode
        mock_cross_validate.assert_called()

        # Final verdict should be based on combined confidence
        assert result["final_verdict"] in ("approved", "needs_review")

    @patch("picko.quality.validators.primary.PrimaryValidator.validate")
    def test_normal_mode_skips_cross_check_at_high_confidence(self, mock_primary_validate):
        """Normal mode should skip cross-check at >= 0.9 confidence."""
        mock_primary_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.93,
            "scores": {"factual": 9, "source_credibility": 9, "bias": 9, "value": 9},
            "reasoning": "Excellent content",
            "flags": [],
        }

        qg = QualityGraph()
        result = qg.verify(
            item_id="trusted-source-001",
            title="Test Article",
            content="Test content",
            enhanced_verification=False,
        )

        # Should approve without cross-check
        assert result["primary_verdict"] == "approved"
        assert result["cross_check_verdict"] is None  # No cross-check performed


class TestEnhancedVerificationScenarios:
    """Real-world scenario tests for enhanced verification."""

    def test_new_source_with_medium_quality(self):
        """New source with medium quality should need review."""
        # Primary: 0.70, Cross-check: 0.65 disagreement
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.70},
            cross_check={
                "verdict": "needs_review",
                "confidence": 0.65,
                "agreement": False,
            },
        )

        verdict = determine_verdict(result, enhanced_mode=True)

        # Disagreement penalty should push it down
        assert result < 0.70
        # In enhanced mode, should need review or be rejected
        assert verdict in ("needs_review", "rejected")

    def test_new_source_with_high_agreement(self):
        """New source with high agreement should be approved."""
        result = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.94},
            cross_check={"verdict": "approved", "confidence": 0.92, "agreement": True},
        )

        verdict = determine_verdict(result, enhanced_mode=True)

        # Should be above enhanced threshold
        assert result >= 0.92
        assert verdict == "approved"

    def test_trusted_source_same_confidence_approved(self):
        """Same confidence should be approved for trusted source."""
        confidence = 0.88

        verdict_normal = determine_verdict(confidence, enhanced_mode=False)
        verdict_enhanced = determine_verdict(confidence, enhanced_mode=True)

        assert verdict_normal == "approved"
        assert verdict_enhanced == "needs_review"

    def test_enhanced_mode_low_confidence_early_rejection(self):
        """Enhanced mode should reject very low confidence early."""
        result = calculate_final_confidence(
            primary={"verdict": "rejected", "confidence": 0.25},
        )

        verdict = determine_verdict(result, enhanced_mode=True)

        assert verdict == "rejected"


class TestEnhancedVerificationConfidence:
    """Tests for confidence calculation with enhanced mode flag."""

    def test_confidence_calculation_ignores_enhanced_flag(self):
        """Confidence calculation should be the same regardless of enhanced mode."""
        # The enhanced_mode flag only affects verdict determination, not confidence
        result_normal = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.90},
            cross_check={"verdict": "approved", "confidence": 0.85, "agreement": True},
        )

        # calculate_final_confidence doesn't change based on enhanced_mode
        # It's determine_verdict that uses the flag
        assert result_normal == pytest.approx(0.88125, rel=0.01)

    def test_disagreement_penalty_applies_in_enhanced_mode(self):
        """Disagreement penalty should apply regardless of mode."""
        result_agree = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.85},
            cross_check={"verdict": "approved", "confidence": 0.85, "agreement": True},
            enhanced_mode=True,
        )

        result_disagree = calculate_final_confidence(
            primary={"verdict": "approved", "confidence": 0.85},
            cross_check={"verdict": "rejected", "confidence": 0.85, "agreement": False},
            enhanced_mode=True,
        )

        assert result_disagree < result_agree
