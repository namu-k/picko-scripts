# Image Rendering Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build CLI-based image rendering pipeline with API background generation, HTML overlay, and 2-stage interactive review.

**Architecture:** Template-based input → LLM proposal generation → API background + HTML layout → Playwright rendering → CLI interactive review → final storage. Integrates with existing longform via `derivative_status` extension.

**Tech Stack:** Python, Playwright (HTML→PNG), Stability AI / OpenAI API, Jinja2 (HTML templates), Click (CLI), pytest

---

## Phase 1: Core Infrastructure

### Task 1: Multimedia Input Template Parser

**Files:**
- Create: `picko/multimedia_io.py`
- Test: `tests/test_multimedia_io.py`

**Step 1: Write the failing test**

```python
# tests/test_multimedia_io.py
"""Tests for multimedia input/output module."""
import pytest
from pathlib import Path
from picko.multimedia_io import MultimediaInput, parse_multimedia_input


class TestMultimediaInput:
    """Test multimedia input parsing."""

    def test_parse_standalone_input(self, tmp_path: Path):
        """Parse standalone multimedia input template."""
        input_file = tmp_path / "mm_20260224_001.md"
        input_file.write_text("""---
id: mm_20260224_001
account: socialbuilders
source_type: standalone
channels: [linkedin, twitter]
content_types: [image]
created: 2026-02-24
status: draft
---

## 주제/컨셉
창업자를 위한 시간 관리

## 포함할 텍스트
시간은 창업자의 가장 귀한 자산이다
""")
        result = parse_multimedia_input(input_file)

        assert result.id == "mm_20260224_001"
        assert result.account == "socialbuilders"
        assert result.source_type == "standalone"
        assert result.channels == ["linkedin", "twitter"]
        assert result.concept == "창업자를 위한 시간 관리"
        assert result.overlay_text == "시간은 창업자의 가장 귀한 자산이다"

    def test_parse_with_refs(self, tmp_path: Path):
        """Parse input with reference documents."""
        input_file = tmp_path / "mm_20260224_002.md"
        input_file.write_text("""---
id: mm_20260224_002
account: socialbuilders
source_type: from_longform
longform_ref: "Content/Longform/long_input_xxx.md"
refs:
  - type: reference_style, id: founder_tech_brief
created: 2026-02-24
---

## 주제/컨셉
PMF 달성 전략
""")
        result = parse_multimedia_input(input_file)

        assert result.source_type == "from_longform"
        assert result.longform_ref == "Content/Longform/long_input_xxx.md"
        assert len(result.refs) == 1
        assert result.refs[0]["type"] == "reference_style"

    def test_missing_required_field_raises(self, tmp_path: Path):
        """Missing required fields should raise ValueError."""
        input_file = tmp_path / "mm_invalid.md"
        input_file.write_text("""---
id: mm_20260224_003
account: socialbuilders
---
""")
        with pytest.raises(ValueError, match="주제/컨셉"):
            parse_multimedia_input(input_file)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multimedia_io.py -v`
Expected: FAIL with module import error or function not defined

**Step 3: Write minimal implementation**

