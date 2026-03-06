import json

from picko.account_context import AccountIdentity, WeeklySlot
from picko.video.generator import VideoGenerator
from picko.video.quality_scorer import VideoPlanScorer


def _identity() -> AccountIdentity:
    return AccountIdentity(
        account_id="socialbuilders",
        one_liner="Build social products",
        target_audience=["founders"],
        value_proposition="Clear growth strategy",
        pillars=["P1: product", "P2: growth"],
        tone_voice={
            "tone": "authoritative, informative, casual",
            "forbidden": "fear-based urgency",
            "cta_style": "direct but warm",
        },
        boundaries=[],
    )


def test_parse_response_coerces_numeric_string_fields():
    generator = VideoGenerator(
        account_id="socialbuilders",
        services=["luma", "runway", "pika", "kling", "veo", "sora"],
        platforms=["instagram_reel"],
        intent="ad",
    )

    raw = json.dumps(
        {
            "goal": "app install",
            "shots": [
                {
                    "index": "1",
                    "duration_sec": "5",
                    "shot_type": "intro",
                    "script": "phone notification rings",
                    "caption": "새벽 알림",
                    "services": {
                        "luma": {
                            "prompt": "cinematic dawn phone notification close-up with subtle fog",
                            "negative_prompt": "low quality",
                            "camera_motion": "slow_pan",
                            "motion_intensity": "4",
                            "loop": "true",
                        },
                        "runway": {
                            "prompt": "user reaches for phone in dawn light",
                            "negative_prompt": "blurry",
                            "motion": "8",
                            "camera_move": "zoom_in",
                            "seed": "42",
                            "upscale": "true",
                        },
                    },
                }
            ],
        }
    )

    plan = generator._parse_response(raw, identity=_identity(), content_summary=None)
    shot = plan.shots[0]

    assert shot.index == 1
    assert shot.duration_sec == 5
    assert shot.luma is not None
    assert shot.luma.motion_intensity == 4
    assert shot.luma.loop is True
    assert shot.runway is not None
    assert shot.runway.motion == 8
    assert shot.runway.seed == 42
    assert shot.runway.upscale is True


def test_parse_response_normalizes_non_numeric_motion_for_scorer():
    generator = VideoGenerator(
        account_id="socialbuilders",
        services=["luma"],
        platforms=["instagram_reel"],
        intent="ad",
    )

    raw = json.dumps(
        {
            "goal": "conversion",
            "shots": [
                {
                    "index": "1",
                    "duration_sec": "5",
                    "shot_type": "intro",
                    "script": "dawn call alert appears",
                    "caption": "연결의 시작",
                    "services": {
                        "luma": {
                            "prompt": "close-up of smartphone showing incoming dawn call in cinematic style",
                            "negative_prompt": "artifacts",
                            "camera_motion": "slow_pan",
                            "motion_intensity": "very high",
                        }
                    },
                },
                {
                    "index": 2,
                    "duration_sec": 5,
                    "shot_type": "main",
                    "script": "user answers and smiles",
                    "caption": "감성 통화",
                    "services": {
                        "luma": {
                            "prompt": "warm emotional phone call scene with gentle camera movement",
                            "negative_prompt": "noise",
                            "camera_motion": "tilt_up",
                            "motion_intensity": "medium",
                        }
                    },
                },
                {
                    "index": 3,
                    "duration_sec": 5,
                    "shot_type": "cta",
                    "script": "install now",
                    "caption": "지금 시작",
                    "services": {
                        "luma": {
                            "prompt": "app install call to action with logo and phone UI",
                            "negative_prompt": "distortion",
                            "camera_motion": "zoom_in",
                            "motion_intensity": "low",
                        }
                    },
                },
            ],
        }
    )

    plan = generator._parse_response(raw, identity=_identity(), content_summary=None)
    score = VideoPlanScorer().score(plan, ["luma"])

    assert isinstance(score.overall, float)
    assert plan.shots[0].luma is not None
    assert isinstance(plan.shots[0].luma.motion_intensity, int)


def test_build_prompt_includes_selected_model_workflows():
    generator = VideoGenerator(
        account_id="socialbuilders",
        services=["luma", "runway"],
        platforms=["instagram_reel"],
        intent="ad",
    )

    prompt = generator._build_prompt(_identity(), None, None)

    assert "## 모델별 생성 워크플로우 레퍼런스" in prompt
    assert "### Luma Workflow" in prompt
    assert "### Runway Workflow" in prompt
    assert "### Pika Workflow" not in prompt


def test_video_generator_build_prompt_includes_identity_and_weekly_fields():
    identity = AccountIdentity(
        account_id="test",
        one_liner="Test one liner",
        target_audience=["audience1", "audience2"],
        value_proposition="Test value",
        pillars=[],
        tone_voice={
            "tone": "calm",
            "forbidden": "aggressive claims",
            "cta_style": "soft",
        },
        boundaries=[],
    )
    weekly_slot = WeeklySlot(
        week_of="2026-03-02",
        account_id="test",
        customer_outcome="Test outcome",
        operator_kpi="Test KPI",
        cta="Test CTA",
        pillar_distribution={},
    )

    gen = VideoGenerator(account_id="test", services=["luma"], intent="ad")
    prompt = gen._build_prompt(identity=identity, weekly_slot=weekly_slot, content_summary=None)

    assert "Test one liner" in prompt
    assert "audience1" in prompt or "audience2" in prompt
    assert "Test outcome" in prompt
    assert "Test CTA" in prompt


def test_build_prompt_includes_brand_tone_and_keyframe_schema_fields():
    generator = VideoGenerator(
        account_id="socialbuilders",
        services=["runway"],
        platforms=["instagram_reel"],
        intent="ad",
    )

    prompt = generator._build_prompt(_identity(), None, None)

    assert "## 브랜드 톤 & 비주얼 정체성" in prompt
    assert "authoritative, informative, casual" in prompt
    assert '"visual_anchor": "' in prompt
    assert '"keyframe_image_prompt": "' in prompt
    assert '"reference_image_url": "' in prompt


def test_parse_response_parses_keyframe_fields_and_brand_style_tone():
    generator = VideoGenerator(
        account_id="socialbuilders",
        services=["runway"],
        platforms=["instagram_reel"],
        intent="ad",
    )

    raw = json.dumps(
        {
            "goal": "install",
            "visual_anchor": "3AM bedroom, cool blue moonlight, 9:16 vertical",
            "shots": [
                {
                    "index": 1,
                    "duration_sec": 5,
                    "shot_type": "intro",
                    "script": "scene",
                    "caption": "caption",
                    "keyframe_image_prompt": "3AM bedroom side profile, 9:16 vertical",
                    "services": {
                        "runway": {
                            "prompt": "phone glow close-up",
                            "negative_prompt": "text, watermark",
                            "motion": 4,
                            "camera_move": "static",
                            "reference_image_url": "https://example.com/frame-1.png",
                        }
                    },
                }
            ],
        }
    )

    plan = generator._parse_response(raw, identity=_identity(), content_summary=None)

    assert plan.visual_anchor == "3AM bedroom, cool blue moonlight, 9:16 vertical"
    assert plan.brand_style.tone == "authoritative, informative, casual"
    assert plan.brand_style.theme == "socialbuilders"
    assert plan.shots[0].keyframe_image_prompt == "3AM bedroom side profile, 9:16 vertical"
    assert plan.shots[0].runway is not None
    assert plan.shots[0].runway.reference_image_url == "https://example.com/frame-1.png"
