"""HTML to PNG rendering using Playwright."""

import asyncio
import io
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

from .logger import get_logger

logger = get_logger("html_renderer")

# Platform-specific image dimensions (width, height)
PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    # Square formats
    "instagram_feed": (1080, 1080),
    "instagram_square": (1080, 1080),
    "linkedin_square": (1200, 1200),
    "twitter_square": (1200, 1200),
    # Portrait formats
    "instagram_portrait": (1080, 1350),
    "instagram_story": (1080, 1920),
    "threads": (1080, 1350),
    # Landscape formats
    "linkedin": (1200, 627),
    "linkedin_landscape": (1200, 627),
    "twitter": (1200, 675),
    "twitter_landscape": (1200, 675),
    "newsletter": (1200, 630),
    "blog": (1200, 630),
    # Default
    "default": (1080, 1080),
}

# Channel aliases mapping
CHANNEL_ALIASES: dict[str, str] = {
    "instagram": "instagram_feed",
    "ig": "instagram_feed",
    "linkedin": "linkedin",
    "li": "linkedin",
    "twitter": "twitter",
    "x": "twitter",
    "threads": "threads",
    "newsletter": "newsletter",
    "blog": "blog",
}


def get_dimensions_for_channel(channel: str) -> tuple[int, int]:
    """Get image dimensions for a specific channel.

    Args:
        channel: Channel name (e.g., 'instagram', 'linkedin', 'twitter')

    Returns:
        Tuple of (width, height) for the channel
    """
    normalized = channel.lower().strip()
    platform_key = CHANNEL_ALIASES.get(normalized, normalized)
    return PLATFORM_DIMENSIONS.get(platform_key, PLATFORM_DIMENSIONS["default"])


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
    output_path = Path(output_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})

        # Set content
        await page.set_content(html, wait_until="networkidle")

        # Take screenshot
        screenshot_bytes = await page.screenshot(type="png")

        await browser.close()

    # Composite with background if provided
    if background_image and Path(background_image).exists():
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
    return asyncio.run(render_html_to_png(html, output_path, width, height, background_image))