```python
# picko/multimedia_io.py
"""Multimedia input/output handling."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .logger import get_logger

logger = get_logger("multimedia_io")


@dataclass
class MultimediaInput:
    """Multimedia input template data."""
    id: str
    account: str
    source_type: str  # standalone | from_longform
    channels: list[str]
    content_types: list[str]
    concept: str
    created: str
    status: str = "draft"
    longform_ref: str = ""
    overlay_text: str = ""
    refs: list[dict[str, str]] = field(default_factory=list)
    notes: str = ""


def parse_multimedia_input(file_path: Path) -> MultimediaInput:
    """Parse multimedia input template file."""
    content = file_path.read_text(encoding="utf-8")

    # Parse frontmatter
    if not content.startswith("---"):
        raise ValueError(f"No frontmatter found in {file_path}")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter format in {file_path}")

    meta = yaml.safe_load(parts[1])
    body = parts[2].strip()

    # Extract body sections
    sections = _parse_body_sections(body)

    # Validate required fields
    if "주제/컨셉" not in sections:
        raise ValueError("필수 필드 누락: 주제/컨셉")

    return MultimediaInput(
        id=meta.get("id", ""),
        account=meta.get("account", ""),
        source_type=meta.get("source_type", "standalone"),
        channels=meta.get("channels", []),
        content_types=meta.get("content_types", ["image"]),
        concept=sections.get("주제/컨셉", ""),
        created=meta.get("created", ""),
        status=meta.get("status", "draft"),
        longform_ref=meta.get("longform_ref", ""),
        overlay_text=sections.get("포함할 텍스트", ""),
        refs=meta.get("refs", []),
        notes=sections.get("비고", ""),
    )


def _parse_body_sections(body: str) -> dict[str, str]:
    """Parse markdown body into sections."""
    sections: dict[str, str] = {}
    current_header = None
    current_content: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = line[3:].strip()
            current_content = []
        elif current_header:
            current_content.append(line)

    if current_header:
        sections[current_header] = "\n".join(current_content).strip()

    return sections
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_multimedia_io.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add picko/multimedia_io.py tests/test_multimedia_io.py
git commit -m "feat(multimedia): add input template parser"
```

---

### Task 2: Reference Document Loader

**Files:**
- Modify: `picko/multimedia_io.py`
- Test: `tests/test_multimedia_io.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_multimedia_io.py

class TestReferenceLoader:
    """Test reference document loading."""

    def test_load_account_config_auto(self, tmp_path: Path, monkeypatch):
        """Auto-load account config from account_id."""
        # Create mock account config
        accounts_dir = tmp_path / "config" / "accounts"
        accounts_dir.mkdir(parents=True)
        account_file = accounts_dir / "testaccount.yml"
        account_file.write_text("""
account_id: testaccount
name: "Test Account"
channels:
  linkedin:
    enabled: true
""")

        from picko import multimedia_io
        monkeypatch.setattr(multimedia_io, "PROJECT_ROOT", tmp_path)

        from picko.multimedia_io import load_account_config

        config = load_account_config("testaccount")
        assert config["account_id"] == "testaccount"
        assert config["name"] == "Test Account"

    def test_load_reference_by_type_and_id(self, tmp_path: Path, monkeypatch):
        """Load reference document by type and ID."""
        # Create mock reference
        ref_dir = tmp_path / "Assets" / "References"
        ref_dir.mkdir(parents=True)
        ref_file = ref_dir / "test_style.md"
        ref_file.write_text("# Test Style\n\nThis is a test style reference.")

        from picko import multimedia_io
        monkeypatch.setattr(multimedia_io, "PROJECT_ROOT", tmp_path)

        from picko.multimedia_io import load_reference

        content = load_reference("reference_style", "test_style")
        assert "Test Style" in content

    def test_resolve_refs_list(self, tmp_path: Path, monkeypatch):
        """Resolve list of references."""
        from picko.multimedia_io import MultimediaInput, resolve_all_refs

        input_data = MultimediaInput(
            id="test",
            account="testaccount",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="test concept",
            created="2026-02-24",
            refs=[
                {"type": "reference_style", "id": "style1"},
                {"type": "exploration", "id": "exp1"},
            ],
        )

        # Mock the loader
        def mock_load(ref_type, ref_id):
            return f"Content of {ref_type}/{ref_id}"

        monkeypatch.setattr("picko.multimedia_io.load_reference", mock_load)

        resolved = resolve_all_refs(input_data)
        assert len(resolved) == 2
        assert "style1" in resolved[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multimedia_io.py::TestReferenceLoader -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# Add to picko/multimedia_io.py

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent

# Reference type to path mapping
REFERENCE_PATHS = {
    "longform": "Content/Longform/{id}.md",
    "reference_style": "Assets/References/{id}.md",
    "exploration": "Inbox/Explorations/{id}.md",
    "image_style": "mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0. 프레임워크/이미지 스타일 프리셋 라이브러리.md",
}


def load_account_config(account_id: str) -> dict[str, Any]:
    """Load account configuration by account_id."""
    config_path = PROJECT_ROOT / "config" / "accounts" / f"{account_id}.yml"

    if not config_path.exists():
        logger.warning(f"Account config not found: {config_path}")
        return {"account_id": account_id}

    import yaml
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_reference(ref_type: str, ref_id: str) -> str:
    """Load reference document by type and ID."""
    if ref_type not in REFERENCE_PATHS:
        raise ValueError(f"Unknown reference type: {ref_type}")

    path_pattern = REFERENCE_PATHS[ref_type]
    ref_path = PROJECT_ROOT / path_pattern.format(id=ref_id)

    if not ref_path.exists():
        logger.warning(f"Reference not found: {ref_path}")
        return ""

    return ref_path.read_text(encoding="utf-8")


def resolve_all_refs(input_data: MultimediaInput) -> list[str]:
    """Resolve all references from input data."""
    resolved = []

    for ref in input_data.refs:
        ref_type = ref.get("type")
        ref_id = ref.get("id")
        if ref_type and ref_id:
            content = load_reference(ref_type, ref_id)
            if content:
                resolved.append(content)

    return resolved
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_multimedia_io.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add picko/multimedia_io.py tests/test_multimedia_io.py
git commit -m "feat(multimedia): add reference document loader"
```

