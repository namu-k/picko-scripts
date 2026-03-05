"""
Tests for video_plan.py data models
"""

from picko.video_plan import (
    AudioSpec,
    BrandStyle,
    KlingParams,
    LumaParams,
    PikaParams,
    RunwayParams,
    ServiceParams,
    TextOverlay,
    VeoParams,
    VideoPlan,
    VideoShot,
    VideoSource,
)


class TestServiceParams:
    """ServiceParams 기본 dataclass 테스트"""

    def test_service_params_to_dict(self):
        params = ServiceParams(
            prompt="dawn city, blue hour",
            negative_prompt="text, watermark",
            aspect_ratio="9:16",
            duration_sec=5,
        )
        d = params.to_dict()
        assert d["prompt"] == "dawn city, blue hour"
        assert d["negative_prompt"] == "text, watermark"
        assert d["aspect_ratio"] == "9:16"
        assert d["duration_sec"] == 5

    def test_service_params_from_dict(self):
        d = {"prompt": "test prompt", "aspect_ratio": "16:9"}
        params = ServiceParams.from_dict(d)
        assert params.prompt == "test prompt"
        assert params.aspect_ratio == "16:9"
        assert params.negative_prompt == ""


class TestLumaParams:
    """LumaParams 테스트"""

    def test_luma_params_to_dict(self):
        params = LumaParams(
            prompt="dawn city, blue hour",
            negative_prompt="text, watermark",
            camera_motion="slow_pan",
            motion_intensity=3,
        )
        d = params.to_dict()
        assert d["prompt"] == "dawn city, blue hour"
        assert d["camera_motion"] == "slow_pan"
        assert d["motion_intensity"] == 3

    def test_luma_params_from_dict(self):
        d = {
            "prompt": "cinematic shot",
            "camera_motion": "zoom_in",
            "loop": True,
        }
        params = LumaParams.from_dict(d)
        assert params.prompt == "cinematic shot"
        assert params.camera_motion == "zoom_in"
        assert params.loop is True

    def test_luma_params_defaults(self):
        params = LumaParams(prompt="test")
        assert params.camera_motion == ""
        assert params.motion_intensity == 3
        assert params.loop is False


class TestRunwayParams:
    """RunwayParams 테스트"""

    def test_runway_params_to_dict(self):
        params = RunwayParams(
            prompt="product showcase",
            motion=8,
            camera_move="orbit",
            seed=12345,
        )
        d = params.to_dict()
        assert d["prompt"] == "product showcase"
        assert d["motion"] == 8
        assert d["camera_move"] == "orbit"
        assert d["seed"] == 12345

    def test_runway_params_from_dict(self):
        d = {"prompt": "test", "motion": 7, "upscale": True}
        params = RunwayParams.from_dict(d)
        assert params.motion == 7
        assert params.upscale is True


class TestPikaParams:
    """PikaParams 테스트"""

    def test_pika_params_to_dict(self):
        params = PikaParams(
            prompt="funny cat video",
            pikaffect="Levitate",
            style_preset="3D",
        )
        d = params.to_dict()
        assert d["pikaffect"] == "Levitate"
        assert d["style_preset"] == "3D"

    def test_pika_params_from_dict(self):
        d = {"prompt": "test", "pikaffect": "Explode"}
        params = PikaParams.from_dict(d)
        assert params.pikaffect == "Explode"


class TestKlingParams:
    """KlingParams 테스트"""

    def test_kling_params_to_dict(self):
        params = KlingParams(
            prompt="tutorial video",
            camera_motion="pan_left",
            style="cinematic",
        )
        d = params.to_dict()
        assert d["camera_motion"] == "pan_left"
        assert d["style"] == "cinematic"


class TestVeoParams:
    """VeoParams 테스트"""

    def test_veo_params_to_dict(self):
        params = VeoParams(
            prompt="brand video",
            generate_audio=True,
            audio_mood="calm",
        )
        d = params.to_dict()
        assert d["generate_audio"] is True
        assert d["audio_mood"] == "calm"

    def test_veo_params_audio_defaults(self):
        params = VeoParams(prompt="test")
        assert params.generate_audio is True


