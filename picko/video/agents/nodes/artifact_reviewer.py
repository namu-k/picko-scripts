from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.artifact_qa import review_artifacts


@safe_node
def artifact_reviewer_node(state: VideoAgentState) -> dict[str, object]:
    return review_artifacts(state)
