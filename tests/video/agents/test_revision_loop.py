from picko.video.agents.graph import VideoAgentGraph
from picko.video.agents.nodes.orchestrator import route_by_revision
from picko.video.agents.tools.orchestrate import orchestrate_revision


def test_route_by_revision_maps_issue_code_to_copy(base_state) -> None:
    base_state["terminal_status"] = "revise_required"
    base_state["revision_issues"] = [
        {
            "code": "copy.missing_caption",
            "severity": "high",
            "target_agents": ["copywriter"],
            "shot_ids": ["shot_1"],
            "description": "caption required",
        }
    ]
    assert route_by_revision(base_state) == "revise_copy"


def test_orchestrate_respects_max_iterations(base_state) -> None:
    base_state["plan_review"] = {
        "quality_score": 10.0,
        "issues": [
            {
                "code": "story.no_shots",
                "severity": "critical",
                "target_agents": ["story_writer"],
                "shot_ids": [],
                "description": "none",
            }
        ],
        "feedback_notes": [],
    }
    base_state["max_iterations"] = 1
    update = orchestrate_revision(base_state)
    assert update["terminal_status"] == "max_iterations_reached"
    assert update["iteration_count"] == 1


def test_graph_loop_stops_without_infinite_cycle(
    creative_brief: dict[str, object],
) -> None:
    engine = VideoAgentGraph()
    result = engine.generate(
        creative_brief,
        auto_approve_threshold=101.0,
        human_review_threshold=101.0,
        max_iterations=2,
    )
    assert result["terminal_status"] == "max_iterations_reached"
    assert result["iteration_count"] == 2