class TestAudioSpec:
    """AudioSpec 테스트"""

    def test_audio_spec_to_dict(self):
        spec = AudioSpec(
            mood="romantic",
            genre="lofi",
            bpm=80,
            voiceover_text="Hello world",
            voiceover_gender="female",
            sfx=["whoosh", "ding"],
        )
        d = spec.to_dict()
        assert d["mood"] == "romantic"
        assert d["genre"] == "lofi"
        assert d["bpm"] == 80
        assert d["voiceover_text"] == "Hello world"
        assert d["sfx"] == ["whoosh", "ding"]

    def test_audio_spec_from_dict(self):
        d = {"mood": "energetic", "bpm": 120}
        spec = AudioSpec.from_dict(d)
        assert spec.mood == "energetic"
        assert spec.bpm == 120


class TestTextOverlay:
    """TextOverlay 테스트"""

    def test_text_overlay_to_dict(self):
        overlay = TextOverlay(
            text="Welcome!",
            position="top",
            font_size="large",
            animation="fade_in",
            start_sec=0.5,
            end_sec=3.0,
        )
        d = overlay.to_dict()
        assert d["text"] == "Welcome!"
        assert d["position"] == "top"
        assert d["animation"] == "fade_in"

    def test_text_overlay_from_dict(self):
        d = {"text": "CTA", "position": "bottom"}
        overlay = TextOverlay.from_dict(d)
        assert overlay.text == "CTA"
        assert overlay.position == "bottom"


class TestVideoShot:
    """VideoShot 테스트"""

    def test_shot_basic(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="intro",
            script="새벽 배경",
            caption="새벽 2시",
        )
        assert shot.index == 1
        assert shot.duration_sec == 5
        assert shot.shot_type == "intro"
        assert shot.background_prompt == ""

    def test_shot_with_luma_params(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="intro",
            script="새벽 배경",
            caption="새벽 2시",
            luma=LumaParams(prompt="dawn city, cinematic"),
        )
        assert shot.luma is not None
        assert shot.luma.prompt == "dawn city, cinematic"

    def test_shot_with_audio(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="main",
            script="설명",
            caption="",
            audio=AudioSpec(mood="calm", genre="ambient"),
        )
        assert shot.audio is not None
        assert shot.audio.mood == "calm"

    def test_shot_with_text_overlays(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="cta",
            script="CTA",
            caption="",
            text_overlays=[
                TextOverlay(text="Download Now!", position="bottom"),
            ],
        )
        assert len(shot.text_overlays) == 1
        assert shot.text_overlays[0].text == "Download Now!"

    def test_shot_to_dict_with_services(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="intro",
            script="새벽 배경",
            caption="새벽 2시",
            luma=LumaParams(prompt="dawn city"),
            runway=RunwayParams(prompt="dawn city", motion=6),
        )
        d = shot.to_dict()
        assert "luma" in d
        assert "runway" in d
        assert d["luma"]["prompt"] == "dawn city"
        assert d["runway"]["motion"] == 6

    def test_shot_from_dict_with_services(self):
        d = {
            "index": 1,
            "duration_sec": 5,
            "shot_type": "main",
            "script": "test",
            "caption": "",
            "luma": {"prompt": "test luma"},
            "pika": {"prompt": "test pika", "pikaffect": "Levitate"},
        }
        shot = VideoShot.from_dict(d)
        assert shot.luma is not None
        assert shot.luma.prompt == "test luma"
        assert shot.pika is not None
        assert shot.pika.pikaffect == "Levitate"

    def test_shot_with_transitions(self):
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="main",
            script="test",
            caption="",
            transition_in="fade",
            transition_out="dissolve",
        )
        d = shot.to_dict()
        assert d["transition_in"] == "fade"
        assert d["transition_out"] == "dissolve"


