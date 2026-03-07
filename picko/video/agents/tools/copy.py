from picko.video.agents.state import VideoAgentState


def build_copy_bundles(state: VideoAgentState) -> dict[str, object]:
    shot_order = state.get("shot_order", [])
    shots_by_id = state.get("shots_by_id", {})
    objective = state.get("creative_brief", {}).get("objective", "")

    copy_by_shot_id: dict[str, dict[str, object]] = {}
    for idx, shot_id in enumerate(shot_order):
        shot = shots_by_id.get(shot_id, {})
        hook = f"{objective}" if idx == 0 and objective else None
        caption = f"{shot.get('scene_description', 'Scene')}"
        copy_by_shot_id[shot_id] = {
            "hook": hook,
            "caption": caption,
            "cta": "Learn more" if idx == len(shot_order) - 1 else None,
            "overlay_text": caption if shot.get("overlay_text_needed") else None,
        }

    return {
        "copy_by_shot_id": copy_by_shot_id,
        "llm_calls_used": 1,
        "tokens_used_estimate": 100,
        "cost_usd_estimate": 0.01,
    }
