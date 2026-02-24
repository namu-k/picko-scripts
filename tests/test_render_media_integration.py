"""Integration tests for render_media pipeline."""

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.mark.integration
class TestRenderMediaIntegration:
    """Integration tests for full pipeline."""

    def test_full_pipeline_dry_run(self, tmp_path: Path):
        """Test full pipeline in dry-run mode (no actual rendering)."""
        from scripts.render_media import cli

        # Create input template
        input_file = tmp_path / "mm_test.md"
        input_file.write_text(
            """---
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
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["render", "--input", str(input_file)],
        )

        # Should load and parse successfully
        assert result.exit_code == 0
        assert "mm_test_001" in result.output

    def test_proposal_generation_from_input(self, tmp_path: Path):
        """Test proposal generation from parsed input."""
        from picko.multimedia_io import parse_multimedia_input
        from picko.proposal_generator import generate_proposal

        # Create input template
        input_file = tmp_path / "mm_quote.md"
        input_file.write_text(
            """---
id: mm_quote_001
account: socialbuilders
source_type: standalone
channels: [linkedin, twitter]
content_types: [image]
created: 2026-02-24
---

## 주제/컨셉
인용문 테스트

## 포함할 텍스트
실패는 성공의 어머니다
""",
            encoding="utf-8",
        )

        # Parse input
        input_data = parse_multimedia_input(input_file)

        # Generate proposal
        proposal = generate_proposal(input_data, account_config={}, references=[])

        # Verify proposal
        assert proposal.input_id == "mm_quote_001"
        assert proposal.content_type == "quote"
        assert proposal.template == "quote.html"
        assert "linkedin" in proposal.channels
        assert "twitter" in proposal.channels

    def test_html_template_rendering(self):
        """Test HTML template rendering with proposal data."""
        from picko.templates import get_image_renderer

        renderer = get_image_renderer()

        # Render quote template
        html = renderer.render_image(
            template="quote",
            context={
                "quote": "테스트 인용문",
                "author": "테스트 작성자",
                "background_color": "#1a1a2e",
            },
        )

        assert "테스트 인용문" in html
        assert "테스트 작성자" in html
        assert "<html" in html

    @pytest.mark.asyncio
    async def test_end_to_end_render(self, tmp_path: Path):
        """Test end-to-end HTML to PNG rendering."""
        from picko.html_renderer import render_html_to_png
        from picko.templates import get_image_renderer

        # Get HTML from template
        renderer = get_image_renderer()
        html = renderer.render_image(
            template="quote",
            context={
                "quote": "End-to-End 테스트",
                "author": "",
                "background_color": "#2d3436",
            },
        )

        # Render to PNG
        output_path = tmp_path / "e2e_test.png"
        result = await render_html_to_png(html, output_path, width=100, height=100)

        # Verify output
        assert result.exists()
        assert result.read_bytes()[:4] == b"\x89PNG"