class TestVideoPlan:
    """VideoPlan 테스트"""

    def test_video_plan_basic(self):
        plan = VideoPlan(
            id="video_2026-03-05_001",
            account="socialbuilders",
            intent="ad",
            goal="앱 다운로드 유도",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="감성/몽환적"),
            shots=[
                VideoShot(
                    index=1,
                    duration_sec=5,
                    shot_type="intro",
                    script="시작",
                    caption="",
                ),
                VideoShot(index=2, duration_sec=5, shot_type="cta", script="CTA", caption=""),
            ],
            target_services=["luma"],
            platforms=["instagram_reel"],
        )
        assert plan.id == "video_2026-03-05_001"
        assert plan.intent == "ad"
        assert len(plan.shots) == 2
        assert plan.duration_sec == 10  # 자동 계산

    def test_video_plan_with_quality(self):
        plan = VideoPlan(
            id="video_001",
            account="test",
            intent="ad",
            goal="test goal",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="test"),
            shots=[],
            quality_score=85,
            quality_issues=[],
            quality_suggestions=["팁 1"],
        )
        assert plan.quality_score == 85
        assert plan.quality_suggestions == ["팁 1"]

    def test_video_plan_to_dict_with_quality(self):
        plan = VideoPlan(
            id="video_001",
            account="test",
            intent="ad",
            goal="test goal",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="test"),
            shots=[],
            quality_score=90,
            quality_warning=True,
        )
        d = plan.to_dict()
        assert d["quality_score"] == 90
        assert d["quality_warning"] is True

    def test_video_plan_from_dict_with_quality(self):
        d = {
            "id": "video_001",
            "account": "test",
            "intent": "ad",
            "goal": "test goal",
            "source": {"type": "account_only"},
            "brand_style": {"tone": "test"},
            "shots": [],
            "quality_score": 75,
            "quality_issues": ["issue1"],
            "final_evaluation": {
                "verdict": "needs_review",
                "overall_score": 72.5,
            },
        }
        plan = VideoPlan.from_dict(d)
        assert plan.quality_score == 75
        assert plan.quality_issues == ["issue1"]
        assert plan.final_evaluation is not None
        assert plan.final_evaluation["verdict"] == "needs_review"

    def test_video_plan_roundtrip(self):
        original = VideoPlan(
            id="video_001",
            account="test",
            intent="explainer",
            goal="explain something",
            source=VideoSource(type="longform", id="lf_001"),
            brand_style=BrandStyle(tone="educational", aspect_ratio="16:9"),
            shots=[
                VideoShot(
                    index=1,
                    duration_sec=10,
                    shot_type="intro",
                    script="Hello",
                    caption="",
                    luma=LumaParams(prompt="intro scene"),
                    audio=AudioSpec(mood="calm"),
                ),
            ],
            target_services=["luma", "runway"],
            platforms=["youtube_short"],
            quality_score=88,
        )
        restored = VideoPlan.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.intent == "explainer"
        assert restored.source.type == "longform"
        assert restored.source.id == "lf_001"
        assert len(restored.shots) == 1
        assert restored.shots[0].luma is not None
        assert restored.shots[0].audio is not None
        assert restored.quality_score == 88

    def test_video_plan_roundtrip_with_final_evaluation(self):
        plan = VideoPlan(
            id="video_final_eval_001",
            account="socialbuilders",
            intent="ad",
            goal="install",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="emotional"),
            shots=[],
            quality_score=80,
            final_evaluation={
                "verdict": "approved",
                "overall_score": 82.5,
                "issues": [],
            },
        )

        restored = VideoPlan.from_dict(plan.to_dict())
        assert restored.final_evaluation is not None
        assert restored.final_evaluation["verdict"] == "approved"
        assert restored.final_evaluation["overall_score"] == 82.5

    def test_video_plan_to_json(self):
        plan = VideoPlan(
            id="video_001",
            account="test",
            intent="ad",
            goal="test",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="test"),
            shots=[],
        )
        json_str = plan.to_json()
        assert '"id": "video_001"' in json_str
        assert '"account": "test"' in json_str

    def test_video_plan_from_json(self):
        json_str = """
        {
            "id": "video_002",
            "account": "test2",
            "intent": "brand",
            "goal": "brand awareness",
            "source": {"type": "account_only"},
            "brand_style": {"tone": "cinematic"},
            "shots": []
        }
        """
        plan = VideoPlan.from_json(json_str)
        assert plan.id == "video_002"
        assert plan.intent == "brand"

    def test_video_plan_to_markdown(self):
        plan = VideoPlan(
            id="video_001",
            account="test",
            intent="ad",
            goal="test goal",
            source=VideoSource(type="account_only"),
            brand_style=BrandStyle(tone="test tone"),
            shots=[
                VideoShot(
                    index=1,
                    duration_sec=5,
                    shot_type="intro",
                    script="Hello",
                    caption="Welcome",
                    notes={"luma": "cinematic style"},
                ),
            ],
            target_services=["luma"],
            platforms=["instagram_reel"],
        )
        md = plan.to_markdown()
        assert "# VideoPlan: video_001" in md
        assert "**계정**: test" in md
        assert "**의도**: ad" in md
        assert "### 샷 1" in md
        assert "서비스별 노트" in md
