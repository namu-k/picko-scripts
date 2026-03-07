from picko.video.agents.state import VideoAgentState


def review_artifacts(state: VideoAgentState) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    assets = state.get("asset_manifest", [])
    if not assets:
        issues.append(
            {
                "code": "artifact.missing_assets",
                "severity": "high",
                "target_agents": ["stitch_planner"],
                "shot_ids": [],
                "description": "No assets were prepared for rendering.",
            }
        )
    for asset in assets:
        cost_obj = asset.get("estimated_cost_usd", 0.0)
        cost = float(cost_obj) if isinstance(cost_obj, (int, float, str)) else 0.0
        if cost < 0:
            issues.append(
                {
                    "code": "artifact.invalid_cost",
                    "severity": "medium",
                    "target_agents": ["stitch_planner"],
                    "shot_ids": asset.get("shot_ids", []),
                    "description": "Asset cost estimate cannot be negative.",
                }
            )

    artifact_review = {
        "passed": len(issues) == 0,
        "issues": issues,
    }
    return {"artifact_review": artifact_review}
