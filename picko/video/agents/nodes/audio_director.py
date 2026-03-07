from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.audio import build_audio_specs


@safe_node
def audio_director_node(state: VideoAgentState) -> dict[str, object]:
    return build_audio_specs(state)
