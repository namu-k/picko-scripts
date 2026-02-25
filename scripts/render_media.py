"""Render media CLI - image and video rendering pipeline."""

from pathlib import Path
from typing import Any

import click
import yaml

from picko.logger import setup_logger

logger = setup_logger("render_media")

# Default vault path
DEFAULT_VAULT = Path("mock_vault")


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
    vault = ctx.obj.get("vault", DEFAULT_VAULT)
    output = get_status(vault)
    click.echo(output)


@cli.command()
@click.option("--finals", is_flag=True, help="Review final renders")
@click.option("--id", "item_id", default=None, help="Specific item ID to review")
@click.pass_context
def review(ctx: click.Context, finals: bool, item_id: str | None):
    """Review pending proposals or renders."""
    vault = ctx.obj.get("vault", DEFAULT_VAULT)

    if finals:
        items = get_pending_finals(vault)
        review_mode = "결과물"
    else:
        items = get_pending_proposals(vault)
        review_mode = "제안"

    if not items:
        click.echo(f"📋 검토 대기 중인 {review_mode} 없음")
        return

    # Filter by item_id if specified
    if item_id:
        items = [i for i in items if i.get("id") == item_id]
        if not items:
            click.echo(f"📋 ID '{item_id}'에 해당하는 {review_mode} 없음")
            return

    # Interactive review loop
    for item in items:
        review_item(item)


