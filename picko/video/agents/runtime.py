from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from picko.video_plan import VideoPlan


def build_render_briefs(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    shot_order = state.get("shot_order", [])
    shots_by_id = state.get("shots_by_id", {})
    production_by_shot_id = state.get("production_by_shot_id", {})
    prompts_by_shot_id = state.get("prompts_by_shot_id", {})
    audio_by_shot_id = state.get("audio_by_shot_id", {})
    copy_by_shot_id = state.get("copy_by_shot_id", {})

    briefs: list[dict[str, Any]] = []
    for shot_id in shot_order:
        shot = shots_by_id.get(shot_id, {})
        production = production_by_shot_id.get(shot_id, {})
        prompt = prompts_by_shot_id.get(shot_id, {})
        audio = audio_by_shot_id.get(shot_id, {})
        copy = copy_by_shot_id.get(shot_id, {})

        render_recipe = production.get("render_recipe", {})
        briefs.append(
            {
                "shot_id": shot_id,
                "production_mode": production.get("production_mode", "pure_video"),
                "render_recipe": render_recipe,
                "video_prompt": prompt.get("video_prompt", ""),
                "image_prompt": prompt.get("image_prompt", ""),
                "negative_prompt": prompt.get("negative_prompt", ""),
                "audio_strategy": audio.get("audio_strategy", "silent_visual"),
                "voiceover_script": audio.get("voiceover_script"),
                "caption": copy.get("caption", ""),
                "overlay_text": copy.get("overlay_text"),
                "duration_sec": shot.get("duration_sec", 5.0),
            }
        )

    return briefs


def review_rendered_artifact(plan: VideoPlan, uploaded_file: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not uploaded_file:
        issues.append(
            {
                "code": "artifact.missing_file",
                "severity": "high",
                "description": "Uploaded file path is required.",
                "shot_ids": [],
            }
        )

    if not plan.render_briefs:
        issues.append(
            {
                "code": "artifact.missing_render_briefs",
                "severity": "high",
                "description": "Render briefs are required before artifact review.",
                "shot_ids": [],
            }
        )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "auto_regen_suggestions": [] if issues else ["none"],
        "human_review_items": [] if not issues else ["artifact_upload_validation"],
    }


def apply_publish_decision(plan: VideoPlan, human_decision: str) -> dict[str, Any]:
    if plan.publish_status in {"approved", "blocked"}:
        return {
            "publish_status": plan.publish_status,
            "issues": [
                {
                    "code": "publish.invalid_transition",
                    "severity": "medium",
                    "description": "Publish status is already terminal.",
                }
            ],
        }

    if human_decision not in {"approved", "blocked"}:
        return {
            "publish_status": "blocked",
            "issues": [
                {
                    "code": "publish.invalid_human_decision",
                    "severity": "high",
                    "description": "Human decision must be 'approved' or 'blocked'.",
                }
            ],
        }

    plan.publish_status = human_decision
    return {
        "publish_status": plan.publish_status,
        "issues": [],
    }
