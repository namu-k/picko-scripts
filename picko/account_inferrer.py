"""AI-powered inference for account configuration files."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .logger import get_logger

logger = get_logger("account_inferrer")


@dataclass
class AccountSeed:
    """Minimal account information used during account onboarding."""

    account_id: str
    name: str
    description: str
    target_audience: list[str]
    channels: list[str]
    one_liner: str = ""
    tone_hints: list[str] | None = None
    reference_text: str | None = None
    reference_url: str | None = None


class AccountInferrer:
    """Infer scoring/style metadata from AccountSeed via LLM."""

    SCORING_SYSTEM_PROMPT = """당신은 소셜 미디어 콘텐츠 전략가입니다.
아래 계정 정보를 바탕으로 콘텐츠 스코어링에 사용할 interests와 keywords를 추론하세요.

규칙:
- primary interests: 5-8개, 계정의 핵심 주제
- secondary interests: 3-6개, 관련 주제
- high_relevance keywords: 5-10개, 계정과 직접 관련
- medium_relevance keywords: 3-5개, 간접 관련
- low_relevance keywords: 2-3개, 배제 키워드
- trusted_sources: 해당 도메인의 신뢰할 수 있는 소스 이름 (URL 아님)

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:
{
  "interests": {"primary": [...], "secondary": [...]},
  "keywords": {"high_relevance": [...], "medium_relevance": [...], "low_relevance": [...]},
  "trusted_sources": [...]
}"""

    STYLE_SYSTEM_PROMPT = """당신은 소셜 미디어 콘텐츠 스타일 전문가입니다.
아래 계정 정보를 바탕으로 글쓰기 스타일과 비주얼 설정을 추론하세요.

규칙:
- tone.primary: 3-5개의 형용사로 톤 정의
- tone.forbidden: 피해야 할 표현 스타일
- tone.cta_style: CTA(행동 유도) 스타일
- sentence_style: short_emotional | medium_balanced | long_analytical 중 하나
- structure_patterns: 글 구조 패턴 2-3개
- vocabulary: 사용할 어휘 유형 2-3개
- visual_settings.default_layout_preset: corporate | minimal_dark | minimal_light | social_gradient | vibrant 중 하나
- content_themes: 콘텐츠 테마 2-3개

