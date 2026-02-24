"""Tests for HTML to PNG rendering."""

from pathlib import Path

import pytest

from picko.html_renderer import render_html_to_png, render_html_to_png_sync


class TestHtmlRenderer:
    """Test HTML rendering to PNG."""

    @pytest.mark.asyncio
    async def test_render_simple_html(self, tmp_path: Path):
        """Render simple HTML to PNG."""
        html = """
        <html>
        <head><style>
            body { width: 100px; height: 100px; background: red; margin: 0; }
        </style></head>
        <body>
            <p>Test</p>
        </body>
        </html>
        """
        output_path = tmp_path / "test_output.png"

        result = await render_html_to_png(html, output_path, width=100, height=100)

        assert result == output_path
        assert output_path.exists()
        # Verify it's a valid PNG (PNG magic bytes)
        assert output_path.read_bytes()[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_render_with_background_image(self, tmp_path: Path):
        """Render HTML overlay on background image."""
        # Create a simple background
        from PIL import Image

        bg_path = tmp_path / "bg.png"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(bg_path)

        html = """
        <html>
        <head><style>
            body { width: 100px; height: 100px; background: transparent; margin: 0; }
            p { color: white; }
        </style></head>
        <body>
            <p>Overlay</p>
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

    def test_sync_wrapper(self, tmp_path: Path):
        """Test synchronous wrapper function."""
        html = """
        <html>
        <head><style>
            body { width: 50px; height: 50px; background: green; margin: 0; }
        </style></head>
        <body><p>Sync</p></body>
        </html>
        """
        output_path = tmp_path / "test_sync.png"

        result = render_html_to_png_sync(html, output_path, width=50, height=50)

        assert result.exists()
        assert result.read_bytes()[:4] == b"\x89PNG"
