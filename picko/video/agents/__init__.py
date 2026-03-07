"""
Picko Video Agents - Multi-agent video generation system

This package implements the multi-agent video generation architecture using LangGraph.
It provides shot-level video planning with shot_id-based state management.
"""

from picko.video.agents.providers import (
    PROVIDER_CAPABILITIES,
    ProviderCapability,
    get_providers_for_mode,
    get_providers_for_mode_and_services,
)
from picko.video.agents.schemas import (
    AssetItem,
    AudioSpec,
    ContinuityRefs,
    CopyBundle,
    CreativeBrief,
    ProductionSpec,
    PromptBundle,
    RenderRecipe,
    ReviewIssue,
    ShotDraft,
    StitchPlan,
    StitchSegment,
)
from picko.video.agents.state import TerminalStatus, VideoAgentState

__all__ = [
    # State
    "VideoAgentState",
    "TerminalStatus",
    # Schemas
    "CreativeBrief",
    "ShotDraft",
    "ProductionSpec",
    "RenderRecipe",
    "CopyBundle",
    "PromptBundle",
    "AudioSpec",
    "ReviewIssue",
    "StitchPlan",
    "StitchSegment",
    "AssetItem",
    "ContinuityRefs",
    # Providers
    "ProviderCapability",
    "PROVIDER_CAPABILITIES",
    "get_providers_for_mode",
    "get_providers_for_mode_and_services",
]
