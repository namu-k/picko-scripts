from typing import cast

from picko.video.agents.nodes.publish_reviewer import publish_reviewer_node
from picko.video.agents.state import VideoAgentState


def test_publish_reviewer_approves_auto_approved(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    state["terminal_status"] = "auto_approved"
    state["artifact_review"] = {"passed": True, "issues": []}
    update = publish_reviewer_node(state)
    assert update["publish_status"] == "approved"


def test_publish_reviewer_blocks_failed_artifact(base_state) -> None:
    state = cast(VideoAgentState, cast(object, dict(base_state)))
    state["artifact_review"] = {
        "passed": False,
        "issues": [{"code": "artifact.missing_assets"}],
    }
    update = publish_reviewer_node(state)
    assert update["publish_status"] == "blocked"
    assert update["terminal_status"] == "blocked"