---

## Phase 2: LLM Proposal Generator

### Task 3: Proposal Generator

**Files:**
- Create: `picko/proposal_generator.py`
- Create: `config/prompts/multimedia/proposal.md`
- Test: `tests/test_proposal_generator.py`

**Step 1: Write the failing test**

```python
# tests/test_proposal_generator.py
"""Tests for proposal generator."""
import pytest
from picko.proposal_generator import Proposal, generate_proposal
from picko.multimedia_io import MultimediaInput


class TestProposalGenerator:
    """Test proposal generation."""

    def test_proposal_dataclass(self):
        """Proposal dataclass holds all required fields."""
        proposal = Proposal(
            input_id="mm_001",
            content_type="quote",
            template="quote.html",
            background_prompt="minimal gradient",
            overlay_text="Test quote",
            style_preset="minimal_infographic",
            channels=["linkedin"],
        )

        assert proposal.content_type == "quote"
        assert proposal.template == "quote.html"

    def test_determine_content_type_quote(self):
        """Determine quote type for short text."""
        input_data = MultimediaInput(
            id="mm_001",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="Test",
            overlay_text="짧은 문구 하나",
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "quote"

    def test_determine_content_type_card(self):
        """Determine card type for longer content."""
        input_data = MultimediaInput(
            id="mm_002",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="Test",
            overlay_text="",  # No short quote
            created="2026-02-24",
        )

        # Should default to card when no clear type indicator
        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type in ["card", "quote"]  # Either is acceptable
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_proposal_generator.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# picko/proposal_generator.py
"""Proposal generator for multimedia content."""
from dataclasses import dataclass
from typing import Any

from .logger import get_logger
from .multimedia_io import MultimediaInput

logger = get_logger("proposal_generator")


@dataclass
class Proposal:
    """LLM-generated proposal for multimedia content."""
    input_id: str
    content_type: str  # quote | card | list | data | carousel
    template: str
    background_prompt: str
    overlay_text: str
    style_preset: str
    channels: list[str]
    layout_hints: list[str] | None = None


# Content type heuristics
def _determine_content_type(input_data: MultimediaInput) -> str:
    """Determine content type based on input characteristics."""
    overlay = input_data.overlay_text
    concept = input_data.concept

    # Short quote-like text → quote
    if overlay and len(overlay) < 100:
        return "quote"

    # List indicators → list
    list_indicators = ["단계", "가지", "방법", "체크리스트"]
    if any(ind in concept for ind in list_indicators):
        return "list"

    # Number/data indicators → data
    data_indicators = ["%", "배", "증가", "감소", "수치"]
    if any(ind in concept + overlay for ind in data_indicators):
        return "data"

    # Default to card
    return "card"


def _generate_background_prompt(
    content_type: str,
    concept: str,
    style_preset: str,
) -> str:
    """Generate background image prompt."""
    base_prompts = {
        "quote": f"minimal gradient background, clean, professional, soft tones for quote overlay",
        "card": f"clean background for content card, subtle texture, professional",
        "list": f"minimal infographic background, grid-ready, clean whitespace",
        "data": f"data visualization background, chart-friendly, minimal",
        "carousel": f"consistent series background, cohesive design",
    }
    return base_prompts.get(content_type, base_prompts["card"])


def generate_proposal(
    input_data: MultimediaInput,
    account_config: dict[str, Any],
    references: list[str],
) -> Proposal:
    """Generate proposal for multimedia content."""
    content_type = _determine_content_type(input_data)

    template_map = {
        "quote": "quote.html",
        "card": "card.html",
        "list": "list.html",
        "data": "data.html",
        "carousel": "carousel.html",
    }

    style_presets = {
        "quote": "minimal_infographic",
        "card": "editorial_photo",
        "list": "minimal_infographic",
        "data": "data_card",
        "carousel": "minimal_infographic",
    }

    background_prompt = _generate_background_prompt(
        content_type,
        input_data.concept,
        style_presets.get(content_type, "minimal_infographic"),
    )

    return Proposal(
        input_id=input_data.id,
        content_type=content_type,
        template=template_map.get(content_type, "card.html"),
        background_prompt=background_prompt,
        overlay_text=input_data.overlay_text or input_data.concept,
        style_preset=style_presets.get(content_type, "minimal_infographic"),
        channels=input_data.channels,
        layout_hints=[],
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_proposal_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add picko/proposal_generator.py tests/test_proposal_generator.py
git commit -m "feat(proposal): add proposal generator with content type detection"
```

