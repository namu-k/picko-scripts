from picko.video.agents.state import VideoAgentState


def build_prompt_bundles(state: VideoAgentState) -> dict[str, object]:
    shot_order = state.get("shot_order", [])
    shots_by_id = state.get("shots_by_id", {})
    visual_anchor = state.get("visual_anchor", "")

    prompts_by_shot_id: dict[str, dict[str, object]] = {}
    for shot_id in shot_order:
        shot = shots_by_id.get(shot_id, {})
        scene = shot.get("scene_description", "")
        prompts_by_shot_id[shot_id] = {
            "video_prompt": f"{scene}. Keep consistency with {visual_anchor}".strip(),
            "image_prompt": f"Keyframe for {scene}".strip(),
            "negative_prompt": "low quality, blur, artifacts",
            "service_specific_params": {"ratio": "9:16"},
        }

    return {
        "prompts_by_shot_id": prompts_by_shot_id,
        "llm_calls_used": 1,
        "tokens_used_estimate": 110,
        "cost_usd_estimate": 0.01,
    }
