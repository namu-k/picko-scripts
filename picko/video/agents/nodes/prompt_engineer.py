from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.prompt import build_prompt_bundles


@safe_node
def prompt_engineer_node(state: VideoAgentState) -> dict[str, object]:
    return build_prompt_bundles(state)