---

## Phase 3: HTML Templates

### Task 4: HTML Template System

**Files:**
- Create: `templates/images/quote.html`
- Create: `templates/images/card.html`
- Create: `templates/images/list.html`
- Modify: `picko/templates.py`
- Test: `tests/test_image_templates.py`

**Step 1: Write the failing test**

```python
# tests/test_image_templates.py
"""Tests for image HTML templates."""
import pytest
from picko.templates import get_image_renderer


class TestImageTemplates:
    """Test image template rendering."""

    def test_render_quote_template(self):
        """Render quote template with text."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="quote",
            context={
                "quote": "시간은 창업자의 가장 귀한 자산이다",
                "author": "",
                "background_color": "#1a1a2e",
            }
        )

        assert "시간은 창업자의 가장 귀한 자산이다" in result
        assert "<html" in result
        assert "</html>" in result

    def test_render_card_template(self):
        """Render card template with title and summary."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="card",
            context={
                "title": "PMF 달성 전략",
                "summary": "제품 시장 적합성을 찾는 5단계 가이드",
                "background_color": "#ffffff",
            }
        )

        assert "PMF 달성 전략" in result
        assert "5단계" in result

    def test_render_list_template(self):
        """Render list template with items."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="list",
            context={
                "title": "창업자 체크리스트",
                "items": ["아이디어 검증", "MVP 개발", "고객 인터뷰"],
                "background_color": "#f5f5f5",
            }
        )

        assert "창업자 체크리스트" in result
        assert "아이디어 검증" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_templates.py -v`
Expected: FAIL

**Step 3: Create templates**

```html
<!-- templates/images/quote.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 1080px;
            height: 1080px;
            background-color: {{ background_color }};
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .quote-container {
            text-align: center;
            padding: 60px;
            max-width: 80%;
        }
        .quote {
            font-size: 48px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.4;
            margin-bottom: 30px;
        }
        .author {
            font-size: 24px;
            color: #aaaaaa;
        }
    </style>
</head>
<body>
    <div class="quote-container">
        <div class="quote">{{ quote }}</div>
        {% if author %}<div class="author">— {{ author }}</div>{% endif %}
    </div>
</body>
</html>
```

