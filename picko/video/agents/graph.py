from typing import cast

from langgraph.graph import END, StateGraph

from picko.video.agents.state import TerminalStatus, VideoAgentState, create_initial_state


def build_video_agent_graph() -> StateGraph:
    from picko.video.agents.nodes.audio_director import audio_director_node
    from picko.video.agents.nodes.copywriter import copywriter_node
    from picko.video.agents.nodes.orchestrator import orchestrator_node, route_by_revision
    from picko.video.agents.nodes.plan_reviewer import plan_reviewer_node
    from picko.video.agents.nodes.prompt_engineer import prompt_engineer_node
    from picko.video.agents.nodes.stitch_planner import stitch_planner_node
    from picko.video.agents.nodes.story_writer import story_writer_node

    builder = StateGraph(VideoAgentState)
    builder.add_node("story_writer", story_writer_node)
    builder.add_node("stitch_planner", stitch_planner_node)
    builder.add_node("copywriter", copywriter_node)
    builder.add_node("prompt_engineer", prompt_engineer_node)
    builder.add_node("audio_director", audio_director_node)
    builder.add_node("plan_reviewer", plan_reviewer_node)
    builder.add_node("orchestrator", orchestrator_node)

    builder.set_entry_point("story_writer")
    builder.add_edge("story_writer", "stitch_planner")

    builder.add_edge("stitch_planner", "copywriter")
    builder.add_edge("stitch_planner", "prompt_engineer")
    builder.add_edge("stitch_planner", "audio_director")

    builder.add_edge("copywriter", "plan_reviewer")
    builder.add_edge("prompt_engineer", "plan_reviewer")
    builder.add_edge("audio_director", "plan_reviewer")

    builder.add_edge("plan_reviewer", "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_by_revision,
        {
            "auto_approved": END,
            "needs_human_review": END,
            "max_iterations_reached": END,
            "blocked": END,
            "revise_story": "story_writer",
            "revise_stitch": "stitch_planner",
            "revise_copy": "copywriter",
            "revise_prompt": "prompt_engineer",
            "revise_audio": "audio_director",
        },
    )

    return builder


class VideoAgentGraph:
    def __init__(self) -> None:
        self.graph = build_video_agent_graph()
        self.compiled = self.graph.compile()

    def generate(
        self,
        creative_brief: dict[str, object],
        identity: dict[str, object] | None = None,
        account_config: dict[str, object] | None = None,
        weekly_slot: dict[str, object] | None = None,
        campaign_context: dict[str, object] | None = None,
        performance_hints: list[str] | None = None,
        experiment_vars: dict[str, object] | None = None,
        max_iterations: int = 3,
        auto_approve_threshold: float = 85.0,
        human_review_threshold: float = 60.0,
        cost_budget_usd: float = 1.0,
    ) -> VideoAgentState:
        account_id = creative_brief.get("account_id", "")
        intent = creative_brief.get("intent", "brand")
        services = creative_brief.get("services", ["sora_app"])
        platforms = creative_brief.get("platforms", ["instagram_reel"])
        execution_mode = creative_brief.get("execution_mode", "manual_assisted")

        if not isinstance(account_id, str):
            account_id = ""
        if not isinstance(intent, str):
            intent = "brand"
        if not isinstance(services, list):
            services = ["sora_app"]
        if not isinstance(platforms, list):
            platforms = ["instagram_reel"]
        if not isinstance(execution_mode, str):
            execution_mode = "manual_assisted"

        services = [str(item) for item in services]
        platforms = [str(item) for item in platforms]

        initial_state = create_initial_state(
            account_id=account_id,
            intent=intent,
            services=services,
            platforms=platforms,
            execution_mode=execution_mode,
            creative_brief=creative_brief,
            identity=identity,
            account_config=account_config,
            weekly_slot=weekly_slot,
            campaign_context=campaign_context,
            performance_hints=performance_hints,
            experiment_vars=experiment_vars,
            max_iterations=max_iterations,
            auto_approve_threshold=auto_approve_threshold,
            human_review_threshold=human_review_threshold,
            cost_budget_usd=cost_budget_usd,
        )
        return cast(VideoAgentState, self.compiled.invoke(initial_state))


__all__ = ["TerminalStatus", "VideoAgentGraph", "build_video_agent_graph"]
