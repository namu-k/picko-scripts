"""
VideoPlan 생성 로직

계정 컨텍스트 → LLM → VideoPlan 생성 + 품질 게이트
"""

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from picko.account_context import get_identity, get_weekly_slot
from picko.llm_client import get_writer_client
from picko.video.quality_scorer import QUALITY_THRESHOLD, VideoPlanScorer
from picko.video.validator import VideoPlanValidator
from picko.video_plan import (
    BrandStyle,
    KlingParams,
    LumaParams,
    PikaParams,
    RunwayParams,
    VeoParams,
    VideoIntent,
    VideoPlan,
    VideoShot,
    VideoSource,
)

if TYPE_CHECKING:
    from picko.account_context import AccountIdentity, WeeklySlot

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class VideoGenerator:
    """영상 기획서 생성기"""

    def __init__(
        self,
        account_id: str,
        services: list[str] | None = None,
        platforms: list[str] | None = None,
        intent: VideoIntent = "ad",
        content_id: str = "",
        week_of: str = "",
        lang: str = "ko",
    ) -> None:
        self.account_id = account_id
        self.services = services or ["luma"]
        self.platforms = platforms or ["instagram_reel"]
        self.intent = intent
        self.content_id = content_id
        self.week_of = week_of
        self.lang = lang
        self._feedback: list[str] = []

    def generate(self, validate: bool = True) -> VideoPlan:
        """VideoPlan 생성 (품질 게이트 포함)"""
        for attempt in range(MAX_RETRIES + 1):
            plan = self._generate_plan()

            if not validate:
                return plan

            # 검증
            validator = VideoPlanValidator(plan)
            errors = validator.validate()
            critical = [e for e in errors if e.severity == "error"]

            if critical:
                logger.warning(f"검증 실패 (시도 {attempt + 1}): {critical}")
                self._feedback = [e.message for e in critical]
                continue

            # 품질 평가
            scorer = VideoPlanScorer()
            score = scorer.score(plan)

            if score.overall < QUALITY_THRESHOLD:
                logger.warning(f"품질 점수 낮음 (시도 {attempt + 1}): {score.overall}")
                self._feedback = score.issues + score.suggestions
                continue

            # 통과
            plan.quality_score = score.overall
            plan.quality_issues = score.issues
            plan.quality_suggestions = score.suggestions
            return plan

        # 최대 재시도 초과
        logger.error(f"품질 기준 미달 after {MAX_RETRIES + 1} attempts")
        plan.quality_warning = True
        return plan

    def _generate_plan(self) -> VideoPlan:
        """VideoPlan 생성 (내부)"""
        identity = get_identity(self.account_id)
        if not identity:
            raise ValueError(f"계정을 찾을 수 없습니다: {self.account_id}")
        weekly_slot = get_weekly_slot(self.week_of) if self.week_of else None
        content_summary = self._load_content() if self.content_id else None

        prompt = self._build_prompt(identity, weekly_slot, content_summary)
        client = get_writer_client()
        raw = client.generate(prompt)

        return self._parse_response(raw, identity, content_summary)

    def _build_prompt(
        self,
        identity: "AccountIdentity",
        weekly_slot: "WeeklySlot | None" = None,
        content_summary: str | None = None,
    ) -> str:
        """LLM 프롬프트 빌드"""
        from picko.video.prompt_templates import merge_service_templates

        templates = merge_service_templates(self.services)

        # 계정 정보
        account_info = f"""
## 계정 정보
- 계정명: {identity.account_id}
- 한 줄 소개: {identity.one_liner}
- 타겟 오디언스: {', '.join(identity.target_audience)}
- 가치 제안: {identity.value_proposition}
"""

        # Intent 설정
        intent_config = self._get_intent_config()

        # 주간 맥락
        weekly_info = ""
        if weekly_slot:
            weekly_info = f"""
## 이번 주 목표
- Customer Outcome: {weekly_slot.customer_outcome}
- CTA: {weekly_slot.cta}
- KPI: {weekly_slot.operator_kpi}
"""

        # 참고 콘텐츠
        content_info = ""
        if content_summary:
            content_info = f"""
## 참고 콘텐츠
{content_summary}
"""

        # 이전 피드백
        feedback_info = ""
        if self._feedback:
            feedback_info = f"""
## 이전 시도 피드백 (반영 필요)
{chr(10).join(f'- {f}' for f in self._feedback)}
"""

        return f"""
{templates}

{account_info}

## 영상 목적
- Intent: {self.intent}
- 권장 길이: {intent_config['duration']}
- 권장 샷 수: {intent_config['shots']}
- 톤 가이드: {intent_config['tone']}

{weekly_info}
{content_info}
{feedback_info}

## 출력 형식
다음 JSON 형식으로 출력:
{{
  "goal": "영상 목표",
  "shots": [
    {{
      "index": 1,
      "duration_sec": 5,
      "shot_type": "intro|main|cta",
      "script": "장면 설명",
      "caption": "화면 자막",
      "services": {{
        {self._get_service_schema()}
      }}
    }}
  ]
}}
"""

    def _get_service_schema(self) -> str:
        """각 서비스별 스키마 생성"""
        schemas = []
        for service in self.services:
            schemas.append(f'"{service}": {{ "prompt": "서비스용 프롬프트 (영문)", "negative_prompt": "제외 요소" }}')
        return ", ".join(schemas)

    def _get_intent_config(self) -> dict:
        """Intent별 설정"""
        configs = {
            "ad": {
                "shots": "3-5개",
                "duration": "15-30초",
                "tone": "전환 유도, 첫 3초 훅 필수, 마지막 샷 CTA 필수",
            },
            "explainer": {
                "shots": "5-8개",
                "duration": "45-120초",
                "tone": "교육적, 인트로→본론→결론 구조",
            },
            "brand": {
                "shots": "3-5개",
                "duration": "15-60초",
                "tone": "시네마틱, 텍스트 최소화, 분위기 중심",
            },
            "trend": {
                "shots": "3-4개",
                "duration": "15-30초",
                "tone": "빠른 템포, 대화체, 시의성 강조",
            },
        }
        return configs.get(self.intent, configs["ad"])

    def _parse_response(self, raw: str, identity: "AccountIdentity", content_summary: str | None) -> VideoPlan:
        """LLM 응답 파싱"""
        # JSON 추출 (```json ... ``` 블록 처리)
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
        if json_match:
            raw = json_match.group(1)

        # 추가 텍스트 제거 (JSON 앞뒤 텍스트)
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            raw = raw[json_start:json_end]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}\n원본 응답: {raw[:500]}...")
            raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")

        # VideoPlan 생성
        shots = []
        for s in data.get("shots", []):
            services_data = s.get("services", {})
            first_service_params = (
                services_data.get(self.services[0], {}) if services_data else s.get(self.services[0], {})
            )

            shot = VideoShot(
                index=s["index"],
                duration_sec=s["duration_sec"],
                shot_type=s.get("shot_type", "main"),
                script=s.get("script", ""),
                caption=s.get("caption", ""),
                background_prompt=first_service_params.get("prompt", ""),
            )

            # 모든 서비스 파라미터 설정
            for service in self.services:
                service_params = services_data.get(service, {}) if services_data else s.get(service, {})
                if not service_params:
                    continue

                if service == "luma":
                    shot.luma = LumaParams(
                        prompt=service_params.get("prompt", ""),
                        negative_prompt=service_params.get("negative_prompt", ""),
                        camera_motion=service_params.get("camera_motion", ""),
                    )
                elif service == "runway":
                    shot.runway = RunwayParams(
                        prompt=service_params.get("prompt", ""),
                        negative_prompt=service_params.get("negative_prompt", ""),
                        motion=service_params.get("motion", 5),
                        camera_move=service_params.get("camera_move", ""),
                    )
                elif service == "pika":
                    shot.pika = PikaParams(
                        prompt=service_params.get("prompt", ""),
                        negative_prompt=service_params.get("negative_prompt", ""),
                        pikaffect=service_params.get("pikaffect", ""),
                    )
                elif service == "kling":
                    shot.kling = KlingParams(
                        prompt=service_params.get("prompt", ""),
                        negative_prompt=service_params.get("negative_prompt", ""),
                        camera_motion=service_params.get("camera_motion", ""),
                    )
                elif service == "veo":
                    shot.veo = VeoParams(
                        prompt=service_params.get("prompt", ""),
                        negative_prompt=service_params.get("negative_prompt", ""),
                        generate_audio=service_params.get("generate_audio", True),
                    )

            shots.append(shot)

        plan = VideoPlan(
            id=f"video_{self.account_id}_{self._generate_id()}",
            account=self.account_id,
            intent=self.intent,
            goal=data.get("goal", ""),
            source=VideoSource(
                type="longform" if content_summary else "account_only",
                id=self.content_id,
            ),
            brand_style=BrandStyle(tone=""),
            shots=shots,
            target_services=self.services,
            platforms=self.platforms,
        )

        return plan

    def _generate_id(self) -> str:
        """고유 ID 생성"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _load_content(self) -> str | None:
        """Vault에서 longform 로드 (향후 구현)"""
        # TODO: VaultIO로 Content/Longform/longform_{content_id}.md 로드
        return None