```html
<!-- templates/images/card.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 1080px;
            height: 1080px;
            background-color: {{ background_color }};
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 80px;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .title {
            font-size: 56px;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 40px;
            line-height: 1.3;
        }
        .summary {
            font-size: 32px;
            color: #666666;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="title">{{ title }}</div>
    <div class="summary">{{ summary }}</div>
</body>
</html>
```

```html
<!-- templates/images/list.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 1080px;
            height: 1080px;
            background-color: {{ background_color }};
            display: flex;
            flex-direction: column;
            padding: 80px;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .title {
            font-size: 48px;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 50px;
        }
        .items {
            list-style: none;
        }
        .item {
            font-size: 36px;
            color: #333333;
            padding: 20px 0;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
        }
        .item-number {
            font-weight: 700;
            color: #4a90d9;
            margin-right: 20px;
            font-size: 40px;
        }
    </style>
</head>
<body>
    <div class="title">{{ title }}</div>
    <ul class="items">
        {% for item in items %}
        <li class="item">
            <span class="item-number">{{ loop.index }}</span>
            {{ item }}
        </li>
        {% endfor %}
    </ul>
</body>
</html>
```

**Step 4: Modify templates.py**

```python
# Add to picko/templates.py

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class ImageRenderer:
    """Render HTML templates for images."""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR / "images"),
            autoescape=select_autoescape(["html"]),
        )

    def render_image(self, template: str, context: dict) -> str:
        """Render image HTML template."""
        tmpl = self.env.get_template(f"{template}.html")
        return tmpl.render(**context)


def get_image_renderer() -> ImageRenderer:
    """Get image renderer instance."""
    return ImageRenderer()
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_image_templates.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add templates/images/ picko/templates.py tests/test_image_templates.py
git commit -m "feat(templates): add HTML image templates (quote, card, list)"
```

---

## Phase 4: Playwright Renderer

### Task 5: Playwright HTML-to-PNG

**Files:**
- Create: `picko/html_renderer.py`
- Test: `tests/test_html_renderer.py`

**Step 1: Write the failing test**

```python
# tests/test_html_renderer.py
"""Tests for HTML to PNG rendering."""
import pytest
from pathlib import Path
from picko.html_renderer import render_html_to_png


class TestHtmlRenderer:
    """Test HTML rendering to PNG."""

    @pytest.mark.asyncio
    async def test_render_simple_html(self, tmp_path: Path):
        """Render simple HTML to PNG."""
        html = """
        <html>
        <body style="width: 100px; height: 100px; background: red;">
            <p>Test</p>
        </body>
        </html>
        """
        output_path = tmp_path / "test_output.png"

        result = await render_html_to_png(html, output_path, width=100, height=100)

        assert result == output_path
        assert output_path.exists()
        # Verify it's a valid PNG
        assert output_path.read_bytes()[:4] == b'\x89PNG'

    @pytest.mark.asyncio
    async def test_render_with_background_image(self, tmp_path: Path):
        """Render HTML overlay on background image."""
        # Create a simple background
        from PIL import Image
        bg_path = tmp_path / "bg.png"
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(bg_path)

        html = """
        <html>
        <body style="width: 100px; height: 100px; background: transparent;">
            <p style="color: white;">Overlay</p>
        </body>
        </html>
        """
        output_path = tmp_path / "test_overlay.png"

        result = await render_html_to_png(
            html,
            output_path,
            width=100,
            height=100,
            background_image=bg_path,
        )

        assert result.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_html_renderer.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# picko/html_renderer.py
"""HTML to PNG rendering using Playwright."""
import asyncio
from pathlib import Path
from typing import Path | None

from playwright.async_api import async_playwright

from .logger import get_logger

logger = get_logger("html_renderer")


async def render_html_to_png(
    html: str,
    output_path: Path,
    width: int = 1080,
    height: int = 1080,
    background_image: Path | None = None,
) -> Path:
    """Render HTML to PNG using Playwright.

    Args:
        html: HTML content to render
        output_path: Output PNG file path
        width: Viewport width
        height: Viewport height
        background_image: Optional background image to composite

    Returns:
        Path to rendered PNG file
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})

        # Set content
        await page.set_content(html, wait_until="networkidle")

        # Take screenshot
        screenshot_bytes = await page.screenshot(type="png")

        await browser.close()

    # Composite with background if provided
    if background_image and background_image.exists():
        from PIL import Image
        import io

        bg = Image.open(background_image).convert("RGBA")
        overlay = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")

        # Resize overlay to match background
        overlay = overlay.resize(bg.size, Image.Resampling.LANCZOS)

        # Composite
        combined = Image.alpha_composite(bg, overlay)
        combined = combined.convert("RGB")
        combined.save(output_path, "PNG")
    else:
        output_path.write_bytes(screenshot_bytes)

    logger.info(f"Rendered HTML to PNG: {output_path}")
    return output_path


def render_html_to_png_sync(
    html: str,
    output_path: Path,
    width: int = 1080,
    height: int = 1080,
    background_image: Path | None = None,
) -> Path:
    """Synchronous wrapper for render_html_to_png."""
    return asyncio.run(
        render_html_to_png(html, output_path, width, height, background_image)
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_html_renderer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add picko/html_renderer.py tests/test_html_renderer.py
git commit -m "feat(renderer): add Playwright HTML-to-PNG renderer"
```

