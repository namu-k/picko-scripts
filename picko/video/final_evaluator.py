"""
Final evaluator for video plans (second-pass review).

This evaluator is deterministic and focuses on final delivery quality,
especially ad effectiveness signals like visual events and UI presence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from picko.video_plan import VideoIntent, VideoPlan, VideoShot


FINAL_APPROVED_THRESHOLD = 78.0
FINAL_NEEDS_REVIEW_THRESHOLD = 65.0


EVENT_KEYWORDS = {
    "show",
    "reveals",
    "opens",
    "rings",
    "vibrates",
    "appears",
    "turns",
    "connects",
    "calls",
    "answers",
    "notification",
    "alert",
    "ring",
    "vibration",
    "알림",
    "진동",
    "울림",
    "통화",
    "연결",
    "등장",
    "전환",
    "클릭",
}

UI_SIGNAL_KEYWORDS = {
    "ui",
    "screen",
    "app",
    "phone",
    "smartphone",
    "notification",
    "status bar",
    "call ui",
    "message bubble",
    "인터페이스",
    "화면",
    "앱",
    "폰",
    "스마트폰",
    "알림",
    "통화 화면",
}

HOOK_KEYWORDS = {
    "suddenly",
    "immediately",
    "ring",
    "notification",
    "urgent",
    "first",
    "instantly",
    "새벽",
    "지금",
    "즉시",
    "알림",
    "진동",
    "통화",
}

CTA_KEYWORDS = {
    "download",
    "install",
    "join",
    "start now",
    "try now",
    "get app",
    "지금 시작",
    "지금 다운로드",
    "설치",
    "바로",
    "지금",
}


@dataclass
class FinalEvaluationResult:
    verdict: str
    overall_score: float
    dimensions: dict[str, float] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    ad_signals: dict[str, float | bool | int] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "ad_signals": self.ad_signals,
            "reasoning": self.reasoning,
        }


class VideoPlanFinalEvaluator:
    """Second-pass final evaluator agent for video plans."""

    def evaluate(
        self,
        plan: "VideoPlan",
        services: list[str] | None = None,
        intent: "VideoIntent | None" = None,
    ) -> FinalEvaluationResult:
        target_services = services or plan.target_services
        target_intent = intent or plan.intent

        base_quality = float(plan.quality_score or 0.0)

        event_density = self._event_density_score(plan, target_services)
        ui_signal_density = self._ui_signal_score(plan, target_services)
        shot_distinctiveness = self._shot_distinctiveness_score(plan, target_services)
        hook_score = self._hook_score(plan, target_services)
        cta_score = self._cta_score(plan)

        dimensions = {
            "base_quality": round(base_quality, 1),
            "event_density": round(event_density, 1),
            "ui_signal_density": round(ui_signal_density, 1),
            "shot_distinctiveness": round(shot_distinctiveness, 1),
            "hook_score": round(hook_score, 1),
            "cta_score": round(cta_score, 1),
        }

        overall = (
            base_quality * 0.35
            + event_density * 0.2
            + ui_signal_density * 0.15
            + shot_distinctiveness * 0.15
            + hook_score * 0.1
            + cta_score * 0.05
        )

        issues: list[str] = []
        suggestions: list[str] = []

        event_count = self._event_shot_count(plan, target_services)
        ui_count = self._ui_shot_count(plan, target_services)
        has_cta = any(shot.shot_type == "cta" for shot in plan.shots)

        ad_hard_fail = False
        if target_intent == "ad":
            if not has_cta:
                ad_hard_fail = True
                issues.append("광고 의도(ad)에서 CTA 샷이 없습니다.")
                suggestions.append("마지막 샷에 명확한 CTA 장면과 문구를 추가하세요.")
            if ui_count == 0:
                ad_hard_fail = True
                issues.append("앱 UI 신호(화면/알림/진동/통화 UI)가 한 번도 등장하지 않습니다.")
                suggestions.append("최소 1샷에 스마트폰 화면, 알림 팝업, 진동, 통화 UI를 명시하세요.")
            if event_count < 2:
                ad_hard_fail = True
                issues.append("샷별 보이는 사건(event)이 부족해 결과가 단조로울 가능성이 큽니다.")
                suggestions.append("각 샷에 눈에 보이는 사건을 넣으세요 (예: 알림 울림 -> 통화 연결 -> CTA 클릭).")

        if dimensions["hook_score"] < 60:
            issues.append("첫 3초 훅이 약합니다.")
            suggestions.append("초반 3초 안에 알림/진동/급격한 변화 같은 훅 장면을 명시하세요.")

        if dimensions["shot_distinctiveness"] < 55:
            issues.append("샷 간 차별성이 낮아 비슷한 장면이 반복될 수 있습니다.")
            suggestions.append("샷마다 장소/카메라/사건/오브젝트를 분리해 프롬프트를 차별화하세요.")

        if dimensions["event_density"] < 60:
            issues.append("사건 밀도가 낮습니다.")
            suggestions.append("정적인 무드 설명 대신 동작 동사를 포함해 사건 중심으로 작성하세요.")

        if dimensions["ui_signal_density"] < 50:
            issues.append("UI/제품 증거 신호가 부족합니다.")
            suggestions.append("브랜드나 앱의 실제 사용 순간(화면/알림/터치)을 1회 이상 넣으세요.")

        if ad_hard_fail or overall < FINAL_NEEDS_REVIEW_THRESHOLD:
            verdict = "rejected"
        elif overall < FINAL_APPROVED_THRESHOLD:
            verdict = "needs_review"
        else:
            verdict = "approved"

        ad_signals: dict[str, float | bool | int] = {
            "event_shot_count": event_count,
            "ui_signal_shot_count": ui_count,
            "has_cta": has_cta,
            "ad_hard_fail": ad_hard_fail,
        }

        reasoning = (
            f"Second-pass evaluation: overall={overall:.1f}, verdict={verdict}, "
            f"event_shots={event_count}, ui_shots={ui_count}, cta={has_cta}"
        )

        return FinalEvaluationResult(
            verdict=verdict,
            overall_score=round(overall, 1),
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
            ad_signals=ad_signals,
            reasoning=reasoning,
        )

    def _collect_shot_texts(self, shot: "VideoShot", services: list[str]) -> list[str]:
        texts = [shot.script or "", shot.caption or "", shot.background_prompt or ""]
        for service in services:
            params = getattr(shot, service, None)
            if params is not None and hasattr(params, "prompt"):
                texts.append(str(getattr(params, "prompt", "")))
        return [t.lower() for t in texts if t]

    def _event_shot_count(self, plan: "VideoPlan", services: list[str]) -> int:
        count = 0
        for shot in plan.shots:
            text = " ".join(self._collect_shot_texts(shot, services))
            if any(keyword in text for keyword in EVENT_KEYWORDS):
                count += 1
        return count

    def _ui_shot_count(self, plan: "VideoPlan", services: list[str]) -> int:
        count = 0
        for shot in plan.shots:
            text = " ".join(self._collect_shot_texts(shot, services))
            if any(keyword in text for keyword in UI_SIGNAL_KEYWORDS):
                count += 1
        return count

    def _event_density_score(self, plan: "VideoPlan", services: list[str]) -> float:
        if not plan.shots:
            return 0.0
        event_count = self._event_shot_count(plan, services)
        return (event_count / len(plan.shots)) * 100.0

    def _ui_signal_score(self, plan: "VideoPlan", services: list[str]) -> float:
        if not plan.shots:
            return 0.0
        ui_count = self._ui_shot_count(plan, services)
        return (ui_count / len(plan.shots)) * 100.0

    def _tokenize(self, text: str) -> set[str]:
        base = text.lower().replace(",", " ").replace(".", " ").replace("-", " ")
        tokens = {tok for tok in base.split() if len(tok) >= 3}
        return tokens

    def _shot_distinctiveness_score(self, plan: "VideoPlan", services: list[str]) -> float:
        if len(plan.shots) <= 1:
            return 100.0

        shot_tokens: list[set[str]] = []
        for shot in plan.shots:
            text = " ".join(self._collect_shot_texts(shot, services))
            shot_tokens.append(self._tokenize(text))

        similarities: list[float] = []
        for i in range(len(shot_tokens)):
            for j in range(i + 1, len(shot_tokens)):
                a = shot_tokens[i]
                b = shot_tokens[j]
                if not a and not b:
                    similarities.append(1.0)
                    continue
                union = a | b
                inter = a & b
                sim = (len(inter) / len(union)) if union else 1.0
                similarities.append(sim)

        if not similarities:
            return 100.0
        avg_similarity = sum(similarities) / len(similarities)
        return (1.0 - avg_similarity) * 100.0

    def _hook_score(self, plan: "VideoPlan", services: list[str]) -> float:
        if not plan.shots:
            return 0.0

        elapsed = 0
        first_three_texts: list[str] = []
        for shot in plan.shots:
            if elapsed >= 3:
                break
            first_three_texts.extend(self._collect_shot_texts(shot, services))
            elapsed += max(shot.duration_sec, 0)

        text = " ".join(first_three_texts)
        if not text:
            return 0.0

        match_count = sum(1 for keyword in HOOK_KEYWORDS if keyword in text)
        return min(100.0, 40.0 + (match_count * 20.0))

    def _cta_score(self, plan: "VideoPlan") -> float:
        cta_shots = [shot for shot in plan.shots if shot.shot_type == "cta"]
        if not cta_shots:
            return 0.0

        text = " ".join(f"{shot.script} {shot.caption}".lower() for shot in cta_shots)
        if any(keyword in text for keyword in CTA_KEYWORDS):
            return 100.0
        return 60.0


def evaluate_video_plan_final(
    plan: "VideoPlan",
    services: list[str] | None = None,
    intent: "VideoIntent | None" = None,
) -> FinalEvaluationResult:
    evaluator = VideoPlanFinalEvaluator()
    return evaluator.evaluate(plan=plan, services=services, intent=intent)
