"""
VideoPlan 품질 평가 로직

VideoPlan의 품질을 다차원으로 평가하고 점수를 산출한다.
품질 게이트에서 70점 이상을 보장하기 위한 기준 제공.
서비스별 최적화된 프롬프트 평가 기준을 적용한다.
"""

import re
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


# =============================================================================
# 서비스별 프롬프트 평가 기준
# =============================================================================

# 서비스별 필수 키워드 (프롬프트에 포함되어야 함)
SERVICE_REQUIRED_KEYWORDS = {
    "luma": {
        "camera_words": [
            "camera",
            "shot",
            "pan",
            "zoom",
            "tilt",
            "push",
            "static",
            "orbit",
        ],
        "lighting_words": [
            "light",
            "lighting",
            "glow",
            "ray",
            "shadow",
            "ambient",
            "soft",
        ],
        "mood_words": [
            "mood",
            "atmosphere",
            "feeling",
            "tone",
            "cinematic",
            "dreamy",
            "calm",
        ],
        "aspect_ratio": ["9:16", "16:9", "1:1", "vertical", "horizontal"],
    },
    "runway": {
        "camera_words": [
            "camera",
            "shot",
            "pan",
            "zoom",
            "tilt",
            "orbit",
            "push",
            "static",
        ],
        "style_words": [
            "cinematic",
            "commercial",
            "professional",
            "4k",
            "quality",
            "studio",
        ],
        "motion_words": ["motion", "movement", "dynamic", "timelapse", "slow"],
        "aspect_ratio": ["9:16", "16:9", "1:1", "vertical", "horizontal"],
    },
    "pika": {
        "action_words": [
            "jumping",
            "floating",
            "flying",
            "running",
            "exploding",
            "melting",
        ],
        "style_presets": ["3d", "anime", "realistic", "cartoon"],
        "pikaffect_keywords": ["levitate", "explode", "slice", "melt"],
        "aspect_ratio": ["9:16", "16:9", "1:1", "vertical", "horizontal"],
    },
    "kling": {
        "camera_words": ["camera", "pan", "zoom", "tilt", "orbit", "push", "drone"],
        "style_words": ["cinematic", "documentary", "commercial", "artistic"],
        "duration_words": ["seconds", "sec", "duration"],
        "aspect_ratio": ["9:16", "16:9", "vertical", "horizontal"],
    },
    "veo": {
        "visual_words": ["light", "color", "scene", "landscape", "atmosphere"],
        "audio_moods": ["calm", "energetic", "dramatic", "ambient", "orchestral"],
        "style_presets": ["cinematic", "natural", "artistic"],
        "aspect_ratio": ["9:16", "16:9", "vertical", "horizontal"],
    },
    "sora": {
        "camera_words": [
            "camera",
            "pan",
            "tracking",
            "static",
            "drone",
            "push",
            "aerial",
        ],
        "mood_words": [
            "contemplative",
            "serene",
            "nostalgic",
            "dreamy",
            "epic",
            "peaceful",
        ],
        "lighting_words": [
            "golden hour",
            "blue hour",
            "dawn",
            "dusk",
            "sunrise",
            "sunset",
        ],
        "style_words": ["cinematic", "natural", "artistic", "photorealistic"],
        "aspect_ratio": ["9:16", "16:9", "1:1", "vertical", "horizontal"],
    },
}

# 서비스별 금지 패턴 (프롬프트에 포함되면 안 됨)
SERVICE_FORBIDDEN_PATTERNS = {
    "luma": [
        "please",
        "create",
        "make",
        "show me",
        "can you",
        "text",
        "watermark",
        "logo",
    ],
    "runway": [
        "please",
        "create",
        "make",
        "show me",
        "can you",
        "add a",
        "i want",
        "doesn't move",
        "no camera",
    ],
    "pika": ["please", "create", "make", "only effect", "no scene"],
    "kling": ["please", "create", "make", "complex narrative", "multiple transitions"],
    "veo": ["please", "create", "make", "ambiguous audio", "text request", "subtitle"],
    "sora": [
        "please",
        "create",
        "make",
        "complex narrative",
        "text request",
        "subtitle",
        "dialogue",
    ],
}

# 서비스별 필수 필드
SERVICE_REQUIRED_FIELDS = {
    "luma": ["prompt", "negative_prompt", "camera_motion"],
    "runway": ["prompt", "negative_prompt", "motion", "camera_move"],
    "pika": ["prompt", "negative_prompt"],
    "kling": ["prompt", "negative_prompt", "camera_motion"],
    "veo": ["prompt", "negative_prompt"],
    "sora": ["prompt", "negative_prompt"],
}

