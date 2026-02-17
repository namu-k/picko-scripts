"""
프롬프트 합성 모듈
기본 프롬프트 + 스타일 프로필 + 계정 정체성 + 주간 컨텍스트를 합성
"""

import json
from dataclasses import dataclass, field
from typing import Any

from jinja2 import Template

from .account_context import AccountIdentity, StyleProfile, WeeklySlot, get_identity, get_loader, get_weekly_slot
from .config import get_config
from .logger import get_logger
from .prompt_loader import get_prompt_loader

logger = get_logger("prompt_composer")


@dataclass
class PromptLayer:
    """프롬프트 레이어 정보"""

    name: str
    content: str = ""
    variables: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ComposedPrompt:
    """합성된 프롬프트 결과"""

    content: str
    layers: list[PromptLayer]
    variables: dict
    account_id: str
    content_type: str


class PromptComposer:
    """
    프롬프트 합성기

    여러 소스에서 프롬프트를 로드하고 합성하여 최종 프롬프트를 생성합니다.

    레이어 구조:
    1. base_prompt: 기본 프롬프트 (config/prompts/)
    2. style_layer: 스타일 특성 (config/reference_styles/)
    3. identity_layer: 계정 정체성 (tone, target)
    4. context_layer: 주간 컨텍스트 (CTA, 목표)
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.layers: list[PromptLayer] = []
        self.variables: dict[str, Any] = {}

        # 로더들
        self._prompt_loader = get_prompt_loader()
        self._context_loader = get_loader()

        # 캐시
        self._cache: dict[str, ComposedPrompt] = {}

        logger.debug(f"PromptComposer initialized for account: {account_id}")

    def reset(self) -> "PromptComposer":
        """모든 레이어와 변수 초기화"""
        self.layers = []
        self.variables = {}
        return self

    def load_base_prompt(self, content_type: str) -> "PromptComposer":
        """
        기본 프롬프트 로드

        Args:
            content_type: 콘텐츠 타입 ("longform", "pack_twitter", "image" 등)
        """
        # 프롬프트 경로 매핑
        type_to_path = {
            "longform": "longform/default.md",
            "longform_with_exploration": "longform/with_exploration.md",
            "longform_with_reference": "longform/with_reference.md",
            "pack_twitter": "packs/twitter.md",
            "pack_linkedin": "packs/linkedin.md",
            "pack_newsletter": "packs/newsletter.md",
            "pack_instagram": "packs/instagram.md",
            "pack_threads": "packs/threads.md",
            "image": "image/default.md",
            "image_twitter": "image/twitter.md",
            "image_linkedin": "image/linkedin.md",
            "image_newsletter": "image/newsletter.md",
            "exploration": "exploration/default.md",
            "reference": "reference/analyze.md",
        }

        prompt_path = type_to_path.get(content_type, f"{content_type}/default.md")

        try:
            content = self._prompt_loader.load(prompt_path)
            layer = PromptLayer(name="base", content=content)
            self.layers.append(layer)
            logger.debug(f"Loaded base prompt: {prompt_path}")
        except Exception as e:
            logger.warning(f"Failed to load base prompt {prompt_path}: {e}")
            # 기본 프롬프트 없이 진행

        return self

    def apply_style(self, style_name: str | None = None) -> "PromptComposer":
        """
        스타일 프로필 적용

        Args:
            style_name: 스타일 이름 (None이면 계정 기본 스타일 사용)
        """
        if style_name is None:
            # 계정 프로필에서 style_name 확인
            config = get_config()
            account_profile = config.get_account(self.account_id)
            if account_profile:
                style_name = account_profile.get("style_name")

        if not style_name:
            logger.debug("No style profile to apply")
            return self

        style_profile = self._context_loader.load_style_profile(style_name)
        if not style_profile:
            logger.warning(f"Style profile not found: {style_name}")
            return self

        # 스타일 특성을 프롬프트 섹션으로 변환
        style_section = self._build_style_section(style_profile)
        layer = PromptLayer(name="style", content=style_section)
        self.layers.append(layer)
        logger.debug(f"Applied style profile: {style_name}")

        return self

    def apply_identity(self, identity: AccountIdentity | None = None) -> "PromptComposer":
        """
        계정 정체성 적용

        Args:
            identity: 계정 정체성 (None이면 로드)
        """
        if identity is None:
            identity = get_identity(self.account_id)

        if not identity:
            logger.debug("No identity to apply")
            return self

        # 정체성을 프롬프트 섹션으로 변환
        identity_section = self._build_identity_section(identity)
        layer = PromptLayer(name="identity", content=identity_section)
        self.layers.append(layer)

        # 변수에 타겟 추가
        if identity.target_audience:
            self.variables["target_audience"] = identity.target_audience
        if identity.tone_voice:
            self.variables["tone_voice"] = identity.tone_voice

        logger.debug(f"Applied identity for: {self.account_id}")
        return self

    def apply_context(self, slot: WeeklySlot | None = None, week_of: str | None = None) -> "PromptComposer":
        """
        주간 컨텍스트 적용

        Args:
            slot: 주간 슬롯 (None이면 week_of로 로드)
            week_of: 주간 시작일 (YYYY-MM-DD)
        """
        if slot is None and week_of:
            slot = get_weekly_slot(week_of)

        if not slot:
            logger.debug("No weekly context to apply")
            return self

        # 컨텍스트를 변수로 추가
        if slot.cta:
            self.variables["cta"] = slot.cta
            self.variables["call_to_action"] = slot.cta
        if slot.customer_outcome:
            self.variables["customer_outcome"] = slot.customer_outcome
            self.variables["week_goal"] = slot.customer_outcome
        if slot.operator_kpi:
            self.variables["operator_kpi"] = slot.operator_kpi

        logger.debug(f"Applied weekly context for: {slot.week_of}")
        return self

    def set_variables(self, **kwargs) -> "PromptComposer":
        """변수 설정"""
        self.variables.update(kwargs)
        return self

    def compose(self, content_type: str = "longform") -> ComposedPrompt:
        """
        모든 레이어를 합성해서 최종 프롬프트 반환

        Args:
            content_type: 콘텐츠 타입 (캐싱용)

        Returns:
            ComposedPrompt 인스턴스
        """

        # 캐시 키 생성 (list/dict를 JSON 문자열로 변환하여 hash 가능하게)
        def make_hashable(obj: Any) -> str:
            if isinstance(obj, (list, dict)):
                return json.dumps(obj, sort_keys=True, ensure_ascii=False)
            return str(obj)

        vars_hash = hash(frozenset((k, make_hashable(v)) for k, v in self.variables.items()))
        cache_key = f"{self.account_id}:{content_type}:{vars_hash}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # 레이어 합성
        sections = []
        for layer in self.layers:
            if layer.enabled and layer.content:
                sections.append(f"\n{layer.content}\n")

        # 최종 프롬프트 조합
        if sections:
            # 기본 프롬프트 뒤에 추가 레이어를 붙이는 방식
            final_content = self.layers[0].content if self.layers else ""

            # 스타일/아이덴티티 레이어는 "스타일 가이드" 섹션으로 추가
            style_sections = [
                layer.content for layer in self.layers if layer.name in ("style", "identity") and layer.content
            ]
            if style_sections:
                final_content += "\n\n---\n\n## 작성 스타일 가이드\n\n"
                final_content += "\n".join(style_sections)
        else:
            final_content = ""

        result = ComposedPrompt(
            content=final_content,
            layers=list(self.layers),
            variables=dict(self.variables),
            account_id=self.account_id,
            content_type=content_type,
        )

        self._cache[cache_key] = result
        logger.info(f"Composed prompt for {self.account_id}:{content_type}")

        return result

    def _build_style_section(self, style: StyleProfile) -> str:
        """스타일 프로필을 프롬프트 섹션으로 변환"""
        sections = []

        char = style.characteristics

        if "tone" in char:
            tones = char["tone"]
            if isinstance(tones, list):
                sections.append(f"- **어조**: {', '.join(tones)}")

        if "sentence_style" in char:
            sections.append(f"- **문장 스타일**: {char['sentence_style']}")

        if "structure_patterns" in char:
            patterns = char["structure_patterns"]
            if isinstance(patterns, list):
                sections.append(f"- **구조 패턴**: {', '.join(patterns)}")

        if "vocabulary" in char:
            vocab = char["vocabulary"]
            if isinstance(vocab, list):
                sections.append(f"- **어휘 스타일**: {', '.join(vocab)}")

        if "hooks" in char:
            hooks = char["hooks"]
            if isinstance(hooks, list):
                sections.append(f"- **시작 방식**: {', '.join(hooks)}")

        if "closings" in char:
            closings = char["closings"]
            if isinstance(closings, list):
                sections.append(f"- **마무리 방식**: {', '.join(closings)}")

        if sections:
            return "### 스타일 특성\n\n" + "\n".join(sections)
        return ""

    def _build_identity_section(self, identity: AccountIdentity) -> str:
        """계정 정체성을 프롬프트 섹션으로 변환"""
        sections = []

        if identity.one_liner:
            sections.append(f"- **계정 정체성**: {identity.one_liner}")

        if identity.target_audience:
            targets = identity.target_audience
            if isinstance(targets, list):
                sections.append(f"- **타겟 독자**: {', '.join(targets)}")

        if identity.tone_voice:
            tone = identity.tone_voice
            if isinstance(tone, dict):
                if "tone" in tone:
                    sections.append(f"- **톤&보이스**: {tone['tone']}")
                if "forbidden" in tone:
                    sections.append(f"- **금칙어**: {tone['forbidden']}")

        if identity.pillars:
            pillars = identity.pillars
            if isinstance(pillars, list):
                sections.append(f"- **필러(주제 영역)**: {', '.join(pillars)}")

        if sections:
            return "### 계정 정체성\n\n" + "\n".join(sections)
        return ""

    def render(self, composed: ComposedPrompt, extra_variables: dict | None = None) -> str:
        """
        합성된 프롬프트를 렌더링

        Args:
            composed: 합성된 프롬프트
            extra_variables: 추가 변수

        Returns:
            렌더링된 프롬프트 문자열
        """
        variables = dict(composed.variables)
        if extra_variables:
            variables.update(extra_variables)

        try:
            template = Template(composed.content)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Failed to render prompt: {e}")
            return composed.content


# ─────────────────────────────────────────────────────────────────────────────
# 편의 함수
# ─────────────────────────────────────────────────────────────────────────────

_composer_cache: dict[str, PromptComposer] = {}


def get_composer(account_id: str) -> PromptComposer:
    """
    계정용 PromptComposer 인스턴스 반환 (캐시)

    Args:
        account_id: 계정 ID

    Returns:
        PromptComposer 인스턴스
    """
    if account_id not in _composer_cache:
        _composer_cache[account_id] = PromptComposer(account_id)
    return _composer_cache[account_id]


def get_effective_prompt(
    account_id: str,
    content_type: str,
    weekly_slot: WeeklySlot | None = None,
    week_of: str | None = None,
    include_style: bool = True,
    include_identity: bool = True,
    variables: dict | None = None,
) -> str:
    """
    합성된 프롬프트 반환 (편의 함수)

    Args:
        account_id: 계정 ID
        content_type: 콘텐츠 타입 ("longform", "pack_twitter", "image" 등)
        weekly_slot: 주간 슬롯
        week_of: 주간 시작일 (weekly_slot 없으면 사용)
        include_style: 스타일 프로필 포함 여부
        include_identity: 계정 정체성 포함 여부
        variables: 추가 변수

    Returns:
        합성된 프롬프트 문자열
    """
    composer = get_composer(account_id)
    composer.reset()

    # 레이어 로드
    composer.load_base_prompt(content_type)

    if include_style:
        composer.apply_style()

    if include_identity:
        composer.apply_identity()

    composer.apply_context(weekly_slot, week_of)

    if variables:
        composer.set_variables(**variables)

    # 합성 및 렌더링
    composed = composer.compose(content_type)
    return composer.render(composed)


def clear_composer_cache() -> None:
    """컴포저 캐시 비우기"""
    _composer_cache.clear()
    logger.debug("Cleared composer cache")
