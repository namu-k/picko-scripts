from typing import cast

from picko.video.agents.graph import VideoAgentGraph
from picko.video.agents.state import create_initial_state


def test_create_initial_state_from_brief_fields(
    creative_brief: dict[str, object],
) -> None:
    state = create_initial_state(
        account_id=cast(str, creative_brief["account_id"]),
        intent=cast(str, creative_brief["intent"]),
        services=cast(list[str], creative_brief["services"]),
        platforms=cast(list[str], creative_brief["platforms"]),
        execution_mode=cast(str, creative_brief["execution_mode"]),
        creative_brief=creative_brief,
    )
    assert state["account_id"] == "acct_demo"
    assert state["intent"] == "brand"


def test_graph_generate_accepts_brief_payload(
    creative_brief: dict[str, object],
) -> None:
    graph = VideoAgentGraph()
    result = graph.generate(creative_brief)
    assert result["creative_brief"]["objective"] == "Increase trial signups"
