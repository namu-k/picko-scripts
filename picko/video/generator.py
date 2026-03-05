"""
VideoPlan 생성 로직

계정 컨텍스트 → LLM → VideoPlan 생성 + 품질 게이트
"""

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, cast

from picko.account_context import get_identity, get_weekly_slot
from picko.llm_client import get_writer_client
from picko.prompt_loader import PromptLoader
from picko.video.final_evaluator import VideoPlanFinalEvaluator
from picko.video.prompt_templates import (
    get_default_negative_prompt,
    get_service_schema_with_examples,
    merge_service_instructions,
)
from picko.video.quality_scorer import QUALITY_THRESHOLD, VideoPlanScorer
from picko.video.validator import VideoPlanValidator
from picko.video_plan import (
    BrandStyle,
    KlingParams,
    LumaParams,
    PikaParams,
    RunwayParams,
    SoraParams,
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
        enable_final_evaluation: bool = True,
    ) -> None:
        self.account_id: str = account_id
        self.services: list[str] = services or ["luma"]
        self.platforms: list[str] = platforms or ["instagram_reel"]
        self.intent: VideoIntent = intent
        self.content_id: str = content_id
        self.week_of: str = week_of
        self.lang: str = lang
        self.enable_final_evaluation: bool = enable_final_evaluation
        self._feedback: list[str] = []
        self._final_evaluator = VideoPlanFinalEvaluator()
        self._prompt_loader = PromptLoader()

    def generate(self, validate: bool = True) -> VideoPlan:
        """VideoPlan 생성 (품질 게이트 포함)"""
        last_plan: VideoPlan | None = None
        for attempt in range(MAX_RETRIES + 1):
            plan = self._generate_plan()
            last_plan = plan

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

            # 품질 평가 (서비스별 평가 적용)
            scorer = VideoPlanScorer()
            score = scorer.score(plan, self.services)

            if score.overall < QUALITY_THRESHOLD:
                logger.warning(f"품질 점수 낮음 (시도 {attempt + 1}): {score.overall}")
                self._feedback = score.issues + score.suggestions
                continue

            # 통과
            plan.quality_score = score.overall
            plan.quality_issues = score.issues
            plan.quality_suggestions = score.suggestions

            # 2차 최종 평가 에이전트
            if self.enable_final_evaluation:
                final_eval = self._final_evaluator.evaluate(
                    plan=plan,
                    services=self.services,
                    intent=self.intent,
                )
                plan.final_evaluation = final_eval.to_dict()
                if final_eval.verdict != "approved":
                    logger.warning(
                        "최종 평가 미통과 (시도 %s): verdict=%s, score=%.1f",
                        attempt + 1,
                        final_eval.verdict,
                        final_eval.overall_score,
                    )
                    self._feedback = final_eval.issues + final_eval.suggestions
                    continue

            return plan

        # 최대 재시도 초과
        logger.error(f"품질 기준 미달 after {MAX_RETRIES + 1} attempts")
        if last_plan is None:
            raise RuntimeError("VideoPlan 생성에 실패했습니다.")
        last_plan.quality_warning = True
        if self.enable_final_evaluation and not last_plan.final_evaluation:
            final_eval = self._final_evaluator.evaluate(
                plan=last_plan,
                services=self.services,
                intent=self.intent,
            )
            last_plan.final_evaluation = final_eval.to_dict()
        return last_plan

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
        templates = merge_service_instructions(self.services)
        schema_section = self._build_schema_section(self.services)

        # 계정 정보
        account_info = f"""
## 계정 정보
- 계정명: {identity.account_id}
- 한 줄 소개: {identity.one_liner}
- 타겟 오디언스: {", ".join(identity.target_audience)}
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
{chr(10).join(f"- {f}" for f in self._feedback)}
"""

        # 서비스별 기본 negative prompt 섹션
        default_neg_section = self._build_default_negative_section()

        # 모델별 워크플로우 레퍼런스 (문서 기반)
        model_workflow_section = self._build_model_workflow_section()

        return f"""
{templates}

{account_info}

## 영상 목적
- Intent: {self.intent}
- 권장 길이: {intent_config["duration"]}
- 권장 샷 수: {intent_config["shots"]}
- 톤 가이드: {intent_config["tone"]}

{weekly_info}
{content_info}
{feedback_info}

{default_neg_section}

{model_workflow_section}

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
        {schema_section}
      }}
    }}
  ]
}}
"""

    def _build_schema_section(self, services: list[str]) -> str:
        """서비스별 JSON 스키마 섹션 생성"""
        schemas = []
        for service in services:
            schema = get_service_schema_with_examples(service)
            if schema:
                schemas.append(f'"{service}": {schema}')
            else:
                # 폴백: 기본 스키마
                schemas.append(f'"{service}": {{ "prompt": "영문 프롬프트", "negative_prompt": "제외 요소" }}')
        return ",\n        ".join(schemas)

    def _build_default_negative_section(self) -> str:
        """서비스별 기본 negative prompt 섹션 생성"""
        lines = ["## 서비스별 기본 Negative Prompt (참고용)"]
        for service in self.services:
            default_neg = get_default_negative_prompt(service)
            lines.append(f"- {service}: `{default_neg}`")
        return "\n".join(lines)

    def _build_model_workflow_section(self) -> str:
        """모델별 생성 워크플로우 문서를 로드해 프롬프트에 주입"""
        try:
            return self._prompt_loader.render(
                "video",
                name="model_workflows",
                target_services=self.services,
                intent=self.intent,
            ).strip()
        except FileNotFoundError:
            logger.warning("video/model_workflows prompt file not found; skipping workflow section")
            return ""

    def _get_service_schema(self) -> str:
        """각 서비스별 상세 스키마 생성 (서비스별로 완전히 다른 스키마 사용)"""
        return self._build_schema_section(self.services)

    def _get_intent_config(self) -> dict[str, str]:
        """Intent별 설정"""
        configs: dict[VideoIntent, dict[str, str]] = {
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

    @staticmethod
    def _to_str(value: object, default: str = "") -> str:
        if isinstance(value, str):
            return value
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _to_bool(value: object, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        return default

    @staticmethod
    def _to_int(value: object, default: int = 0) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if not lowered:
                return default
            aliases = {
                "low": 2,
                "medium": 3,
                "med": 3,
                "high": 4,
            }
            if lowered in aliases:
                return aliases[lowered]
            try:
                return int(float(lowered))
            except ValueError:
                return default
        return default

    @classmethod
    def _to_bounded_int(
        cls,
        value: object,
        default: int,
        min_value: int,
        max_value: int,
    ) -> int:
        coerced = cls._to_int(value, default)
        return max(min_value, min(max_value, coerced))

    def _parse_response(self, raw: str, identity: "AccountIdentity", content_summary: str | None) -> VideoPlan:
        """LLM 응답 파싱"""
        del identity
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
        raw_shots = data.get("shots", [])
        if not isinstance(raw_shots, list):
            raise ValueError("LLM 응답의 shots 필드는 배열이어야 합니다.")

        for idx, s in enumerate(raw_shots, start=1):
            if not isinstance(s, dict):
                continue

            raw_services_data = s.get("services", {})
            services_data = raw_services_data if isinstance(raw_services_data, dict) else {}
            raw_first_service_params = (
                services_data.get(self.services[0], {}) if services_data else s.get(self.services[0], {})
            )
            first_service_params = raw_first_service_params if isinstance(raw_first_service_params, dict) else {}

            shot = VideoShot(
                index=self._to_bounded_int(s.get("index", idx), idx, 1, 99),
                duration_sec=self._to_bounded_int(s.get("duration_sec", 5), 5, 1, 300),
                shot_type=self._to_str(s.get("shot_type", "main"), "main"),
                script=self._to_str(s.get("script", ""), ""),
                caption=self._to_str(s.get("caption", ""), ""),
                background_prompt=self._to_str(first_service_params.get("prompt", ""), ""),
            )

            # 모든 서비스 파라미터 설정
            for service in self.services:
                raw_service_params = services_data.get(service, {}) if services_data else s.get(service, {})
                service_params = raw_service_params if isinstance(raw_service_params, dict) else {}
                if not service_params:
                    continue

                if service == "luma":
                    shot.luma = LumaParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        camera_motion=self._to_str(service_params.get("camera_motion", ""), ""),
                        motion_intensity=self._to_bounded_int(
                            service_params.get("motion_intensity", 3),
                            3,
                            1,
                            5,
                        ),
                        style_preset=self._to_str(service_params.get("style_preset", ""), ""),
                        start_image_url=self._to_str(service_params.get("start_image_url", ""), ""),
                        end_image_url=self._to_str(service_params.get("end_image_url", ""), ""),
                        loop=self._to_bool(service_params.get("loop", False), False),
                    )
                elif service == "runway":
                    shot.runway = RunwayParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        motion=self._to_bounded_int(service_params.get("motion", 5), 5, 1, 10),
                        camera_move=self._to_str(service_params.get("camera_move", ""), ""),
                        seed=self._to_int(service_params.get("seed", 0), 0),
                        upscale=self._to_bool(service_params.get("upscale", False), False),
                    )
                elif service == "pika":
                    shot.pika = PikaParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        pikaffect=self._to_str(service_params.get("pikaffect", ""), ""),
                        style_preset=self._to_str(service_params.get("style_preset", ""), ""),
                        motion_intensity=self._to_bounded_int(
                            service_params.get("motion_intensity", 3),
                            3,
                            1,
                            5,
                        ),
                    )
                elif service == "kling":
                    shot.kling = KlingParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        camera_motion=self._to_str(service_params.get("camera_motion", ""), ""),
                        motion_intensity=self._to_bounded_int(
                            service_params.get("motion_intensity", 3),
                            3,
                            1,
                            5,
                        ),
                        style=self._to_str(service_params.get("style", ""), ""),
                    )
                elif service == "veo":
                    shot.veo = VeoParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        generate_audio=self._to_bool(service_params.get("generate_audio", True), True),
                        audio_mood=self._to_str(service_params.get("audio_mood", ""), ""),
                        style_preset=self._to_str(service_params.get("style_preset", ""), ""),
                    )
                elif service == "sora":
                    shot.sora = SoraParams(
                        prompt=self._to_str(service_params.get("prompt", ""), ""),
                        negative_prompt=self._to_str(service_params.get("negative_prompt", ""), ""),
                        style=self._to_str(service_params.get("style", "cinematic"), "cinematic"),
                        camera_motion=self._to_str(service_params.get("camera_motion", ""), ""),
                    )

            shots.append(shot)

        plan = VideoPlan(
            id=f"video_{self.account_id}_{self._generate_id()}",
            account=self.account_id,
            intent=cast(VideoIntent, self.intent),
            goal=self._to_str(data.get("goal", ""), ""),
            source=VideoSource(
                type="longform" if content_summary else "account_only",
                id=self.content_id,
                summary=content_summary or "",
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