@cli.command()
@click.option("--input", "input_path", type=Path, required=True, help="Input template path")
@click.option(
    "--layout",
    "layout_preset",
    default=None,
    help="Layout preset name (e.g., minimal_dark, minimal_light, social_gradient)",
)
@click.option("--theme", "layout_theme", default=None, help="Layout theme name (e.g., socialbuilders)")
@click.option("--override", "layout_overrides", multiple=True, help="Override key=value (e.g., colors.primary=#ff0000)")
@click.option("--output", "output_path", type=Path, default=None, help="Output HTML file path")
@click.option("--output-png", "png_path", type=Path, default=None, help="Output PNG file path")
@click.option(
    "--channel", default="instagram", help="Channel for PNG dimensions (instagram, twitter, linkedin, threads)"
)
@click.pass_context
def render(
    ctx: click.Context,
    input_path: Path,
    layout_preset: str | None,
    layout_theme: str | None,
    layout_overrides: tuple[str, ...],
    output_path: Path | None,
    png_path: Path | None,
    channel: str,
):
    """Render from input template with optional layout configuration."""
    from picko.multimedia_io import parse_multimedia_input
    from picko.templates import ImageRenderer

    try:
        input_data = parse_multimedia_input(input_path)
        click.echo(f"📝 입력 로드 완료: {input_data.id}")
        click.echo(f"   계정: {input_data.account}")
        click.echo(f"   채널: {', '.join(input_data.channels)}")
        click.echo(f"   주제: {input_data.concept}")

        # Display layout configuration
        if layout_preset:
            click.echo(f"   레이아웃 프리셋: {layout_preset}")
        if layout_theme:
            click.echo(f"   레이아웃 테마: {layout_theme}")
        if layout_overrides:
            click.echo(f"   레이아웃 오버라이드: {', '.join(layout_overrides)}")

        # Use quote template as default for short overlay text
        # For longer content, use card template
        template = "quote" if input_data.overlay_text and len(input_data.overlay_text) < 100 else "card"
        click.echo(f"   템플릿: {template}")

        # Build context from input
        context = {
            "quote": input_data.overlay_text or input_data.concept,
            "title": input_data.concept,
            "width": 1080,
            "height": 1080,
            "channels": input_data.channels,
        }

        # Render with layout support
        renderer = ImageRenderer()
        html = renderer.render_image(
            template=template,
            context=context,
            layout_preset=layout_preset,
            layout_theme=layout_theme,
            layout_overrides=list(layout_overrides) if layout_overrides else None,
        )

        # Output handling
        if output_path:
            output_path.write_text(html, encoding="utf-8")
            click.echo(f"\n✅ HTML 렌더링 완료: {output_path}")

        # PNG rendering
        if png_path:
            try:
                from picko.html_renderer import get_dimensions_for_channel, render_html_to_png_sync
            except ImportError as e:
                click.echo(
                    "❌ PNG 렌더링을 위해 playwright 설치 필요: pip install playwright && playwright install", err=True
                )
                raise SystemExit(1) from e

            width, height = get_dimensions_for_channel(channel)
            click.echo(f"   PNG 채널: {channel} ({width}x{height})")
            render_html_to_png_sync(html=html, output_path=png_path, width=width, height=height)
            click.echo(f"✅ PNG 렌더링 완료: {png_path}")

        if not output_path and not png_path:
            click.echo("\n✅ 렌더링 완료 (출력 생략)")

    except FileNotFoundError:
        click.echo(f"❌ 파일을 찾을 수 없습니다: {input_path}", err=True)
        raise SystemExit(1)
    except PermissionError:
        click.echo(f"❌ 파일 읽기 권한이 없습니다: {input_path}", err=True)
        raise SystemExit(1)
    except UnicodeDecodeError as e:
        click.echo(f"❌ 파일 인코딩 오류 (UTF-8 필요): {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"❌ 오류: {e}", err=True)
        raise SystemExit(1)


def get_status(vault_path: Path | None = None) -> str:
    """Get pipeline status summary.

    Args:
        vault_path: Vault root directory (defaults to DEFAULT_VAULT)

    Returns:
        Formatted status string
    """
    vault = vault_path or DEFAULT_VAULT
    multimedia_dir = vault / "Inbox" / "Multimedia"
    images_dir = vault / "Assets" / "Images"

    items = []

    # Scan multimedia inputs
    if multimedia_dir.exists():
        for f in multimedia_dir.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1])
                        status_val = meta.get("status", "draft")
                        channels = meta.get("channels", [])
                        items.append(
                            {
                                "id": meta.get("id", f.stem),
                                "status": status_val,
                                "channels": ", ".join(channels) if channels else "-",
                            }
                        )
            except (yaml.YAMLError, UnicodeDecodeError, IndexError):
                continue

    # Scan rendered images metadata
    if images_dir.exists():
        for meta_file in images_dir.rglob("meta_*.md"):
            try:
                content = meta_file.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1])
                        status_val = meta.get("status", "unknown")
                        if status_val in ["rendered", "pending_final_review"]:
                            items.append(
                                {
                                    "id": meta.get("id", meta_file.stem),
                                    "status": status_val,
                                    "channels": meta.get("channel", "-"),
                                }
                            )
            except (yaml.YAMLError, UnicodeDecodeError, IndexError):
                continue

    if not items:
        return """📊 이미지 렌더링 상태
────────────────────────────────────────
ID                    STATUS          CHANNELS
────────────────────────────────────────
대기 중인 항목 없음
────────────────────────────────────────"""

    # Format output
    lines = ["📊 이미지 렌더링 상태", "─" * 50]
    lines.append(f"{'ID':<20} {'STATUS':<16} {'CHANNELS'}")
    lines.append("─" * 50)

    for item in items:
        lines.append(f"{item['id']:<20} {item['status']:<16} {item['channels']}")

    lines.append("─" * 50)

    # Count by status
    status_counts: dict[str, int] = {}
    for item in items:
        s = item["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    lines.append(f"총 {len(items)}개 항목")
    for s, count in status_counts.items():
        lines.append(f"  - {s}: {count}개")

    return "\n".join(lines)


def get_pending_proposals(vault_path: Path | None = None) -> list[dict[str, Any]]:
    """Get pending proposals for review.

    Args:
        vault_path: Vault root directory (defaults to DEFAULT_VAULT)

    Returns:
        List of proposal dictionaries
    """
    vault = vault_path or DEFAULT_VAULT
    multimedia_dir = vault / "Inbox" / "Multimedia"

    proposals = []

    if not multimedia_dir.exists():
        return proposals

    for f in multimedia_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    status_val = meta.get("status", "draft")

                    # Return items that are proposed or ready for review
                    if status_val in ["proposed", "pending_review"]:
                        proposals.append(
                            {
                                "id": meta.get("id", f.stem),
                                "status": status_val,
                                "account": meta.get("account", "unknown"),
                                "channels": meta.get("channels", []),
                                "content_types": meta.get("content_types", ["image"]),
                                "file_path": str(f),
                            }
                        )
        except (yaml.YAMLError, UnicodeDecodeError, IndexError):
            continue

    return proposals


def get_pending_finals(vault_path: Path | None = None) -> list[dict[str, Any]]:
    """Get pending final renders for review.

    Args:
        vault_path: Vault root directory (defaults to DEFAULT_VAULT)

    Returns:
        List of final render dictionaries
    """
    vault = vault_path or DEFAULT_VAULT
    images_dir = vault / "Assets" / "Images"

    finals = []

    if not images_dir.exists():
        return finals

    for meta_file in images_dir.rglob("meta_*.md"):
        try:
            content = meta_file.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    status_val = meta.get("status", "unknown")

                    if status_val in ["rendered", "pending_final_review"]:
                        # Find the corresponding image file
                        img_id = meta.get("id", "")
                        parent_dir = meta_file.parent
                        img_files = list(parent_dir.glob(f"img_*_{img_id}.png"))
                        img_path = str(img_files[0]) if img_files else "Not found"

                        finals.append(
                            {
                                "id": img_id,
                                "status": status_val,
                                "channel": meta.get("channel", "unknown"),
                                "account": meta.get("account", "unknown"),
                                "image_path": img_path,
                                "meta_path": str(meta_file),
                            }
                        )
        except (yaml.YAMLError, UnicodeDecodeError, IndexError):
            continue

    return finals


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
