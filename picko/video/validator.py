"""
VideoPlan 제약 검증 로직

VideoPlan이 서비스/플랫폼 제약을 준수하는지 검증한다.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from picko.video_plan import VideoPlan


@dataclass
class ValidationError:
    """검증 오류"""

    shot_index: int | None  # None이면 전체 계획 레벨 오류
    field: str
    message: str
    severity: str  # "error" | "warning"


class VideoPlanValidator:
    """VideoPlan 검증기"""

    def __init__(self, plan: "VideoPlan"):
        self.plan = plan
        self.errors: list[ValidationError] = []

    def validate(self) -> list[ValidationError]:
        """모든 검증 수행"""
        self.errors = []
        self._validate_duration()
        self._validate_platform_compatibility()
        self._validate_service_constraints()
        self._validate_intent_structure()
        self._validate_brand_consistency()
        return self.errors

    def _validate_duration(self):
        """총 길이가 플랫폼 제한 내인지 확인"""
        from picko.video.constraints import PLATFORM_CONSTRAINTS

        total = self.plan.duration_sec
        for platform in self.plan.platforms:
            c = PLATFORM_CONSTRAINTS.get(platform)
            if not c:
                continue
            if total > c.max_duration_sec:
                self.errors.append(
                    ValidationError(
                        shot_index=None,
                        field="duration_sec",
                        message=f"총 {total}초는 {platform} 최대 {c.max_duration_sec}초 초과",
                        severity="error",
                    )
                )

    def _validate_service_constraints(self):
        """서비스별 제약 검증"""
        from picko.video.constraints import SERVICE_CONSTRAINTS

        for service in self.plan.target_services:
            c = SERVICE_CONSTRAINTS.get(service)
            if not c:
                continue

            for shot in self.plan.shots:
                params = getattr(shot, service, None)
                if not params:
                    continue

                # 프롬프트 길이 검증
                if hasattr(params, "prompt") and len(params.prompt) > c.max_prompt_length:
                    self.errors.append(
                        ValidationError(
                            shot_index=shot.index,
                            field=f"{service}.prompt",
                            message=f"프롬프트 {len(params.prompt)}자 > {service} 최대 {c.max_prompt_length}자",
                            severity="error",
                        )
                    )

                # 비율 검증
                if hasattr(params, "aspect_ratio") and params.aspect_ratio not in c.supported_ratios:
                    self.errors.append(
                        ValidationError(
                            shot_index=shot.index,
                            field=f"{service}.aspect_ratio",
                            message=f"{params.aspect_ratio}는 {service}에서 미지원",
                            severity="error",
                        )
                    )

                # 길이 검증
                if hasattr(params, "duration_sec"):
                    if params.duration_sec > c.max_duration_sec:
                        self.errors.append(
                            ValidationError(
                                shot_index=shot.index,
                                field=f"{service}.duration_sec",
                                message=f"샷 길이 {params.duration_sec}초 > {service} 최대 {c.max_duration_sec}초",
                                severity="error",
                            )
                        )

    def _validate_intent_structure(self):
        """Intent별 필수 구조 검증"""
        from picko.video.constraints import INTENT_STRUCTURES

        structure = INTENT_STRUCTURES.get(self.plan.intent)
        if not structure:
            return

        shot_types = [s.shot_type for s in self.plan.shots]

        # CTA 필수 검증
        if structure.get("requires_cta") and "cta" not in shot_types:
            self.errors.append(
                ValidationError(
                    shot_index=None,
                    field="shots",
                    message=f"intent={self.plan.intent}는 CTA 샷 필수",
                    severity="error",
                )
            )

        # Intro 권장 검증
        if structure.get("requires_intro") and "intro" not in shot_types:
            self.errors.append(
                ValidationError(
                    shot_index=None,
                    field="shots",
                    message=f"intent={self.plan.intent}는 intro 샷 권장",
                    severity="warning",
                )
            )

    def _validate_platform_compatibility(self):
        """플랫폼 요구 비율과 샷 비율 일치 확인"""
        from picko.video.constraints import PLATFORM_CONSTRAINTS

        for platform in self.plan.platforms:
            c = PLATFORM_CONSTRAINTS.get(platform)
            if not c:
                continue

            # 각 샷의 비율이 플랫폼 요구사항과 일치하는지 확인
            for shot in self.plan.shots:
                for service in self.plan.target_services:
                    params = getattr(shot, service, None)
                    if params and hasattr(params, "aspect_ratio"):
                        if params.aspect_ratio != c.required_ratio:
                            # Twitter는 16:9 또는 1:1 허용
                            if platform == "twitter_video" and params.aspect_ratio in ["16:9", "1:1"]:
                                continue
                            self.errors.append(
                                ValidationError(
                                    shot_index=shot.index,
                                    field=f"{service}.aspect_ratio",
                                    message=f"{params.aspect_ratio}는 {platform} 권장 비율({c.required_ratio})과 불일치",
                                    severity="warning",
                                )
                            )

    def _validate_brand_consistency(self):
        """브랜드 일관성 검증"""
        # 샷 간 비율 일관성 확인
        ratios = set()
        for shot in self.plan.shots:
            for service in self.plan.target_services:
                params = getattr(shot, service, None)
                if params and hasattr(params, "aspect_ratio"):
                    ratios.add(params.aspect_ratio)

        if len(ratios) > 1:
            self.errors.append(
                ValidationError(
                    shot_index=None,
                    field="aspect_ratio",
                    message=f"샷 간 비율 불일치: {ratios}",
                    severity="warning",
                )
            )

    def has_errors(self) -> bool:
        """치명적 오류 존재 여부"""
        return any(e.severity == "error" for e in self.errors)

    def has_warnings(self) -> bool:
        """경고 존재 여부"""
        return any(e.severity == "warning" for e in self.errors)

    def get_errors(self) -> list[ValidationError]:
        """오류만 반환"""
        return [e for e in self.errors if e.severity == "error"]

    def get_warnings(self) -> list[ValidationError]:
        """경고만 반환"""
        return [e for e in self.errors if e.severity == "warning"]
