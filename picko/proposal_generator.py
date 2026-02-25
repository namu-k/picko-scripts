"""Proposal generator for multimedia content."""

from dataclasses import dataclass, field
from typing import Any

from .logger import get_logger
from .multimedia_io import MultimediaInput

logger = get_logger("proposal_generator")


@dataclass
class Proposal:
    """LLM-generated proposal for multimedia content."""

    input_id: str
    content_type: str  # quote | social_quote | card | modern_card | list | data | carousel
    template: str
    background_prompt: str
    overlay_text: str
    style_preset: str
    channels: list[str]
    layout_hints: list[str] = field(default_factory=list)


def _determine_content_type(input_data: MultimediaInput) -> str:
    """Determine content type based on input characteristics.

    Priority order:
    1. List indicators in concept (e.g., "5가지", "3단계")
    2. Data indicators in concept or overlay (e.g., "200%", "증가")
    3. Hero/feature indicators → modern_card
    4. Social channels with short quote → social_quote
    5. Short quote-like text in overlay (< 100 chars) → quote
    6. Default to card
    """
    overlay = input_data.overlay_text or ""
    concept = input_data.concept or ""
    combined = concept + overlay
    channels = input_data.channels or []

    # Normalize channels for matching
    social_channels = {"instagram", "linkedin", "threads", "twitter", "x"}

    # List indicators → list (check first for explicit list content)
    list_indicators = [
        "단계", "가지", "방법", "체크리스트",
        "실수", "팁", "전략", "원칙", "습관",
        "things", "steps", "ways", "tips",
    ]
    if any(ind in concept for ind in list_indicators):
        return "list"

    # Number/data indicators → data
    data_indicators = ["%", "배", "증가", "감소", "수치", "달성", "기록", "突破"]
    if any(ind in combined for ind in data_indicators):
        return "data"

    # Hero/feature indicators → modern_card
    hero_indicators = ["핵심", "소개", "가이드", "특집", "특집", "hero", "feature"]
    if any(ind in concept.lower() for ind in hero_indicators):
        return "modern_card"

    # Social channels with short quote → social_quote
    has_social_channel = bool(set(ch.lower() for ch in channels) & social_channels)
    if has_social_channel and overlay and len(overlay) < 100:
        return "social_quote"

    # Short quote-like text → quote
    if overlay and len(overlay) < 100:
        return "quote"

    # Default to card
    return "card"


def _generate_background_prompt(
    content_type: str,
    concept: str,
    style_preset: str,
) -> str:
    """Generate background image prompt."""
    base_prompts = {
        "quote": "minimal gradient background, clean, professional, soft tones for quote overlay",
        "social_quote": "vibrant gradient background, social media style, engaging colors",
        "card": "clean background for content card, subtle texture, professional",
        "modern_card": "dark premium background, gradient hero section, modern tech aesthetic",
        "list": "minimal infographic background, grid-ready, clean whitespace",
        "data": "data visualization background, chart-friendly, minimal dark theme",
        "carousel": "consistent series background, cohesive design",
    }
    return base_prompts.get(content_type, base_prompts["card"])


def generate_proposal(
    input_data: MultimediaInput,
    account_config: dict[str, Any],
    references: list[str],
) -> Proposal:
    """Generate proposal for multimedia content.

    Args:
        input_data: Multimedia input containing content and metadata
        account_config: Account configuration (currently unused, reserved for
            future enhancements like style customization from account settings)
        references: List of reference document contents (currently unused,
            reserved for future enhancements like style extraction)

    Returns:
        Proposal with content type, template, and rendering parameters.

    Note:
        account_config and references are accepted for API compatibility and
        future enhancement. They are not currently used in proposal generation
        but may be used for:
        - Style preset selection based on account preferences
        - Content tone adjustment from reference documents
        - Channel-specific customization from account settings
    """
    content_type = _determine_content_type(input_data)

    template_map = {
        "quote": "quote.html",
        "social_quote": "social_quote.html",
        "card": "card.html",
        "modern_card": "modern_card.html",
        "list": "list.html",
        "data": "data.html",
        "carousel": "carousel.html",
    }

    style_presets = {
        "quote": "minimal_infographic",
        "social_quote": "social_gradient",
        "card": "editorial_photo",
        "modern_card": "dark_gradient",
        "list": "minimal_infographic",
        "data": "data_card",
        "carousel": "minimal_infographic",
    }

    background_prompt = _generate_background_prompt(
        content_type,
        input_data.concept,
        style_presets.get(content_type, "minimal_infographic"),
    )

    return Proposal(
        input_id=input_data.id,
        content_type=content_type,
        template=template_map.get(content_type, "card.html"),
        background_prompt=background_prompt,
        overlay_text=input_data.overlay_text or input_data.concept,
        style_preset=style_presets.get(content_type, "minimal_infographic"),
        channels=input_data.channels,
        layout_hints=[],
    )
