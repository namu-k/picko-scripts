from typing import cast

from picko.video.agents.graph import VideoAgentGraph
from picko.video.agents.state import assert_shot_key_invariants
from picko.video.generator import VideoGenerator


def test_end_to_end_default_path_auto_approves(
    creative_brief: dict[str, object],
) -> None:
    engine = VideoAgentGraph()
    result = engine.generate(creative_brief)

    assert result["terminal_status"] == "auto_approved"
    plan_review = result["plan_review"]
    assert cast(float, plan_review["quality_score"]) >= 85.0
    assert_shot_key_invariants(result)


def test_video_generator_multi_agent_path(creative_brief: dict[str, object]) -> None:
    generator = VideoGenerator(
        account_id=str(creative_brief["account_id"]),
        services=["sora_app"],
        platforms=["instagram_reel"],
        intent="brand",
        use_multi_agent=True,
    )

    plan = generator.generate(validate=False)
    assert plan.render_briefs
    assert plan.production_specs
    assert plan.platform_variants == []
