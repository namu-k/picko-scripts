"""
템플릿 렌더링 모듈
Jinja2 기반 콘텐츠 템플릿 처리
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .logger import get_logger

if TYPE_CHECKING:
    from .layout_config import LayoutConfig

logger = get_logger("templates")

# 기본 템플릿 디렉토리
DEFAULT_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class TemplateRenderer:
    """Jinja2 템플릿 렌더러"""

    def __init__(self, templates_dir: str | Path | None = None):
        if templates_dir is None:
            templates_dir = DEFAULT_TEMPLATES_DIR

        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # 커스텀 필터 등록
        self._register_filters()

        logger.debug(f"TemplateRenderer initialized: {self.templates_dir}")

    def _register_filters(self):
        """커스텀 Jinja2 필터 등록"""

        def format_date(value, fmt="%Y-%m-%d"):
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except ValueError:
                    return value
            if isinstance(value, datetime):
                return value.strftime(fmt)
            return value

        def truncate_smart(value, length=100):
            """단어 경계에서 자르기"""
            if len(value) <= length:
                return value
            truncated = value[:length].rsplit(" ", 1)[0]
            return truncated + "..."

        def to_wikilink(value):
            """Obsidian wikilink 형식으로 변환"""
            return f"[[{value}]]"

        def to_hashtag(value):
            """해시태그 형식으로 변환"""
            tag = value.replace(" ", "_").lower()
            return f"#{tag}"

        self.env.filters["format_date"] = format_date
        self.env.filters["truncate_smart"] = truncate_smart
        self.env.filters["wikilink"] = to_wikilink
        self.env.filters["hashtag"] = to_hashtag

    def render(self, template_name: str, **context) -> str:
        """
        템플릿 렌더링

        Args:
            template_name: 템플릿 파일명
            **context: 템플릿 변수

        Returns:
            렌더링된 문자열
        """
        template = self.env.get_template(template_name)
        result = template.render(**context)
        logger.debug(f"Rendered template: {template_name}")
        return result

    def render_string(self, template_string: str, **context) -> str:
        """
        문자열 템플릿 렌더링

        Args:
            template_string: 템플릿 문자열
            **context: 템플릿 변수

        Returns:
            렌더링된 문자열
        """
        template = self.env.from_string(template_string)
        return template.render(**context)

    # ─────────────────────────────────────────────────────────────
    # 콘텐츠 타입별 렌더링
    # ─────────────────────────────────────────────────────────────

    def render_input_note(self, content: dict) -> str:
        """
        Input 노트 렌더링

        Args:
            content: 콘텐츠 정보

        Returns:
            마크다운 문자열
        """
        template = """---
id: {{ id }}
title: "{{ title }}"
source: {{ source }}
source_url: {{ source_url }}
publish_date: {{ publish_date }}
collected_at: {{ collected_at }}
status: inbox
writing_status: pending
score:
  novelty: {{ score.novelty }}
  relevance: {{ score.relevance }}
  quality: {{ score.quality }}
  total: {{ score.total }}
tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}---

# {{ title }}

> [!info] 소스
> [{{ source }}]({{ source_url }}) | {{ publish_date | format_date }}

> [!tip] 글쓰기 처리 방법 선택
> - [ ] **자동 작성**: API로 블로그/소셜 미디어 콘텐츠 자동 생성 (체크하고 저장)
> - [ ] **수동 작성**: GPT Web 등에서 직접 작성完成后, 아래에 결과를 입력하세요

## 요약

{{ summary }}

## 핵심 포인트

{% for point in key_points %}- {{ point }}
{% endfor %}

## 원문 발췌

{{ excerpt }}

---

## 수동 작성 결과 (수동 작성 선택 시)

<!-- 자동 작성을 원하시면 위 체크박스에 체크하고 저장하세요 -->
<!-- 수동 작성 완료 후에는 writing_status를 'completed'로 변경하세요 -->
"""
        return self.render_string(template, **content)

    def render_digest(self, date: str, items: list[dict]) -> str:
        """
        Digest 노트 렌더링

        Args:
            date: 날짜 (YYYY-MM-DD)
            items: 콘텐츠 항목 리스트

        Returns:
            마크다운 문자열
        """
        template = """---
type: digest
date: {{ date }}
created_at: {{ created_at }}
total_items: {{ items | length }}
---

# Daily Digest: {{ date }}

