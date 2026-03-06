"""
Tests for video/quality_scorer.py
"""

from picko.video.quality_scorer import QUALITY_THRESHOLD, QualityScore, VideoPlanScorer, score_video_plan
from picko.video_plan import BrandStyle, LumaParams, RunwayParams, VideoIntent, VideoPlan, VideoShot, VideoSource


def make_plan(
    intent: VideoIntent = "ad",
    duration_sec: int = 15,
    services: list[str] | None = None,
    platforms: list[str] | None = None,
    shots: list[VideoShot] | None = None,
) -> VideoPlan:
    """테스트용 VideoPlan 생성 헬퍼"""
    return VideoPlan(
        id="video_test_001",
        account="test_account",
        intent=intent,
        goal="test goal",
        source=VideoSource(type="account_only"),
        brand_style=BrandStyle(tone="test"),
        shots=shots or [],
        target_services=services or ["luma"],
        platforms=platforms or ["instagram_reel"],
        duration_sec=duration_sec,
    )


def make_shot(
    index: int = 1,
    shot_type: str = "main",
    duration_sec: int = 5,
    luma: LumaParams | None = None,
) -> VideoShot:
    """테스트용 VideoShot 생성 헬퍼"""
    return VideoShot(
        index=index,
        duration_sec=duration_sec,
        shot_type=shot_type,
        script=f"shot {index}",
        caption="",
        luma=luma,
    )


def make_high_quality_luma_params() -> LumaParams:
    """고품질 LumaParams 생성"""
    return LumaParams(
        prompt=(
            "Dawn bedroom window view, blue hour cityscape outside, "
            "soft curtains gently moving, single desk lamp warm glow, "
            "contemplative mood, 9:16 vertical, cinematic"
        ),
        negative_prompt="text, watermark, logo, blurry, distorted",
        aspect_ratio="9:16",
        camera_motion="slow_pan",
        style_preset="cinematic",
    )


class TestQualityScore:
    """QualityScore dataclass 테스트"""

    def test_quality_score_creation(self):
        score = QualityScore(
            overall=85.0,
            dimensions={"prompt_quality": 90, "structure": 80},
            issues=["issue1"],
            suggestions=["tip1"],
        )
        assert score.overall == 85.0
        assert score.dimensions["prompt_quality"] == 90
        assert len(score.issues) == 1

    def test_quality_score_defaults(self):
        score = QualityScore(overall=70, dimensions={})
        assert score.issues == []
        assert score.suggestions == []


class TestQualityThreshold:
    """QUALITY_THRESHOLD 상수 테스트"""

    def test_threshold_value(self):
        assert QUALITY_THRESHOLD == 70


