from picko.video.agents.graph import VideoAgentGraph
from picko.video.agents.runtime import apply_publish_decision, build_render_briefs, review_rendered_artifact
from picko.video.generator import VideoGenerator


def test_revision_runtime_hits_cap_and_terminates(
    creative_brief: dict[str, object],
) -> None:
    graph = VideoAgentGraph()
    result = graph.generate(
        creative_brief,
        auto_approve_threshold=200.0,
        human_review_threshold=200.0,
        max_iterations=3,
    )

    assert result["terminal_status"] == "max_iterations_reached"
    assert result["iteration_count"] == 3


def test_runtime_entrypoints_with_plan(creative_brief: dict[str, object]) -> None:
    graph = VideoAgentGraph()
    state = graph.generate(creative_brief)

    briefs = build_render_briefs(state)
    assert briefs
    assert briefs[0]["shot_id"] == state["shot_order"][0]

    generator = VideoGenerator(
        account_id=str(creative_brief["account_id"]),
        services=["sora_app"],
        platforms=["instagram_reel"],
        intent="brand",
        use_multi_agent=True,
    )
    plan = generator._state_to_plan(state)

    artifact_review = review_rendered_artifact(plan, "rendered.mp4")
    assert artifact_review["passed"] is True

    publish = apply_publish_decision(plan, "approved")
    assert publish["publish_status"] == "approved"
