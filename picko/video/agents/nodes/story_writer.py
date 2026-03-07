from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.story import build_story_plan


@safe_node
def story_writer_node(state: VideoAgentState) -> dict[str, object]:
    return build_story_plan(state)
