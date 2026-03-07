from typing import cast

from picko.video.agents.graph import VideoAgentGraph


def test_reserved_fields_pass_through(creative_brief: dict[str, object]) -> None:
    graph = VideoAgentGraph()
    campaign_context: dict[str, object] = {"utm_campaign": "launch"}
    performance_hints = ["fast_hook", "single_cta"]
    experiment_vars: dict[str, object] = {"variant": "B"}

    result = graph.generate(
        creative_brief,
        campaign_context=campaign_context,
        performance_hints=performance_hints,
        experiment_vars=experiment_vars,
    )

    assert cast(dict[str, object], result["campaign_context"]) == campaign_context
    assert result["performance_hints"] == performance_hints
    assert cast(dict[str, object], result["experiment_vars"]) == experiment_vars
