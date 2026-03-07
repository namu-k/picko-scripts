from picko.video.agents.state import VideoAgentState


def review_plan(state: VideoAgentState) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    shot_order = state.get("shot_order", [])

    if not shot_order:
        issues.append(
            {
                "code": "story.no_shots",
                "severity": "critical",
                "target_agents": ["story_writer"],
                "shot_ids": [],
                "description": "No shots were generated.",
            }
        )

    expected = set(shot_order)
    if set(state.get("production_by_shot_id", {}).keys()) != expected:
        issues.append(
            {
                "code": "production.key_mismatch",
                "severity": "high",
                "target_agents": ["stitch_planner"],
                "shot_ids": shot_order,
                "description": "Production keys do not match shot order.",
            }
        )

    for shot_id in shot_order:
        copy_item = state.get("copy_by_shot_id", {}).get(shot_id, {})
        prompt_item = state.get("prompts_by_shot_id", {}).get(shot_id, {})
        audio_item = state.get("audio_by_shot_id", {}).get(shot_id, {})
        if not copy_item.get("caption"):
            issues.append(
                {
                    "code": "copy.missing_caption",
                    "severity": "medium",
                    "target_agents": ["copywriter"],
                    "shot_ids": [shot_id],
                    "description": "Caption is missing.",
                }
            )
        if not prompt_item.get("video_prompt"):
            issues.append(
                {
                    "code": "prompt.missing_video_prompt",
                    "severity": "medium",
                    "target_agents": ["prompt_engineer"],
                    "shot_ids": [shot_id],
                    "description": "Video prompt is missing.",
                }
            )
        if not audio_item.get("audio_strategy"):
            issues.append(
                {
                    "code": "audio.missing_strategy",
                    "severity": "medium",
                    "target_agents": ["audio_director"],
                    "shot_ids": [shot_id],
                    "description": "Audio strategy is missing.",
                }
            )

    quality_score = max(0.0, 100.0 - (15.0 * len(issues)))
    feedback_notes = ["Plan is consistent"] if not issues else ["Revisions required"]

    return {
        "plan_review": {
            "quality_score": quality_score,
            "issues": issues,
            "feedback_notes": feedback_notes,
        },
        "revision_issues": issues,
    }