반드시 아래 JSON 형식으로만 응답하세요:
{
  "tone": {"primary": "...", "forbidden": "...", "cta_style": "..."},
  "sentence_style": "...",
  "structure_patterns": [...],
  "vocabulary": [...],
  "visual_settings": {"default_layout_preset": "...", "channel_layouts": {}},
  "content_themes": [...]
}"""

    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Extract JSON payload from plain/markdown-wrapped response text."""
        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json", maxsplit=1)[1].split("```", maxsplit=1)[0]
            elif "```" in json_str:
                json_str = json_str.split("```", maxsplit=1)[1].split("```", maxsplit=1)[0]

            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = json_str[start : end + 1]

            parsed = json.loads(json_str.strip())
            if isinstance(parsed, dict):
                return parsed
            logger.error("LLM JSON response was not an object")
            return {}
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse LLM response as JSON: {exc}")
            return {}

    def infer_scoring(self, seed: AccountSeed) -> dict[str, Any]:
        """Infer scoring.yml structure from AccountSeed."""
        prompt = f"""계정 정보:
- 이름: {seed.name}
- 설명: {seed.description}
- 한줄 요약: {seed.one_liner}
- 타겟 오디언스: {", ".join(seed.target_audience)}
- 운영 채널: {", ".join(seed.channels)}
{f"- 톤 힌트: {', '.join(seed.tone_hints)}" if seed.tone_hints else ""}

위 정보를 바탕으로 interests, keywords, trusted_sources를 추론하세요."""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self.SCORING_SYSTEM_PROMPT,
        )

        result = self._parse_json_response(response)
        if result:
            logger.info(f"Inferred scoring for account: {seed.account_id}")
            return result

        return {
            "interests": {"primary": [], "secondary": []},
            "keywords": {
                "high_relevance": [],
                "medium_relevance": [],
                "low_relevance": [],
            },
            "trusted_sources": [],
        }

    def infer_style(self, seed: AccountSeed) -> dict[str, Any]:
        """Infer style.yml structure from AccountSeed."""
        prompt = f"""계정 정보:
- 이름: {seed.name}
- 설명: {seed.description}
- 한줄 요약: {seed.one_liner}
- 타겟 오디언스: {", ".join(seed.target_audience)}
- 운영 채널: {", ".join(seed.channels)}
{f"- 톤 힌트: {', '.join(seed.tone_hints)}" if seed.tone_hints else ""}
{f"- 레퍼런스 텍스트 (기존 스타일 분석):\n{seed.reference_text[:1000]}" if seed.reference_text else ""}

위 정보를 바탕으로 스타일 설정을 추론하세요."""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self.STYLE_SYSTEM_PROMPT,
        )

        result = self._parse_json_response(response)
        if result:
            logger.info(f"Inferred style for account: {seed.account_id}")
            return result

        return {
            "tone": {"primary": "", "forbidden": "", "cta_style": ""},
            "sentence_style": "medium_balanced",
            "structure_patterns": [],
            "vocabulary": [],
            "visual_settings": {
                "default_layout_preset": "minimal_dark",
                "channel_layouts": {},
            },
            "content_themes": [],
        }

    def generate_account_files(
        self,
        seed: AccountSeed,
        output_dir: Path,
        overwrite: bool = False,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        index_path = output_dir / "_index.yml"
        if overwrite or not index_path.exists():
            index_data = self._build_index_yml(seed)
            self._write_yaml(index_path, index_data)
            logger.info(f"Created: {index_path}")

        channels_path = output_dir / "channels.yml"
        if overwrite or not channels_path.exists():
            channels_data = self._build_channels_yml(seed)
            self._write_yaml(channels_path, channels_data)
            logger.info(f"Created: {channels_path}")

        identity_path = output_dir / "identity.yml"
        if overwrite or not identity_path.exists():
            identity_data = self._build_identity_yml(seed)
            self._write_yaml(identity_path, identity_data)
            logger.info(f"Created: {identity_path}")

        scoring_path = output_dir / "scoring.yml"
        if overwrite or not scoring_path.exists():
            scoring_data = self.infer_scoring(seed)
            self._write_yaml(scoring_path, scoring_data)
            logger.info(f"Created: {scoring_path}")

        content_path = output_dir / "content.yml"
        if overwrite or not content_path.exists():
            style_data = self.infer_style(seed)
            content_data = self._build_content_yml(style_data)
            self._write_yaml(content_path, content_data)
            logger.info(f"Created: {content_path}")

        style_path = output_dir / "style.yml"
        if overwrite and style_path.exists():
            style_path.unlink()

    def _build_index_yml(self, seed: AccountSeed) -> dict[str, Any]:
        return {
            "account_id": seed.account_id,
            "name": seed.name,
            "description": seed.description,
            "style_name": "default",
            "includes": ["scoring", "channels", "content", "identity"],
        }

    def _build_channels_yml(self, seed: AccountSeed) -> dict[str, Any]:
        return {channel: {"enabled": True} for channel in seed.channels}

    def _build_identity_yml(self, seed: AccountSeed) -> dict[str, Any]:
        return {
            "one_liner": seed.one_liner,
            "target_audience": seed.target_audience,
            "value_proposition": "",
            "pillars": [],
            "tone_voice": {},
            "boundaries": [],
            "bio": "",
            "bio_secondary": "",
            "link_purpose": "",
        }

    def _build_content_yml(self, style_data: dict[str, Any]) -> dict[str, Any]:
        visual_settings = style_data.get("visual_settings", {})
        if not isinstance(visual_settings, dict):
            visual_settings = {
                "default_layout_preset": "minimal_dark",
                "channel_layouts": {},
            }

        return {
            "content_settings": {
                "use_exploration": True,
                "apply_reference_style": True,
                "generate_packs": True,
                "generate_image_prompts": True,
            },
            "visual_settings": visual_settings,
            "content_themes": style_data.get("content_themes", []),
        }

    def _write_yaml(self, path: Path, data: dict[str, Any]) -> None:
        """Write YAML file with generation metadata header."""
        header = "# Auto-generated by AccountInferrer\n" f"# Generated at: {self._get_timestamp()}\n\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _get_timestamp(self) -> str:
        """Return current timestamp string."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