# 서비스별 권장 필드
SERVICE_RECOMMENDED_FIELDS = {
    "luma": ["motion_intensity", "style_preset"],
    "runway": ["seed"],
    "pika": ["pikaffect", "style_preset"],
    "kling": ["style"],
    "veo": ["generate_audio", "audio_mood", "style_preset"],
    "sora": ["style", "camera_motion"],
}


class VideoPlanScorer:
    """VideoPlan 품질 평가기"""

    def score(self, plan: "VideoPlan", services: list[str] | None = None) -> QualityScore:
        """VideoPlan 품질 평가"""
        target_services = services or plan.target_services

        dimensions = {
            "prompt_quality": self._score_prompts(plan, target_services),
            "service_fit": self._score_service_fit(plan, target_services),
            "structure": self._score_structure(plan),
            "brand_alignment": self._score_brand_alignment(plan),
            "platform_fit": self._score_platform_fit(plan),
            "actionability": self._score_actionability(plan, target_services),
        }
        if "runway" in target_services:
            dimensions["keyframe_completeness"] = self._score_keyframe_completeness(plan, target_services)

        overall = sum(dimensions.values()) / len(dimensions)
        issues = self._identify_issues(plan, dimensions, target_services)
        suggestions = self._generate_suggestions(plan, dimensions, target_services)

        return QualityScore(
            overall=round(overall, 1),
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
        )

    def _score_keyframe_completeness(self, plan: "VideoPlan", services: list[str]) -> float:
        if "runway" not in services:
            return 100.0

        score = 100.0
        visual_anchor = getattr(plan, "visual_anchor", "") or ""
        if not visual_anchor:
            score -= 30
        elif len(visual_anchor) < 40:
            score -= 10

        anchor_keywords = self._extract_anchor_keywords(visual_anchor, limit=5)

        for shot in plan.shots:
            keyframe_prompt = getattr(shot, "keyframe_image_prompt", "") or ""
            if not keyframe_prompt:
                score -= 15
                continue

            prompt_lower = keyframe_prompt.lower()
            if "9:16" not in prompt_lower and "vertical" not in prompt_lower:
                score -= 5
            if len(keyframe_prompt) < 40:
                score -= 5

            if anchor_keywords:
                prompt_tokens = set(re.findall(r"[a-z0-9:]+", prompt_lower))
                if not any(token in prompt_tokens for token in anchor_keywords):
                    score -= 5

        return max(0.0, min(100.0, score))

    def _extract_anchor_keywords(self, text: str, limit: int = 5) -> list[str]:
        tokens = re.findall(r"[a-z0-9:]+", text.lower())
        stopwords = {
            "the",
            "and",
            "with",
            "for",
            "from",
            "into",
            "through",
            "over",
            "under",
            "in",
            "on",
            "at",
            "of",
            "to",
            "a",
            "an",
        }
        filtered = [token for token in tokens if token not in stopwords and len(token) > 1]
        deduped = list(dict.fromkeys(filtered))
        return deduped[:limit]

    def _score_prompts(self, plan: "VideoPlan", services: list[str]) -> float:
        """프롬프트 품질 평가 (서비스별 기준 적용)"""
        score = 100.0

        # 공통 모호 표현
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

        for shot in plan.shots:
            for service in services:
                params = getattr(shot, service, None)
                if not params:
                    score -= 25
                    continue

                if not hasattr(params, "prompt"):
                    score -= 20
                    continue

                prompt = params.prompt
                prompt_lower = prompt.lower()

                # 1. 프롬프트 길이 확인
                if len(prompt) < 30:
                    score -= 15
                elif len(prompt) < 50:
                    score -= 5

                # 2. 모호한 단어 확인
                vague_count = sum(1 for w in vague_words if w in prompt_lower)
                score -= vague_count * 5

                # 3. 서비스별 필수 키워드 확인
                service_keywords = SERVICE_REQUIRED_KEYWORDS.get(service, {})
                keyword_score = self._check_service_keywords(prompt_lower, service_keywords)
                score -= (100 - keyword_score) * 0.3

                # 4. 서비스별 금지 패턴 확인
                forbidden = SERVICE_FORBIDDEN_PATTERNS.get(service, [])
                for pattern in forbidden:
                    if pattern in prompt_lower:
                        score -= 10

                # 5. negative_prompt 확인
                if hasattr(params, "negative_prompt"):
                    if not params.negative_prompt:
                        score -= 8
                    elif len(params.negative_prompt) < 10:
                        score -= 3

        return max(0, score)

    def _check_service_keywords(self, prompt_lower: str, keywords: dict[str, list[str]]) -> float:
        """서비스별 필수 키워드 체크"""
        if not keywords:
            return 100.0

        score = 100.0
        for category, words in keywords.items():
            if not any(w in prompt_lower for w in words):
                score -= 15
        return max(0, score)

    def _score_service_fit(self, plan: "VideoPlan", services: list[str]) -> float:  # noqa: C901
        """서비스별 특성 적합성 평가"""
        score = 100.0

        for shot in plan.shots:
            for service in services:
                params = getattr(shot, service, None)
                if not params:
                    score -= 20
                    continue

                # Luma: 5초 클립 최적화, 카메라 모션 필수
                if service == "luma":
                    if shot.duration_sec > 5:
                        score -= 10
                    if hasattr(params, "camera_motion") and not params.camera_motion:
                        score -= 10
                    if hasattr(params, "motion_intensity"):
                        if params.motion_intensity < 1 or params.motion_intensity > 5:
                            score -= 5

                # Runway: motion(1-10), camera_move 필수
                elif service == "runway":
                    if hasattr(params, "motion"):
                        if params.motion < 1 or params.motion > 10:
                            score -= 10
                    else:
                        score -= 10
                    if hasattr(params, "camera_move") and not params.camera_move:
                        score -= 10

                # Pika: 장면+액션 조합, Pikaffect 활용 권장
                elif service == "pika":
                    prompt = params.prompt.lower() if hasattr(params, "prompt") else ""
                    action_words = SERVICE_REQUIRED_KEYWORDS["pika"]["action_words"]
                    if not any(w in prompt for w in action_words):
                        score -= 5  # 액션 단어 권장
                    if hasattr(params, "pikaffect") and params.pikaffect:
                        score += 5  # Pikaffect 활용 시 가산점

                # Kling: 카메라 모션, 스타일 명시
                elif service == "kling":
                    if hasattr(params, "camera_motion") and not params.camera_motion:
                        score -= 10
                    if hasattr(params, "style") and not params.style:
                        score -= 5
                    if shot.duration_sec > 15:
                        score -= 10

                # Veo: 오디오 mood 설정 (generate_audio=true일 때)
                elif service == "veo":
                    if hasattr(params, "generate_audio") and params.generate_audio:
                        if hasattr(params, "audio_mood") and not params.audio_mood:
                            score -= 10
                    if hasattr(params, "style_preset") and not params.style_preset:
                        score -= 5

                # Sora: 카메라 워크, 분위기 묘사 필수
                elif service == "sora":
                    prompt = params.prompt.lower() if hasattr(params, "prompt") else ""
                    sora_keywords = SERVICE_REQUIRED_KEYWORDS["sora"]
                    if not any(w in prompt for w in sora_keywords["camera_words"]):
                        score -= 10
                    if not any(w in prompt for w in sora_keywords["mood_words"]):
                        score -= 10

        return max(0, min(100, score))

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

    def _score_actionability(self, plan: "VideoPlan", services: list[str]) -> float:
        """실행 가능성 평가 (서비스별 파라미터 완비성)"""
        score = 100.0

        for shot in plan.shots:
            for service in services:
                params = getattr(shot, service, None)
                if not params:
                    score -= 30
                    continue

                # 필수 필드 확인
                required = SERVICE_REQUIRED_FIELDS.get(service, [])
                for fname in required:
                    value = getattr(params, fname, None)
                    if not value:
                        score -= 10

                # 권장 필드 확인
                recommended = SERVICE_RECOMMENDED_FIELDS.get(service, [])
                for fname in recommended:
                    value = getattr(params, fname, None)
                    if not value:
                        score -= 3

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
        if len(styles) > 2:
            score -= 10

        # 3. intent에 맞는 톤 확인
        tone_keywords = {
            "ad": ["commercial", "professional", "clean", "product"],
            "explainer": ["educational", "clear", "informative", "tutorial"],
            "brand": ["cinematic", "artistic", "emotional", "atmospheric"],
            "trend": ["dynamic", "energetic", "modern", "fast"],
        }

        expected_tones = tone_keywords.get(plan.intent, [])
        tone_matches = 0
        for shot in plan.shots:
            for service in plan.target_services:
                params = getattr(shot, service, None)
                if params and hasattr(params, "prompt"):
                    prompt_lower = params.prompt.lower()
                    if any(t in prompt_lower for t in expected_tones):
                        tone_matches += 1

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

    def _identify_issues(self, plan: "VideoPlan", dimensions: dict[str, float], services: list[str]) -> list[str]:
        """품질 이슈 식별"""
        issues = []

        if dimensions["prompt_quality"] < 70:
            issues.append("프롬프트가 너무 추상적입니다. 구체적인 시각 묘사를 추가하세요.")
        if dimensions["service_fit"] < 70:
            issues.append("서비스별 특성에 맞는 파라미터가 누락되었습니다.")
        if dimensions["structure"] < 70:
            issues.append("영상 구조가 intent에 맞지 않습니다.")
        if dimensions["actionability"] < 70:
            issues.append("일부 서비스용 필수 파라미터가 누락되었습니다.")
        if dimensions["brand_alignment"] < 70:
            issues.append("샷 간 일관성이 부족합니다.")
        if dimensions["platform_fit"] < 70:
            issues.append("플랫폼 제약을 준수하지 않습니다.")
        if "keyframe_completeness" in dimensions and dimensions["keyframe_completeness"] < 70:
            issues.append("Runway 스티칭용 keyframe 정보가 부족합니다.")

        # 서비스별 구체적 이슈
        for service in services:
            service_issues = self._identify_service_issues(plan, service)
            issues.extend(service_issues)

        return issues

    def _identify_service_issues(self, plan: "VideoPlan", service: str) -> list[str]:
        """서비스별 구체적 이슈 식별"""
        issues = []

        for shot in plan.shots:
            params = getattr(shot, service, None)
            if not params:
                issues.append(f"[{service}] 샷 {shot.index}: 서비스 파라미터 없음")
                continue

            if service == "luma":
                if not getattr(params, "camera_motion", None):
                    issues.append(f"[Luma] 샷 {shot.index}: camera_motion 누락")
                if shot.duration_sec > 5:
                    issues.append(f"[Luma] 샷 {shot.index}: 5초 초과 (권장 5초)")

            elif service == "runway":
                if not hasattr(params, "motion") or params.motion < 1:
                    issues.append(f"[Runway] 샷 {shot.index}: motion 값 누락/잘못됨 (1-10)")
                if not getattr(params, "camera_move", None):
                    issues.append(f"[Runway] 샷 {shot.index}: camera_move 누락")

            elif service == "pika":
                prompt = getattr(params, "prompt", "").lower()
                action_words = SERVICE_REQUIRED_KEYWORDS["pika"]["action_words"]
                if not any(w in prompt for w in action_words):
                    issues.append(f"[Pika] 샷 {shot.index}: 액션 단어 권장")

            elif service == "kling":
                if not getattr(params, "camera_motion", None):
                    issues.append(f"[Kling] 샷 {shot.index}: camera_motion 누락")

            elif service == "veo":
                if getattr(params, "generate_audio", True) and not getattr(params, "audio_mood", None):
                    issues.append(f"[Veo] 샷 {shot.index}: audio_mood 누락 (오디오 활성 시)")

            elif service == "sora":
                prompt = getattr(params, "prompt", "").lower()
                sora_kw = SERVICE_REQUIRED_KEYWORDS["sora"]
                if not any(w in prompt for w in sora_kw["camera_words"]):
                    issues.append(f"[Sora] 샷 {shot.index}: 카메라 워크 묘사 권장")
                if not any(w in prompt for w in sora_kw["mood_words"]):
                    issues.append(f"[Sora] 샷 {shot.index}: 분위기/무드 묘사 권장")

        return issues

    def _generate_suggestions(self, plan: "VideoPlan", dimensions: dict[str, float], services: list[str]) -> list[str]:
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
        for service in services:
            if service == "luma":
                suggestions.append("Luma: 각 샷을 5초 이내로 유지하고 camera_motion을 명시하세요.")
            elif service == "runway":
                suggestions.append("Runway: motion(1-10)과 camera_move를 명시하면 더 좋은 결과를 얻을 수 있습니다.")
            elif service == "pika":
                suggestions.append("Pika: 장면+액션 조합으로 프롬프트를 작성하고 Pikaffect를 활용하세요.")
            elif service == "kling":
                suggestions.append("Kling: camera_motion과 style을 명시하고 최대 15초를 유지하세요.")
            elif service == "veo":
                suggestions.append("Veo: generate_audio=true일 때 audio_mood를 설정하고 style_preset을 활용하세요.")
            elif service == "sora":
                suggestions.append("Sora: 카메라 워크(slow pan, tracking, drone)와 분위기 묘사를 포함하세요.")

        if "keyframe_completeness" in dimensions and dimensions["keyframe_completeness"] < 70:
            suggestions.append("Runway 스티칭 시 visual_anchor와 shot별 keyframe_image_prompt를 보강하세요.")

        return suggestions


def score_video_plan(plan: "VideoPlan", services: list[str] | None = None) -> QualityScore:
    """VideoPlan 품질 평가 편의 함수"""
    scorer = VideoPlanScorer()
    return scorer.score(plan, services)