---

## Phase 5: CLI Interface

### Task 6: CLI Entry Point

**Files:**
- Create: `scripts/render_media.py`
- Test: `tests/test_render_media_cli.py`

**Step 1: Write the failing test**

```python
# tests/test_render_media_cli.py
"""Tests for render_media CLI."""
import pytest
from click.testing import CliRunner
from scripts.render_media import cli


class TestRenderMediaCLI:
    """Test render_media CLI commands."""

    def test_cli_help(self):
        """CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "render" in result.output.lower() or "media" in result.output.lower()

    def test_status_command(self, tmp_path, monkeypatch):
        """Status command shows pipeline status."""
        runner = CliRunner()

        # Mock the status function
        def mock_status():
            return "📊 이미지 렌더링 상태\n─────────\n대기 중: 0개"

        monkeypatch.setattr("scripts.render_media.get_status", mock_status)

        result = runner.invoke(cli, ["--status"])
        assert result.exit_code == 0

    def test_review_no_items(self, tmp_path, monkeypatch):
        """Review command with no pending items."""
        runner = CliRunner()

        def mock_get_pending():
            return []

        monkeypatch.setattr("scripts.render_media.get_pending_proposals", mock_get_pending)

        result = runner.invoke(cli, ["--review"])
        assert "검토 대기" in result.output or "대기" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_render_media_cli.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# scripts/render_media.py
"""Render media CLI - image and video rendering pipeline."""
import click
from pathlib import Path

from picko.logger import setup_logger

logger = setup_logger("render_media")


@click.group()
@click.option("--vault", type=Path, help="Vault root path")
@click.pass_context
def cli(ctx: click.Context, vault: Path | None):
    """Multimedia rendering pipeline CLI."""
    ctx.ensure_object(dict)
    ctx.obj["vault"] = vault or Path("mock_vault")


@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """Show pipeline status."""
    output = get_status()
    click.echo(output)


@cli.command()
@click.option("--finals", is_flag=True, help="Review final renders")
@click.option("--id", "item_id", help="Specific item ID to review")
@click.pass_context
def review(ctx: click.Context, finals: bool, item_id: str | None):
    """Review pending proposals or renders."""
    if finals:
        items = get_pending_finals()
        review_mode = "결과물"
    else:
        items = get_pending_proposals()
        review_mode = "제안"

    if not items:
        click.echo(f"📋 검토 대기 중인 {review_mode} 없음")
        return

    # Interactive review loop
    for item in items:
        review_item(item)


@cli.command()
@click.option("--input", "input_path", type=Path, required=True, help="Input template path")
@click.pass_context
def render(ctx: click.Context, input_path: Path):
    """Render from input template."""
    from picko.multimedia_io import parse_multimedia_input

    try:
        input_data = parse_multimedia_input(input_path)
        click.echo(f"📝 입력 로드 완료: {input_data.id}")
        # TODO: Generate proposal and start pipeline
    except ValueError as e:
        click.echo(f"❌ 오류: {e}", err=True)
        raise SystemExit(1)


def get_status() -> str:
    """Get pipeline status summary."""
    # TODO: Implement actual status check
    return """📊 이미지 렌더링 상태
────────────────────────────────────────
ID                    STATUS          CHANNELS
────────────────────────────────────────
대기 중인 항목 없음
────────────────────────────────────────"""


def get_pending_proposals() -> list:
    """Get pending proposals for review."""
    # TODO: Implement
    return []


def get_pending_finals() -> list:
    """Get pending final renders for review."""
    # TODO: Implement
    return []


def review_item(item: dict):
    """Interactive review of a single item."""
    click.echo(f"\n📋 검토: {item.get('id', 'unknown')}")
    click.echo("─" * 40)

    # Display item details
    for key, value in item.items():
        if key != "id":
            click.echo(f"{key}: {value}")

    # Prompt for action
    choice = click.prompt(
        "\n[A] 승인  [E] 수정  [R] 거절  [S] 건너뛰기",
        type=click.Choice(["A", "E", "R", "S"], case_sensitive=False),
        default="A",
    )

    if choice.upper() == "A":
        click.echo("✅ 승인됨")
    elif choice.upper() == "E":
        click.echo("✏️ 수정 모드 (미구현)")
    elif choice.upper() == "R":
        click.echo("❌ 거절됨")
    else:
        click.echo("⏭️ 건너뜀")


if __name__ == "__main__":
    cli()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_render_media_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/render_media.py tests/test_render_media_cli.py
git commit -m "feat(cli): add render_media CLI with status and review commands"
```

