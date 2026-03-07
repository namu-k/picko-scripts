from typing import Any, cast

from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.audio import build_audio_specs
from picko.video.agents.tools.copy import build_copy_bundles
from picko.video.agents.tools.prompt import build_prompt_bundles
from picko.video.agents.tools.review import review_plan
from picko.video.agents.tools.stitch import build_stitch_plan
from picko.video.agents.tools.story import build_story_plan


def test_review_plan_passes_when_all_sections_exist(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    cast(dict[str, Any], cast(object, state)).update(build_story_plan(state))
    cast(dict[str, Any], cast(object, state)).update(build_stitch_plan(state))
    cast(dict[str, Any], cast(object, state)).update(build_copy_bundles(state))
    cast(dict[str, Any], cast(object, state)).update(build_prompt_bundles(state))
    cast(dict[str, Any], cast(object, state)).update(build_audio_specs(state))

    review = review_plan(state)
    plan_review = cast(dict[str, object], review["plan_review"])
    assert cast(list[dict[str, object]], plan_review["issues"]) == []
    assert cast(float, plan_review["quality_score"]) == 100.0


def test_review_plan_flags_missing_copy(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    cast(dict[str, Any], cast(object, state)).update(build_story_plan(state))
    cast(dict[str, Any], cast(object, state)).update(build_stitch_plan(state))
    cast(dict[str, Any], cast(object, state)).update(build_prompt_bundles(state))
    cast(dict[str, Any], cast(object, state)).update(build_audio_specs(state))
    state["copy_by_shot_id"] = {}

    review = review_plan(state)
    plan_review = cast(dict[str, object], review["plan_review"])
    issues = cast(list[dict[str, object]], plan_review["issues"])
    codes = {cast(str, issue["code"]) for issue in issues}
    assert "copy.missing_caption" in codes
