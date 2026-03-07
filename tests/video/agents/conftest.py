from typing import cast

import pytest

from picko.video.agents.state import VideoAgentState, create_initial_state


@pytest.fixture
def creative_brief() -> dict[str, object]:
    return {
        "account_id": "acct_demo",
        "intent": "brand",
        "objective": "Increase trial signups",
        "audience": "solo creators",
        "message_pillar": "fast workflow",
        "proof_points": ["simple", "reliable"],
        "target_duration_sec": 15.0,
        "services": ["sora_app"],
        "platforms": ["instagram_reel"],
        "execution_mode": "manual_assisted",
    }


@pytest.fixture
def base_state(creative_brief: dict[str, object]) -> VideoAgentState:
    return create_initial_state(
        account_id=cast(str, creative_brief["account_id"]),
        intent=cast(str, creative_brief["intent"]),
        services=cast(list[str], creative_brief["services"]),
        platforms=cast(list[str], creative_brief["platforms"]),
        execution_mode=cast(str, creative_brief["execution_mode"]),
        creative_brief=creative_brief,
        campaign_context={"campaign": "spring"},
        performance_hints=["hook_first_2s"],
        experiment_vars={"variant": "A"},
    )
