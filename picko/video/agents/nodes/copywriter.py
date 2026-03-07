from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.copy import build_copy_bundles


@safe_node
def copywriter_node(state: VideoAgentState) -> dict[str, object]:
    return build_copy_bundles(state)
