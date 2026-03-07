from dataclasses import asdict

from picko.video.agents.schemas import CreativeBrief, ProductionSpec, RenderRecipe, ShotDraft


def test_creative_brief_defaults_and_roundtrip() -> None:
    brief = CreativeBrief(account_id="acct_1", intent="brand")
    payload = asdict(brief)
    assert payload["account_id"] == "acct_1"
    assert payload["intent"] == "brand"
    assert payload["execution_mode"] == "manual_assisted"
    assert payload["proof_points"] == []


def test_shot_draft_and_production_spec() -> None:
    shot = ShotDraft(
        shot_id="shot_1",
        purpose="hook",
        scene_description="Night city close-up",
        subject="Creator",
        setting="city",
        lighting="neon",
        camera_intent="push_in",
    )
    spec = ProductionSpec(shot_id=shot.shot_id, production_mode="pure_video", render_recipe=RenderRecipe())
    assert shot.shot_id == "shot_1"
    assert spec.render_recipe.audio_strategy == "silent_visual"
