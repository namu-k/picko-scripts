# picko/orchestrator/default_actions.py
"""기본 액션 등록 — 기존 스크립트를 액션으로 래핑"""

from __future__ import annotations

from picko.logger import get_logger
from picko.orchestrator.actions import ActionRegistry, ActionResult

logger = get_logger("orchestrator.default_actions")


def register_default_actions(registry: ActionRegistry):
    """기본 Picko 액션을 레지스트리에 등록"""
    registry.register("collector.run", _run_collector)
    registry.register("generator.run", _run_generator)
    registry.register("renderer.run", _run_renderer)
    registry.register("publisher.run", _run_publisher)


def _run_collector(account: str = "socialbuilders", dry_run: bool = False, **kwargs) -> ActionResult:
    """scripts/daily_collector.py의 DailyCollector를 래핑"""
    from scripts.daily_collector import DailyCollector

    try:
        collector = DailyCollector(account_id=account, dry_run=dry_run)
        result = collector.run()
        return ActionResult(success=True, outputs={"result": result})
    except Exception as e:
        logger.error(f"collector.run failed: {e}")
        return ActionResult(success=False, error=str(e))


def _run_generator(
    account: str = "socialbuilders",
    type: str = "longform",
    dry_run: bool = False,
    **kwargs,
) -> ActionResult:
    """scripts/generate_content.py의 ContentGenerator를 래핑"""
    from scripts.generate_content import ContentGenerator

    try:
        generator = ContentGenerator(dry_run=dry_run)
        result = generator.run()
        return ActionResult(success=True, outputs={"result": result})
    except Exception as e:
        logger.error(f"generator.run failed: {e}")
        return ActionResult(success=False, error=str(e))


def _run_renderer(
    status: str = "pending",
    limit: int = 10,
    dry_run: bool = False,
    **kwargs,
) -> ActionResult:
    """scripts/render_media.py의 렌더링 기능을 래핑

    Args:
        status: 렌더링할 항목의 상태 필터 (pending, draft)
        limit: 최대 렌더링 항목 수
        dry_run: 실제 렌더링 없이 상태만 확인
    """
    from pathlib import Path

    from picko.multimedia_io import parse_multimedia_input
    from picko.templates import ImageRenderer
    from scripts.render_media import get_pending_proposals

    try:
        vault_path = Path("mock_vault")
        proposals = get_pending_proposals(vault_path)

        # Filter by status if specified
        if status != "all":
            proposals = [p for p in proposals if p.get("status") == status]

        # Limit results
        proposals = proposals[:limit]

        if not proposals:
            logger.info("No pending proposals to render")
            return ActionResult(success=True, outputs={"rendered": 0, "message": "No pending proposals"})

        if dry_run:
            return ActionResult(
                success=True,
                outputs={
                    "rendered": 0,
                    "pending_count": len(proposals),
                    "message": f"Found {len(proposals)} pending proposals",
                },
            )

        rendered_count = 0
        errors = []

        for proposal in proposals:
            try:
                input_path = vault_path / "Inbox" / "Multimedia" / f"{proposal['id']}.md"
                if not input_path.exists():
                    continue

                input_data = parse_multimedia_input(input_path)

                # Build context
                context = {
                    "quote": input_data.overlay_text or input_data.concept,
                    "title": input_data.concept,
                    "width": 1080,
                    "height": 1080,
                    "channels": input_data.channels,
                }

                # Render HTML
                renderer = ImageRenderer()
                template = "quote" if input_data.overlay_text and len(input_data.overlay_text) < 100 else "card"
                html = renderer.render_image(
                    template=template,
                    context=context,
                    layout_preset=input_data.account if input_data.account else None,
                )

                # Save HTML output
                output_dir = vault_path / "Assets" / "Images" / proposal["id"]
                output_dir.mkdir(parents=True, exist_ok=True)
                html_path = output_dir / "render.html"
                html_path.write_text(html, encoding="utf-8")

                logger.info(f"Rendered: {proposal['id']}")
                rendered_count += 1

            except Exception as e:
                logger.error(f"Failed to render {proposal.get('id', 'unknown')}: {e}")
                errors.append(f"{proposal.get('id', 'unknown')}: {str(e)}")

        return ActionResult(
            success=True,
            outputs={
                "rendered": rendered_count,
                "errors": errors if errors else None,
            },
        )

    except Exception as e:
        logger.error(f"renderer.run failed: {e}")
        return ActionResult(success=False, error=str(e))


def _run_publisher(
    source_path: str = "Content/Packs/twitter",
    filter: str = "derivative_status=approved",
    text_field: str = "tweet_text",
    update_content_status_to: str = "published",
    publish_log_path: str = "Logs/Publish",
    dry_run: bool = False,
    **kwargs,
) -> ActionResult:
    """Twitter 발행 액션

    Args:
        source_path: 발행할 콘텐츠가 있는 Vault 경로
        filter: frontmatter 필터 조건
        text_field: 트윗 텍스트로 사용할 필드명
        update_content_status_to: 발행 후 업데이트할 상태
        publish_log_path: 발행 로그 저장 경로
        dry_run: 실제 발행 없이 시뮬레이션
    """
    from datetime import datetime

    from picko.publisher import TwitterPublisher
    from picko.vault_io import VaultIO

    try:
        vault = VaultIO()
        from picko.orchestrator.vault_adapter import VaultAdapter

        adapter = VaultAdapter(vault)
        notes = adapter.list(source_path, filter)

        if not notes:
            logger.info(f"No notes found matching filter: {filter}")
            return ActionResult(
                success=True,
                outputs={"published_count": 0, "message": "No matching notes"},
            )

        if dry_run:
            logger.info(f"DRY RUN: Would publish {len(notes)} notes")
            return ActionResult(
                success=True,
                outputs={"published_count": 0, "pending_count": len(notes), "dry_run": True},
            )

        publisher = TwitterPublisher()
        published_count = 0
        errors = []

        for note_path in notes:
            try:
                meta, content = vault.read_note(note_path)
                text = meta.get(text_field) or content.strip()

                if not text:
                    logger.warning(f"No text to publish in {note_path}")
                    continue

                result = publisher.publish(text)

                now = datetime.now().isoformat()

                # Update content status
                vault.update_frontmatter(note_path, {update_content_status_to: now})

                # Create/update publish log
                log_filename = f"pub_{note_path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                log_path = f"{publish_log_path}/{log_filename}"
                vault.ensure_dir(publish_log_path)

                log_meta = {
                    "id": f"pub_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "type": "publish_log",
                    "platform": "twitter",
                    "source": str(note_path.relative_to(vault.root)),
                    "status": "published" if result.success else "failed",
                    "created_at": now,
                    "tweet_id": result.tweet_id,
                    "published_url": result.tweet_url,
                    "error": result.error if not result.success else None,
                }
                log_body = f"# Twitter Publish Log\n\n## Text\n\n{text}\n"
                vault.write_note(log_path, log_body, metadata=log_meta, overwrite=True)

                if result.success:
                    published_count += 1
                    logger.info(f"Published: {note_path} -> {result.tweet_url}")
                else:
                    errors.append(f"{note_path}: {result.error}")
                    logger.error(f"Failed to publish {note_path}: {result.error}")

            except Exception as e:
                errors.append(f"{note_path}: {str(e)}")
                logger.error(f"Error processing {note_path}: {e}")

        return ActionResult(
            success=True,
            outputs={
                "published_count": published_count,
                "total_count": len(notes),
                "errors": errors if errors else None,
            },
        )

    except Exception as e:
        logger.error(f"publisher.run failed: {e}")
        return ActionResult(success=False, error=str(e))
