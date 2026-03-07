from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import TerminalStatus, VideoAgentState


@safe_node
def publish_reviewer_node(state: VideoAgentState) -> dict[str, object]:
    artifact_review = state.get("artifact_review") or {}
    if artifact_review and not artifact_review.get("passed", True):
        return {
            "publish_status": "blocked",
            "terminal_status": TerminalStatus.BLOCKED.value,
        }

    status = state.get("terminal_status", TerminalStatus.PENDING.value)
    if status == TerminalStatus.AUTO_APPROVED.value:
        return {"publish_status": "approved"}
    if status in {
        TerminalStatus.NEEDS_HUMAN_REVIEW.value,
        TerminalStatus.PENDING.value,
    }:
        return {"publish_status": "pending"}
    return {"publish_status": "blocked"}
