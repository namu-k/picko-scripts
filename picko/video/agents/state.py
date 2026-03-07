"""Typed state for the video multi-agent LangGraph workflow."""

import operator
from enum import Enum
from typing import Annotated, TypedDict

JsonDict = dict[str, object]
ShotDict = dict[str, object]
IssueDict = dict[str, object]


class TerminalStatus(str, Enum):
    """Terminal status values for planning graph completion."""

    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    REVISE_REQUIRED = "revise_required"
    BLOCKED = "blocked"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class VideoAgentState(TypedDict):
    # Input
    account_id: str
    intent: str
    services: list[str]
    platforms: list[str]
    execution_mode: str
    creative_brief: JsonDict

    # Context
    identity: JsonDict
    account_config: JsonDict
    weekly_slot: JsonDict | None

    # Reserved fields (pass-through)
    campaign_context: JsonDict | None
    performance_hints: list[str]
    experiment_vars: JsonDict | None

    # Planning
    visual_anchor: str
    shots_by_id: dict[str, ShotDict]
    shot_order: list[str]

    # Production
    production_by_shot_id: dict[str, JsonDict]
    continuity_refs: JsonDict
    stitch_plan: JsonDict
    asset_manifest: list[JsonDict]

    # Copy / prompt / audio
    copy_by_shot_id: dict[str, JsonDict]
    prompts_by_shot_id: dict[str, JsonDict]
    audio_by_shot_id: dict[str, JsonDict]

    # Review
    plan_review: JsonDict
    revision_issues: list[IssueDict]
    artifact_review: JsonDict | None
    publish_status: str

    # Control
    terminal_status: str
    iteration_count: int
    max_iterations: int
    auto_approve_threshold: float
    human_review_threshold: float

    # Cost tracking (reducers for parallel fan-out)
    llm_calls_used: Annotated[int, operator.add]
    tokens_used_estimate: Annotated[int, operator.add]
    cost_usd_estimate: Annotated[float, operator.add]
    cost_budget_usd: float


def assert_shot_key_invariants(state: VideoAgentState) -> None:
    """Validate shot-level key alignment with `shot_order`."""

    shot_ids = set(state.get("shot_order", []))
    checks: dict[str, set[str]] = {
        "shots_by_id": set(state.get("shots_by_id", {}).keys()),
        "production_by_shot_id": set(state.get("production_by_shot_id", {}).keys()),
        "copy_by_shot_id": set(state.get("copy_by_shot_id", {}).keys()),
        "prompts_by_shot_id": set(state.get("prompts_by_shot_id", {}).keys()),
        "audio_by_shot_id": set(state.get("audio_by_shot_id", {}).keys()),
    }

    errors: list[str] = []
    if checks["shots_by_id"] != shot_ids:
        errors.append("shots_by_id keys do not match shot_order")
    for key in (
        "production_by_shot_id",
        "copy_by_shot_id",
        "prompts_by_shot_id",
        "audio_by_shot_id",
    ):
        if checks[key] and checks[key] != shot_ids:
            errors.append(f"{key} keys do not match shot_order")

    if errors:
        raise ValueError("Shot key invariant violations: " + "; ".join(errors))


def create_initial_state(
    account_id: str,
    intent: str,
    services: list[str],
    platforms: list[str],
    execution_mode: str,
    creative_brief: JsonDict,
    identity: JsonDict | None = None,
    account_config: JsonDict | None = None,
    weekly_slot: JsonDict | None = None,
    campaign_context: JsonDict | None = None,
    performance_hints: list[str] | None = None,
    experiment_vars: JsonDict | None = None,
    max_iterations: int = 3,
    auto_approve_threshold: float = 85.0,
    human_review_threshold: float = 60.0,
    cost_budget_usd: float = 1.0,
) -> VideoAgentState:
    """Create a fully populated initial graph state."""

    return {
        "account_id": account_id,
        "intent": intent,
        "services": services,
        "platforms": platforms,
        "execution_mode": execution_mode,
        "creative_brief": creative_brief,
        "identity": identity or {},
        "account_config": account_config or {},
        "weekly_slot": weekly_slot,
        "campaign_context": campaign_context,
        "performance_hints": performance_hints or [],
        "experiment_vars": experiment_vars,
        "visual_anchor": "",
        "shots_by_id": {},
        "shot_order": [],
        "production_by_shot_id": {},
        "continuity_refs": {},
        "stitch_plan": {},
        "asset_manifest": [],
        "copy_by_shot_id": {},
        "prompts_by_shot_id": {},
        "audio_by_shot_id": {},
        "plan_review": {},
        "revision_issues": [],
        "artifact_review": None,
        "publish_status": "pending",
        "terminal_status": TerminalStatus.PENDING.value,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "auto_approve_threshold": auto_approve_threshold,
        "human_review_threshold": human_review_threshold,
        "llm_calls_used": 0,
        "tokens_used_estimate": 0,
        "cost_usd_estimate": 0.0,
        "cost_budget_usd": cost_budget_usd,
    }
