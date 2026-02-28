"""
Confidence Calculator - Combine multi-step validation results.

Calculates final confidence scores based on:
- Primary validation
- Cross-check validation (optional)
- External validation (optional)

Weights are automatically normalized based on which steps were used.
"""

from typing import Any

from picko.logger import get_logger

logger = get_logger("quality.confidence")


def calculate_final_confidence(
    primary: dict[str, Any],
    cross_check: dict[str, Any] | None = None,
    external: dict[str, Any] | None = None,
    enhanced_mode: bool = False,
) -> float:
    """
    Calculate final confidence from multi-step validation results.

    Weights (automatically normalized based on available steps):
    - primary only:                      primary=100%
    - primary + cross_check:             primary=62.5%, cross_check=37.5%
    - primary + cross_check + external:  primary=50%, cross_check=30%, external=20%

    Cross-check disagreement applies 50% penalty to cross_check contribution.

    Args:
        primary: Primary validation result with 'verdict' and 'confidence'
        cross_check: Optional cross-check result with 'verdict', 'confidence', 'agreement'
        external: Optional external validation result with 'confidence'
        enhanced_mode: If True, use stricter thresholds for new sources

    Returns:
        Final confidence score (0.0-1.0)
    """
    # Determine weights based on available steps
    if external and cross_check:
        weights = {"primary": 0.50, "cross_check": 0.30, "external": 0.20}
    elif cross_check:
        weights = {"primary": 0.625, "cross_check": 0.375, "external": 0.0}
    else:
        weights = {"primary": 1.0, "cross_check": 0.0, "external": 0.0}

    # Calculate weighted sum
    primary_confidence = primary.get("confidence", 0.5)
    if not isinstance(primary_confidence, (int, float)):
        primary_confidence = 0.5

    total = float(primary_confidence) * weights["primary"]

    if cross_check:
        cross_check_confidence = cross_check.get("confidence", 0.5)
        if not isinstance(cross_check_confidence, (int, float)):
            cross_check_confidence = 0.5

        # Agreement multiplier: 1.0 if agreed, 0.5 if disagreed
        agreement = cross_check.get("agreement", True)
        agreement_mult = 1.0 if agreement else 0.5

        total += float(cross_check_confidence) * weights["cross_check"] * agreement_mult

        if not agreement:
            logger.info("Cross-check disagreement detected, applied 50% penalty")
    if external:
        external_confidence = external.get("confidence", 0.5)
        if not isinstance(external_confidence, (int, float)):
            external_confidence = 0.5
        total += float(external_confidence) * weights["external"]

    # Clamp to valid range
    final_confidence = max(0.0, min(1.0, total))

    logger.debug(
        f"Confidence calculation: primary={primary_confidence:.2f}, "
        f"cross_check={cross_check.get('confidence') if cross_check else 'N/A'}, "
        f"external={external.get('confidence') if external else 'N/A'}, "
        f"final={final_confidence:.2f}"
    )

    return final_confidence


def determine_verdict(
    confidence: float,
    enhanced_mode: bool = False,
) -> str:
    """
    Determine final verdict based on confidence score.

    Thresholds:
    - Normal mode: >= 0.85 approved, >= 0.60 needs_review, < 0.60 rejected
    - Enhanced mode: >= 0.92 approved, >= 0.70 needs_review, < 0.70 rejected

    Args:
        confidence: Final confidence score (0.0-1.0)
        enhanced_mode: If True, use stricter thresholds for new sources

    Returns:
        Verdict string: "approved", "needs_review", or "rejected"
    """
    if enhanced_mode:
        # Stricter thresholds for new/unknown sources
        if confidence >= 0.92:
            return "approved"
        elif confidence >= 0.70:
            return "needs_review"
        else:
            return "rejected"
    else:
        # Normal thresholds
        if confidence >= 0.85:
            return "approved"
        elif confidence >= 0.60:
            return "needs_review"
        else:
            return "rejected"


def get_verdict_thresholds(enhanced_mode: bool = False) -> dict[str, float]:
    """
    Get current verdict thresholds.

    Args:
        enhanced_mode: If True, return stricter thresholds

    Returns:
        Dict with 'approved' and 'needs_review' thresholds
    """
    if enhanced_mode:
        return {
            "approved": 0.92,
            "needs_review": 0.70,
        }
    else:
        return {
            "approved": 0.85,
            "needs_review": 0.60,
        }