class TestVideoPlanScorerPromptQuality:
    """프롬프트 품질 평가 테스트"""

    def test_score_high_quality_prompts(self):
        plan = make_plan(
            intent="ad",
            shots=[
                make_shot(index=1, shot_type="intro", luma=make_high_quality_luma_params()),
                make_shot(index=2, shot_type="cta", luma=make_high_quality_luma_params()),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["prompt_quality"] >= 70

    def test_score_short_prompts(self):
        short_params = LumaParams(prompt="short", aspect_ratio="9:16")
        plan = make_plan(
            shots=[make_shot(index=1, luma=short_params)],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # 짧은 프롬프트는 감점
        assert result.dimensions["prompt_quality"] < 100

    def test_score_vague_prompts(self):
        vague_params = LumaParams(
            prompt="beautiful nice good amazing cool scene with light and camera",
            aspect_ratio="9:16",
        )
        plan = make_plan(
            shots=[make_shot(index=1, luma=vague_params)],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # 모호한 단어가 있으면 감점
        assert result.dimensions["prompt_quality"] < 100

    def test_score_missing_service_params(self):
        # luma params 없음
        plan = make_plan(
            shots=[make_shot(index=1, luma=None)],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["prompt_quality"] < 100


class TestVideoPlanScorerStructure:
    """구조 평가 테스트"""

    def test_score_ad_with_cta(self):
        plan = make_plan(
            intent="ad",
            shots=[
                make_shot(index=1, shot_type="intro"),
                make_shot(index=2, shot_type="main"),
                make_shot(index=3, shot_type="cta"),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["structure"] >= 70

    def test_score_ad_without_cta(self):
        plan = make_plan(
            intent="ad",
            shots=[
                make_shot(index=1, shot_type="intro"),
                make_shot(index=2, shot_type="main"),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["structure"] < 80

    def test_score_explainer_with_intro(self):
        plan = make_plan(
            intent="explainer",
            shots=[
                make_shot(index=1, shot_type="intro"),
                make_shot(index=2, shot_type="main"),
                make_shot(index=3, shot_type="main"),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["structure"] >= 70

    def test_score_explainer_without_intro(self):
        plan = make_plan(
            intent="explainer",
            shots=[
                make_shot(index=1, shot_type="main"),
                make_shot(index=2, shot_type="main"),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # intro 없으면 감점됨
        assert result.dimensions["structure"] < 100


class TestVideoPlanScorerActionability:
    """실행 가능성 평가 테스트"""

    def test_score_complete_params(self):
        plan = make_plan(
            shots=[
                make_shot(index=1, luma=LumaParams(prompt="test prompt", aspect_ratio="9:16")),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["actionability"] >= 70

    def test_score_missing_params(self):
        plan = make_plan(
            shots=[make_shot(index=1, luma=None)],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["actionability"] < 80


class TestVideoPlanScorerBrandAlignment:
    """브랜드 일관성 평가 테스트"""

    def test_score_consistent_ratios(self):
        params1 = LumaParams(prompt="test1", aspect_ratio="9:16")
        params2 = LumaParams(prompt="test2", aspect_ratio="9:16")
        plan = make_plan(
            shots=[
                make_shot(index=1, luma=params1),
                make_shot(index=2, luma=params2),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["brand_alignment"] >= 70

    def test_score_inconsistent_ratios(self):
        params1 = LumaParams(prompt="test1", aspect_ratio="9:16")
        params2 = LumaParams(prompt="test2", aspect_ratio="16:9")
        plan = make_plan(
            shots=[
                make_shot(index=1, luma=params1),
                make_shot(index=2, luma=params2),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert result.dimensions["brand_alignment"] < 80


class TestVideoPlanScorerOverall:
    """전체 점수 테스트"""

    def test_score_overall_calculation(self):
        plan = make_plan(
            intent="ad",
            shots=[
                make_shot(index=1, shot_type="intro", luma=make_high_quality_luma_params()),
                make_shot(index=2, shot_type="main", luma=make_high_quality_luma_params()),
                make_shot(index=3, shot_type="cta", luma=make_high_quality_luma_params()),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # 전체 점수는 모든 차원의 평균 (소수점 1자리 반올림)
        expected = round(sum(result.dimensions.values()) / len(result.dimensions), 1)
        assert result.overall == expected

    def test_score_returns_quality_score(self):
        plan = make_plan()
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert isinstance(result, QualityScore)


class TestVideoPlanScorerIssues:
    """이슈 식별 테스트"""

    def test_identifies_low_prompt_quality_issue(self):
        plan = make_plan(
            shots=[make_shot(index=1, luma=LumaParams(prompt="x", aspect_ratio="9:16"))],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # 낮은 품질이면 이슈가 있어야 함
        if result.dimensions["prompt_quality"] < 70:
            assert len(result.issues) > 0

    def test_no_issues_for_high_quality(self):
        plan = make_plan(
            intent="ad",
            shots=[
                make_shot(index=1, shot_type="intro", luma=make_high_quality_luma_params()),
                make_shot(index=2, shot_type="cta", luma=make_high_quality_luma_params()),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        # 고품질이면 이슈가 적거나 없어야 함
        assert len(result.issues) <= 2


class TestVideoPlanScorerSuggestions:
    """제안 생성 테스트"""

    def test_suggests_shorter_ad(self):
        plan = make_plan(
            intent="ad",
            duration_sec=60,  # 권장 30초 초과
            shots=[
                make_shot(index=1, shot_type="intro", luma=make_high_quality_luma_params()),
                make_shot(index=2, shot_type="cta", luma=make_high_quality_luma_params()),
            ],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert any("30초" in s for s in result.suggestions)

    def test_suggests_more_shots(self):
        plan = make_plan(
            intent="ad",
            shots=[make_shot(index=1, shot_type="cta", luma=make_high_quality_luma_params())],
        )
        scorer = VideoPlanScorer()
        result = scorer.score(plan)
        assert any("3개" in s for s in result.suggestions)


class TestScoreVideoPlanFunction:
    """score_video_plan 편의 함수 테스트"""

    def test_score_video_plan_returns_quality_score(self):
        plan = make_plan()
        result = score_video_plan(plan)
        assert isinstance(result, QualityScore)

    def test_score_video_plan_same_as_scorer(self):
        plan = make_plan(
            shots=[make_shot(index=1, luma=make_high_quality_luma_params())],
        )
        result1 = score_video_plan(plan)
        scorer = VideoPlanScorer()
        result2 = scorer.score(plan)
        assert result1.overall == result2.overall


class TestVideoPlanScorerKeyframeCompleteness:
    def test_keyframe_dimension_enabled_for_runway(self):
        runway = RunwayParams(
            prompt="phone glow close-up in 3AM bedroom",
            negative_prompt="text, watermark",
            motion=4,
            camera_move="static",
        )
        shot = VideoShot(
            index=1,
            duration_sec=5,
            shot_type="intro",
            script="scene",
            caption="",
            keyframe_image_prompt="3AM bedroom side profile in phone glow, 9:16 vertical",
            runway=runway,
        )
        plan = make_plan(services=["runway"], shots=[shot])
        plan.visual_anchor = "3AM bedroom cool blue moonlight phone glow 9:16 vertical"

        result = VideoPlanScorer().score(plan, ["runway"])

        assert "keyframe_completeness" in result.dimensions

    def test_keyframe_dimension_disabled_without_runway(self):
        plan = make_plan(
            services=["luma"],
            shots=[make_shot(index=1, luma=make_high_quality_luma_params())],
        )
        plan.visual_anchor = "3AM bedroom cool blue moonlight phone glow 9:16 vertical"

        result = VideoPlanScorer().score(plan, ["luma"])

        assert "keyframe_completeness" not in result.dimensions
