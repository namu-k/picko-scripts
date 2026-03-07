from picko.video.agents.state import VideoAgentState


def build_audio_specs(state: VideoAgentState) -> dict[str, object]:
    shot_order = state.get("shot_order", [])
    execution_mode = state.get("execution_mode", "manual_assisted")

    strategy = "native_synced_audio" if execution_mode == "api" else "post_audio_tts_sfx"
    audio_by_shot_id: dict[str, dict[str, object]] = {}
    for idx, shot_id in enumerate(shot_order):
        audio_by_shot_id[shot_id] = {
            "audio_strategy": strategy,
            "voiceover_needed": idx == 0,
            "voiceover_script": "" if idx > 0 else "Opening line",
            "silence_windows": [],
            "ambient_profile": "quiet_room",
            "bgm_profile": "minimal",
            "sfx_cues": [],
            "caption_timing_ref": shot_id,
        }

    return {
        "audio_by_shot_id": audio_by_shot_id,
        "llm_calls_used": 1,
        "tokens_used_estimate": 90,
        "cost_usd_estimate": 0.01,
    }
