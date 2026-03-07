from picko.video.agents.nodes.base import safe_node
from picko.video.agents.state import TerminalStatus, VideoAgentState
from picko.video.agents.tools.orchestrate import orchestrate_revision

_CODE_AGENT_MAP = {
    "story.": "story_writer",
    "continuity.": "stitch_planner",
    "production.": "stitch_planner",
    "copy.": "copywriter",
    "prompt.": "prompt_engineer",
    "audio.": "audio_director",
}
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_AGENT_ORDER = {
    "story_writer": 0,
    "stitch_planner": 1,
    "copywriter": 2,
    "prompt_engineer": 2,
    "audio_director": 2,
}


def _issue_rank(issue: dict[str, object]) -> int:
    severity_obj = issue.get("severity", "low")
    severity = severity_obj if isinstance(severity_obj, str) else "low"
    return _SEVERITY_ORDER.get(severity, 3)


def _resolve_revision_targets(issues: list[dict[str, object]]) -> list[str]:
    ordered = sorted(issues, key=_issue_rank)
    targets: list[str] = []
    for issue in ordered:
        code_obj = issue.get("code", "")
        code = str(code_obj)
        for prefix, agent in _CODE_AGENT_MAP.items():
            if code.startswith(prefix) and agent not in targets:
                targets.append(agent)
        target_agents = issue.get("target_agents", [])
        if not isinstance(target_agents, list):
            target_agents = []
        for agent in [str(item) for item in target_agents]:
            if agent not in targets:
                targets.append(agent)
    targets.sort(key=lambda name: _AGENT_ORDER.get(name, 99))
    return targets


def route_by_revision(state: VideoAgentState) -> str:
    status = state.get("terminal_status", TerminalStatus.PENDING.value)
    if status == TerminalStatus.AUTO_APPROVED.value:
        return "auto_approved"
    if status == TerminalStatus.NEEDS_HUMAN_REVIEW.value:
        return "needs_human_review"
    if status == TerminalStatus.MAX_ITERATIONS_REACHED.value:
        return "max_iterations_reached"
    if status == TerminalStatus.BLOCKED.value:
        return "blocked"

    targets = _resolve_revision_targets(state.get("revision_issues", []))
    if not targets:
        return "revise_story"

    route_map = {
        "story_writer": "revise_story",
        "stitch_planner": "revise_stitch",
        "copywriter": "revise_copy",
        "prompt_engineer": "revise_prompt",
        "audio_director": "revise_audio",
    }
    return route_map.get(targets[0], "revise_story")


@safe_node
def orchestrator_node(state: VideoAgentState) -> dict[str, object]:
    return orchestrate_revision(state)
