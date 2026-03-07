from typing import Any, cast

from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.stitch import build_stitch_plan
from picko.video.agents.tools.story import build_story_plan


def test_stitch_tool_generates_shot_keyed_structures(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    cast(dict[str, Any], cast(object, state)).update(build_story_plan(state))
    update = build_stitch_plan(state)

    shot_order = state["shot_order"]
    production = cast(dict[str, dict[str, object]], update["production_by_shot_id"])
    stitch_plan = cast(dict[str, object], update["stitch_plan"])
    segments = cast(list[dict[str, object]], stitch_plan["segments"])
    manifest = cast(list[dict[str, object]], update["asset_manifest"])
    assert set(production.keys()) == set(shot_order)
    assert len(segments) == len(shot_order)
    assert len(manifest) == len(shot_order)