> [!info] 처리 방법
> - 체크박스 `[ ]`를 `[x]`로 변경하고 저장하면 글쓰기 API가 실행됩니다
> - 수동 작성을 원하시면 Input 노트에서 "수동 작성"을 체크하세요

{% for item in items %}
{% if item.writing_status != 'completed' %}
## [ ] {{ item.title }}

- **ID**: {{ item.id }}
- **Writing Status**: {{ item.writing_status | default("pending") }}
- **Score**: {{ item.score.total | round(2) }} (N:{{ item.score.novelty | round(2) }} R:{{
  item.score.relevance | round(2) }} Q:{{ item.score.quality | round(2) }})
- **Source**: [{{ item.source }}]({{ item.source_url }})
- **Input**: {{ item.id | wikilink }}

> {{ item.summary | truncate_smart(150) }}

---
{% endif %}
{% endfor %}

## 완료된 항목

{% for item in items %}
{% if item.writing_status == 'completed' %}
- [x] {{ item.title }} ({{ item.id }})
{% endif %}
{% endfor %}
"""
        return self.render_string(template, date=date, created_at=datetime.now().isoformat(), items=items)

    def render_longform(self, content: dict, channel_config: dict | None = None) -> str:
        """
        Longform 콘텐츠 렌더링

        Args:
            content: 콘텐츠 정보
            channel_config: 채널별 설정

        Returns:
            마크다운 문자열
        """
        template = """---
id: {{ id }}
title: "{{ title }}"
type: longform
status: draft
source_input: {{ source_input_id | wikilink }}
derivative_status: pending
packs_channels: []
images_approved: false
created_at: {{ created_at }}
{% if tags %}tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}{% endif %}
---

# {{ title }}

> [!tip] 파생 콘텐츠 승인
> 이 롱폼을 바탕으로 소셜 미디어 팩/이미지를 생성하려면 아래 체크박스를 선택하세요:
>
> **팩 생성 채널 선택**:
> - [ ] **Twitter**: 캐주얼한 톤, 280자 제한
> - [ ] **LinkedIn**: 프로페셔널 톤, 700자
> - [ ] **Newsletter**: 에디토리얼 톤, 1000자
> - [ ] **Instagram**: 비주얼 중심, 500자
> - [ ] **Threads**: 캐주얼 톤, 500자
>
> **이미지 생성**:
> - [ ] **이미지 프롬프트**: 썸네일용 이미지 프롬프트 자동 생성
>
> 체크 후 저장하면 `generate_content --type packs,images` 실행 시 선택된 채널만 자동 생성됩니다.

{{ intro }}

## 핵심 내용

{{ main_content }}

## 주요 시사점

{{ takeaways }}

{% if cta %}
---

{{ cta }}
{% endif %}
"""
        return self.render_string(template, created_at=datetime.now().isoformat(), **content)

    def render_pack(self, content: dict, channel: str, channel_config: dict | None = None) -> str:
        """
        채널별 패키징 콘텐츠 렌더링

        Args:
            content: 콘텐츠 정보
            channel: 채널명 (twitter, linkedin 등)
            channel_config: 채널 설정

        Returns:
            마크다운 문자열
        """
        channel_config = channel_config or {}
        max_length = channel_config.get("max_length", 280)
        use_hashtags = channel_config.get("hashtags", True)

        template = """---
id: {{ id }}
type: pack
channel: {{ channel }}
source_longform: {{ source_longform_id | wikilink }}
status: draft
created_at: {{ created_at }}
---

# {{ channel | title }} Pack

**Character Count**: {{ text | length }} / {{ max_length }}

---

{{ text }}

{% if use_hashtags and hashtags %}
{{ hashtags | join(" ") }}
{% endif %}
"""
        return self.render_string(
            template,
            channel=channel,
            max_length=max_length,
            use_hashtags=use_hashtags,
            created_at=datetime.now().isoformat(),
            **content,
        )

    def render_image_prompt(self, content: dict) -> str:
        """
        이미지 프롬프트 렌더링

        Args:
            content: 프롬프트 정보

        Returns:
            마크다운 문자열
        """
        template = """---
id: {{ id }}
type: image_prompt
source_content: {{ source_content_id | wikilink }}
status: pending
created_at: {{ created_at }}
---

# Image Prompt

## 메인 프롬프트

{{ prompt }}

## 스타일 가이드

- **Style**: {{ style | default("modern, clean") }}
- **Mood**: {{ mood | default("professional") }}
- **Colors**: {{ colors | default("brand colors") }}

## 네거티브 프롬프트

