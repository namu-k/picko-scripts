from picko.video.agents.state import TerminalStatus, VideoAgentState


def orchestrate_revision(state: VideoAgentState) -> dict[str, object]:
    plan_review_obj = state.get("plan_review", {})
    plan_review = plan_review_obj if isinstance(plan_review_obj, dict) else {}
    issues_obj = plan_review.get("issues", state.get("revision_issues", []))
    issues = [item for item in issues_obj if isinstance(item, dict)] if isinstance(issues_obj, list) else []
    quality_obj = plan_review.get("quality_score", 0.0)
    score = float(quality_obj) if isinstance(quality_obj, (int, float, str)) else 0.0

    iteration_count = int(state.get("iteration_count", 0))
    next_iteration = iteration_count + 1
    max_iterations = int(state.get("max_iterations", 3))
    auto_threshold_obj = state.get("auto_approve_threshold", 85.0)
    human_threshold_obj = state.get("human_review_threshold", 60.0)
    auto_threshold = float(auto_threshold_obj) if isinstance(auto_threshold_obj, (int, float, str)) else 85.0
    human_threshold = float(human_threshold_obj) if isinstance(human_threshold_obj, (int, float, str)) else 60.0

    if score >= auto_threshold:
        terminal_status = TerminalStatus.AUTO_APPROVED.value
    elif score >= human_threshold:
        terminal_status = TerminalStatus.NEEDS_HUMAN_REVIEW.value
    elif next_iteration >= max_iterations:
        terminal_status = TerminalStatus.MAX_ITERATIONS_REACHED.value
    elif issues:
        terminal_status = TerminalStatus.REVISE_REQUIRED.value
    else:
        terminal_status = TerminalStatus.REVISE_REQUIRED.value

    return {
        "terminal_status": terminal_status,
        "revision_issues": issues,
        "iteration_count": next_iteration,
    }
