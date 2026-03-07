from picko.video.agents.state import VideoAgentState


def build_story_plan(state: VideoAgentState) -> dict[str, object]:
    brief_obj = state.get("creative_brief", {})
    brief: dict[str, object] = brief_obj if isinstance(brief_obj, dict) else {}
    raw_duration = brief.get("target_duration_sec", 15.0)
    target_duration = 15.0
    if isinstance(raw_duration, (int, float, str)):
        target_duration = float(raw_duration)
    shot_count = max(3, min(6, int(round(target_duration / 5.0))))

    existing_order = state.get("shot_order", [])
    shot_order = existing_order or [f"shot_{i}" for i in range(1, shot_count + 1)]
    purpose_cycle = ["hook", "main", "cta", "detail", "detail", "outro"]

    objective = brief.get("objective", "Share one clear message")
    message_pillar = brief.get("message_pillar", state.get("intent", "brand"))
    visual_anchor = f"{message_pillar} | {objective}".strip(" |")

    shots_by_id: dict[str, dict[str, object]] = {}
    for index, shot_id in enumerate(shot_order):
        shots_by_id[shot_id] = {
            "shot_id": shot_id,
            "purpose": purpose_cycle[index % len(purpose_cycle)],
            "scene_description": f"Scene {index + 1} for {message_pillar}",
            "subject": brief.get("audience", "general audience"),
            "setting": "studio",
            "lighting": "soft",
            "camera_intent": "steady",
            "motion_type": "static",
            "duration_sec": round(target_duration / len(shot_order), 2),
            "overlay_text_needed": index == 0,
            "continuity_constraints": ["keep same subject identity"],
            "risk_flags": [],
        }

    return {
        "visual_anchor": visual_anchor,
        "shots_by_id": shots_by_id,
        "shot_order": shot_order,
        "llm_calls_used": 1,
        "tokens_used_estimate": 160,
        "cost_usd_estimate": 0.01,
    }
