"""Render media CLI - image and video rendering pipeline."""

from pathlib import Path

import click

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
@click.option("--id", "item_id", default=None, help="Specific item ID to review")
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
        click.echo(f"   계정: {input_data.account}")
        click.echo(f"   채널: {', '.join(input_data.channels)}")
        click.echo(f"   주제: {input_data.concept}")
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
