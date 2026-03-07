from collections.abc import Callable
from functools import wraps
from typing import Any

from picko.video.agents.state import TerminalStatus, VideoAgentState


def safe_node(
    func: Callable[[VideoAgentState], dict[str, Any]],
) -> Callable[[VideoAgentState], dict[str, Any]]:
    @wraps(func)
    def wrapper(state: VideoAgentState) -> dict[str, Any]:
        try:
            return func(state)
        except Exception as exc:
            return {
                "revision_issues": [
                    {
                        "code": "orchestrator.node_error",
                        "severity": "critical",
                        "target_agents": ["story_writer"],
                        "description": str(exc),
                        "shot_ids": [],
                    }
                ],
                "terminal_status": TerminalStatus.REVISE_REQUIRED.value,
            }

    return wrapper