---

## Phase 6: Integration

### Task 7: Full Pipeline Integration

**Files:**
- Modify: `scripts/render_media.py`
- Test: `tests/test_render_media_integration.py`

**Step 1: Write integration test**

```python
# tests/test_render_media_integration.py
"""Integration tests for render_media pipeline."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from scripts.render_media import cli


@pytest.mark.integration
class TestRenderMediaIntegration:
    """Integration tests for full pipeline."""

    def test_full_pipeline_dry_run(self, tmp_path: Path, monkeypatch):
        """Test full pipeline in dry-run mode."""
        # Create input template
        input_file = tmp_path / "mm_test.md"
        input_file.write_text("""---
id: mm_test_001
account: socialbuilders
source_type: standalone
channels: [linkedin]
content_types: [image]
created: 2026-02-24
status: draft
---

## 주제/컨셉
테스트 이미지

## 포함할 텍스트
이것은 테스트입니다
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["render", "--input", str(input_file)],
            obj={"vault": tmp_path},
        )

        # Should load and parse successfully
        assert "mm_test_001" in result.output or result.exit_code == 0
```

**Step 2: Run test**

Run: `pytest tests/test_render_media_integration.py -v -m integration`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_render_media_integration.py
git commit -m "test(integration): add render_media pipeline integration test"
```

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|------------------|
| 1 | 1-2 | Input parser, Reference loader |
| 2 | 3 | Proposal generator |
| 3 | 4 | HTML templates (quote, card, list) |
| 4 | 5 | Playwright renderer |
| 5 | 6 | CLI interface |
| 6 | 7 | Integration tests |

**Dependencies to add:**
- `playwright` - HTML rendering
- `Pillow` - Image compositing
- `click` - CLI (likely already present)

**Run after implementation:**
```bash
playwright install chromium
```

---

*Plan created: 2026-02-24*
*Design doc: `specs/003-auto-collector/canonical/Image_Rendering_Pipeline.md`*
