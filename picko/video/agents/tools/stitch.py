from picko.video.agents.state import VideoAgentState


def build_stitch_plan(state: VideoAgentState) -> dict[str, object]:
    shot_order = state.get("shot_order", [])
    shots_by_id = state.get("shots_by_id", {})

    production_mode = "pure_video" if state.get("execution_mode") == "api" else "keyframe_motion"
    production_by_shot_id: dict[str, dict[str, object]] = {}
    segments: list[dict[str, object]] = []
    asset_manifest: list[dict[str, object]] = []

    total_duration = 0.0
    services_obj = state.get("services", ["sora_app"])
    services = services_obj if isinstance(services_obj, list) and services_obj else ["sora_app"]
    primary_service = str(services[0])

    for idx, shot_id in enumerate(shot_order):
        shot_obj = shots_by_id.get(shot_id, {})
        shot = shot_obj if isinstance(shot_obj, dict) else {}
        raw_duration = shot.get("duration_sec", 5.0)
        duration = 5.0
        if isinstance(raw_duration, (int, float, str)):
            duration = float(raw_duration)
        total_duration += duration
        production_by_shot_id[shot_id] = {
            "shot_id": shot_id,
            "production_mode": production_mode,
            "render_recipe": {
                "image_service": "flux",
                "motion_service": primary_service,
                "stitch_engine": "ffmpeg",
                "audio_strategy": "post_audio_tts_sfx",
            },
        }
        segments.append(
            {
                "segment_id": f"seg_{idx + 1}",
                "shot_ids": [shot_id],
                "method": production_mode,
                "transition_in": "cut" if idx == 0 else "dissolve",
                "transition_out": "dissolve",
                "duration_sec": duration,
                "assets_required": [f"asset_{shot_id}"],
            }
        )
        asset_manifest.append(
            {
                "asset_id": f"asset_{shot_id}",
                "type": "video",
                "shot_ids": [shot_id],
                "generation_service": primary_service,
                "prompt_ref": shot_id,
                "status": "pending",
                "estimated_cost_usd": 0.02,
            }
        )

    continuity_refs = {
        "character": {
            "name": (
                (
                    (
                        shots_by_id.get(shot_order[0], {})
                        if isinstance(shots_by_id.get(shot_order[0], {}), dict)
                        else {}
                    ).get("subject", "subject")
                )
                if shot_order
                else "subject"
            )
        },
        "setting": {
            "location": (
                (
                    (
                        shots_by_id.get(shot_order[0], {})
                        if isinstance(shots_by_id.get(shot_order[0], {}), dict)
                        else {}
                    ).get("setting", "studio")
                )
                if shot_order
                else "studio"
            )
        },
        "lighting": {
            "style": (
                (
                    (
                        shots_by_id.get(shot_order[0], {})
                        if isinstance(shots_by_id.get(shot_order[0], {}), dict)
                        else {}
                    ).get("lighting", "soft")
                )
                if shot_order
                else "soft"
            )
        },
    }

    return {
        "production_by_shot_id": production_by_shot_id,
        "continuity_refs": continuity_refs,
        "stitch_plan": {
            "strategy": "sequential",
            "segments": segments,
            "total_duration_sec": round(total_duration, 2),
            "transition_style": "clean",
        },
        "asset_manifest": asset_manifest,
        "llm_calls_used": 1,
        "tokens_used_estimate": 120,
        "cost_usd_estimate": 0.01,
    }