{{ negative_prompt | default("text, watermark, low quality") }}

## 참고 이미지

{% if reference_images %}
{% for img in reference_images %}- {{ img }}
{% endfor %}
{% else %}
없음
{% endif %}
"""
        return self.render_string(template, created_at=datetime.now().isoformat(), **content)

    def render_exploration(self, content: dict) -> str:
        """
        주제 탐색 노트 렌더링

        Args:
            content: 탐색 결과 정보

        Returns:
            마크다운 문자열
        """
        template = """---
id: {{ id }}
type: exploration
source_input: {{ source_input_id | wikilink }}
status: completed
created_at: {{ created_at }}
{% if tags %}tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}{% endif %}
---

# 주제 탐색: {{ title }}

## 🎯 주제 확장

{{ topic_expansion | default("분석 중...") }}

## 💭 관련 논의와 반론

{{ related_discussions | default("분석 중...") }}

## 💡 독자 인사이트

{{ reader_insights | default("분석 중...") }}

## 📝 롱폼 작성 가이드

{{ writing_guide | default("분석 중...") }}

---
> 이 탐색 결과는 롱폼 작성 시 컨텍스트로 사용됩니다.
"""
        return self.render_string(template, created_at=datetime.now().isoformat(), **content)


# ─────────────────────────────────────────────────────────────
# 이미지 템플릿 렌더러
# ─────────────────────────────────────────────────────────────


class ImageRenderer:
    """Render HTML templates for images."""

    # Whitelist of valid template names for security
    VALID_TEMPLATES = frozenset(["quote", "card", "list", "data", "carousel", "social_quote", "modern_card"])

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(DEFAULT_TEMPLATES_DIR / "images")),
            autoescape=select_autoescape(["html"]),
        )

    def render_image(
        self,
        template: str,
        context: dict,
        layout_config: LayoutConfig | None = None,
        layout_preset: str | None = None,
        layout_theme: str | None = None,
        layout_overrides: list[str] | None = None,
    ) -> str:
        """Render image HTML template with optional layout configuration.

        Args:
            template: Template name (must be in VALID_TEMPLATES whitelist)
            context: Template variables
            layout_config: Pre-loaded LayoutConfig instance (takes priority)
            layout_preset: Preset name to load (e.g., "minimal_dark")
            layout_theme: Theme name to load (e.g., "socialbuilders")
            layout_overrides: CLI-style override strings (e.g., ["colors.primary=#ff0000"])

        Returns:
            Rendered HTML string

        Raises:
            ValueError: If template name is not in the whitelist
        """
        if template not in self.VALID_TEMPLATES:
            raise ValueError(
                f"Invalid template: {template}. " f"Valid templates: {', '.join(sorted(self.VALID_TEMPLATES))}"
            )

        # Prepare layout configuration
        layout_dict = self._get_layout_config(
            layout_config=layout_config,
            layout_preset=layout_preset,
            layout_theme=layout_theme,
            layout_overrides=layout_overrides,
            template_name=template,
        )

        # Merge layout into context
        merged_context = {**context}
        if layout_dict:
            merged_context["layout"] = layout_dict

        tmpl = self.env.get_template(f"{template}.html")
        return tmpl.render(**merged_context)

    def _get_layout_config(
        self,
        layout_config: LayoutConfig | None,
        layout_preset: str | None,
        layout_theme: str | None,
        layout_overrides: list[str] | None,
        template_name: str,
    ) -> dict | None:
        """Get layout configuration as dictionary."""
        # Import here to avoid circular imports
        from .layout_config import get_layout_for_template

        if layout_config is not None:
            # Use provided config directly
            config = layout_config
        elif layout_preset or layout_theme or layout_overrides:
            # Load from preset/theme/overrides
            config = get_layout_for_template(
                preset=layout_preset,
                theme=layout_theme,
                template_name=template_name,
                overrides=layout_overrides,
            )
        else:
            # No layout specified - use defaults
            return None

        return asdict(config)


def get_image_renderer() -> ImageRenderer:
    """Get image renderer instance."""
    return ImageRenderer()


# ─────────────────────────────────────────────────────────────
# 편의 함수
# ─────────────────────────────────────────────────────────────

_default_renderer: TemplateRenderer | None = None


def get_renderer() -> TemplateRenderer:
    """기본 TemplateRenderer 반환"""
    global _default_renderer
    if _default_renderer is None:
        _default_renderer = TemplateRenderer()
    return _default_renderer
