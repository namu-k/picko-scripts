"""
VideoPlan 품질 평가 로직

VideoPlan의 품질을 다차원으로 평가하고 점수를 산출한다.
품질 게이트에서 70점 이상을 보장하기 위한 기준 제공.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from picko.video_plan import VideoPlan

QUALITY_THRESHOLD = 70


@dataclass
class QualityScore:
    """품질 점수 결과"""

    overall: float
    dimensions: dict[str, float]
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class VideoPlanScorer:
    """VideoPlan 품질 평가기"""

    def score(self, plan: "VideoPlan") -> QualityScore:
        """VideoPlan 품질 평가"""
        dimensions = {
            "prompt_quality": self._score_prompts(plan),
            "structure": self._score_structure(plan),
            "brand_alignment": self._score_brand_alignment(plan),
            "platform_fit": self._score_platform_fit(plan),
            "actionability": self._score_actionability(plan),
        }

        overall = sum(dimensions.values()) / len(dimensions)
        issues = self._identify_issues(plan, dimensions)
        suggestions = self._generate_suggestions(plan, dimensions)

        return QualityScore(
            overall=round(overall, 1),
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
        )

    def _score_prompts(self, plan: "VideoPlan") -> float:
        """프롬프트 품질 평가"""
        score = 100.0

        # 영어 + 한국어 모호 표현
        vague_words = [
            "beautiful",
            "nice",
            "good",
            "great",
            "amazing",
            "cool",
            "아름다운",
            "멋진",
            "좋은",
            "훌륭한",
            "예쁜",
            "귀여운",
        ]

        visual_words = [
            "light",
            "color",
            "angle",
            "texture",
            "shadow",
            "camera",
            "조명",
            "색감",
            "앵글",
            "질감",
            "그림자",
            "카메라",
        ]

        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if not params:
                    score -= 20
                    continue

                # 프롬프트 길이 확인
                if hasattr(params, "prompt"):
                    if len(params.prompt) < 30:
                        score -= 10

                    # 모호한 단어 확인
                    prompt_lower = params.prompt.lower()
                    if any(w in prompt_lower for w in vague_words):
                        score -= 5

                    # 시각적 단어 확인
                    if not any(w in prompt_lower for w in visual_words):
                        score -= 10

                # negative_prompt 확인
                if hasattr(params, "negative_prompt") and not params.negative_prompt:
                    score -= 5

        return max(0, score)

    def _score_structure(self, plan: "VideoPlan") -> float:
        """영상 구조 평가"""
        score = 100.0
        shot_types = [s.shot_type for s in plan.shots]

        if plan.intent == "ad":
            if "cta" not in shot_types:
                score -= 30
            if "intro" not in shot_types:
                score -= 10

        if plan.intent == "explainer":
            if "intro" not in shot_types:
                score -= 20
            if "main" not in shot_types:
                score -= 15

        if plan.intent == "brand":
            if len(shot_types) < 3:
                score -= 15

        if plan.intent == "trend":
            if len(shot_types) > 5:
                score -= 10  # 트렌드는 짧게

        return max(0, score)

    def _score_actionability(self, plan: "VideoPlan") -> float:
        """실행 가능성 평가 (서비스별 파라미터 완비성)"""
        score = 100.0

        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if not params:
                    score -= 30
                elif hasattr(params, "prompt"):
                    if not params.prompt:
                        score -= 20
                    elif not hasattr(params, "aspect_ratio") or not params.aspect_ratio:
                        score -= 10

        return max(0, score)

    def _score_brand_alignment(self, plan: "VideoPlan") -> float:
        """브랜드 일관성 평가"""
        score = 100.0

        # 1. 샷 간 비율 일관성
        ratios = set()
        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if params and hasattr(params, "aspect_ratio") and params.aspect_ratio:
                    ratios.add(params.aspect_ratio)
        if len(ratios) > 1:
            score -= 20  # 비율 불일치

        # 2. 샷 간 톤 일관성 (스타일 프리셋 확인)
        styles = set()
        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if params and hasattr(params, "style_preset") and params.style_preset:
                    styles.add(params.style_preset)
        # 스타일이 너무 다양하면 감점
        if len(styles) > 2:
            score -= 10

        # 3. intent에 맞는 톤 확인
        tone_keywords = {
            "ad": ["commercial", "professional", "clean"],
            "explainer": ["educational", "clear", "informative"],
            "brand": ["cinematic", "artistic", "emotional"],
            "trend": ["dynamic", "energetic", "modern"],
        }

        # 프롬프트에서 톤 키워드 확인
        expected_tones = tone_keywords.get(plan.intent, [])
        tone_matches = 0
        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if params and hasattr(params, "prompt"):
                    prompt_lower = params.prompt.lower()
                    if any(t in prompt_lower for t in expected_tones):
                        tone_matches += 1

        # 톤 키워드가 전혀 없으면 감점
        if expected_tones and tone_matches == 0:
            score -= 15

        return max(0, score)

    def _score_platform_fit(self, plan: "VideoPlan") -> float:
        """플랫폼 적합성 평가"""
        score = 100.0
        from picko.video.constraints import PLATFORM_CONSTRAINTS

        for platform in plan.platforms:
            c = PLATFORM_CONSTRAINTS.get(platform)
            if c:
                # 권장 길이 초과
                if plan.duration_sec > c.recommended_duration_sec:
                    score -= 10
                # 최대 길이 초과
                if plan.duration_sec > c.max_duration_sec:
                    score -= 30

        return max(0, score)

    def _identify_issues(self, plan: "VideoPlan", dimensions: dict[str, float]) -> list[str]:
        """품질 이슈 식별"""
        issues = []

        if dimensions["prompt_quality"] < 70:
            issues.append("프롬프트가 너무 추상적입니다. 구체적인 시각 묘사를 추가하세요.")
        if dimensions["structure"] < 70:
            issues.append("영상 구조가 intent에 맞지 않습니다.")
        if dimensions["actionability"] < 70:
            issues.append("일부 서비스용 파라미터가 누락되었습니다.")
        if dimensions["brand_alignment"] < 70:
            issues.append("샷 간 일관성이 부족합니다.")
        if dimensions["platform_fit"] < 70:
            issues.append("플랫폼 제약을 준수하지 않습니다.")

        return issues

    def _generate_suggestions(self, plan: "VideoPlan", dimensions: dict[str, float]) -> list[str]:
        """개선 제안 생성"""
        suggestions = []

        if plan.intent == "ad" and plan.duration_sec > 30:
            suggestions.append("광고 영상은 30초 이내를 권장합니다.")
        if plan.intent == "explainer" and plan.duration_sec < 30:
            suggestions.append("설명 영상은 최소 30초 이상을 권장합니다.")
        if len(plan.shots) > 5:
            suggestions.append("샷이 많을수록 편집 복잡도가 증가합니다. 3-5개를 권장합니다.")
        if len(plan.shots) < 3:
            suggestions.append("최소 3개의 샷을 권장합니다.")

        # 서비스별 제안
        if "luma" in plan.target_services:
            suggestions.append("Luma는 5초 클립에 최적화되어 있습니다. 각 샷을 5초 이내로 유지하세요.")
        if "runway" in plan.target_services:
            suggestions.append("Runway는 카메라 움직임을 명시하면 더 좋은 결과를 얻을 수 있습니다.")

        return suggestions


def score_video_plan(plan: "VideoPlan") -> QualityScore:
    """VideoPlan 품질 평가 편의 함수"""
    scorer = VideoPlanScorer()
    return scorer.score(plan)
