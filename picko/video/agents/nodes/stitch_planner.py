from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.stitch import build_stitch_plan


@safe_node
def stitch_planner_node(state: VideoAgentState) -> dict[str, object]:
    return build_stitch_plan(state)
