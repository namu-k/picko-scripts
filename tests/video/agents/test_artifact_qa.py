from typing import cast

from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.artifact_qa import review_artifacts


def test_artifact_qa_fails_when_assets_missing(base_state) -> None:
    update = review_artifacts(base_state)
    artifact_review = cast(dict[str, object], update["artifact_review"])
    issues = cast(list[dict[str, object]], artifact_review["issues"])
    assert artifact_review["passed"] is False
    assert issues[0]["code"] == "artifact.missing_assets"


def test_artifact_qa_passes_for_valid_assets(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    state["asset_manifest"] = [
        {
            "asset_id": "asset_1",
            "type": "video",
            "shot_ids": ["shot_1"],
            "generation_service": "sora_app",
            "prompt_ref": "shot_1",
            "status": "pending",
            "estimated_cost_usd": 0.02,
        }
    ]
    update = review_artifacts(state)
    artifact_review = cast(dict[str, object], update["artifact_review"])
    assert artifact_review["passed"] is True
