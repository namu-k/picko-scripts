from langgraph.graph import StateGraph

from picko.video.agents.graph import VideoAgentGraph, build_video_agent_graph


def test_graph_builder_returns_state_graph() -> None:
    graph = build_video_agent_graph()
    assert isinstance(graph, StateGraph)
    node_names = set(graph.nodes.keys())
    assert {
        "story_writer",
        "stitch_planner",
        "copywriter",
        "prompt_engineer",
        "audio_director",
        "plan_reviewer",
        "orchestrator",
    }.issubset(node_names)


def test_graph_compiles_and_fan_out_produces_three_outputs(
    creative_brief: dict[str, object],
) -> None:
    engine = VideoAgentGraph()
    result = engine.generate(creative_brief)

    assert result["shot_order"]
    expected = set(result["shot_order"])
    assert set(result["copy_by_shot_id"].keys()) == expected
    assert set(result["prompts_by_shot_id"].keys()) == expected
    assert set(result["audio_by_shot_id"].keys()) == expected
