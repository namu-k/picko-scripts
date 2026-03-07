from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import VideoAgentState
from picko.video.agents.tools.review import review_plan


@safe_node
def plan_reviewer_node(state: VideoAgentState) -> dict[str, object]:
    return review_plan(state)
