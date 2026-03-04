# picko/orchestrator/default_actions.py
"""기본 액션 등록 — 기존 스크립트를 액션으로 래핑"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from picko.config import PROJECT_ROOT, get_config
from picko.logger import get_logger
from picko.orchestrator.actions import ActionRegistry, ActionResult

logger = get_logger("orchestrator.default_actions")


def register_default_actions(registry: ActionRegistry):
    """기본 Picko 액션을 레지스트리에 등록"""
    registry.register("collector.run", _run_collector)
    registry.register("generator.run", _run_generator)
    registry.register("renderer.run", _run_renderer)
    registry.register("publisher.run", _run_publisher)
    registry.register("engagement.sync", _run_engagement_sync)
    registry.register("embedding.check_duplicate", _check_duplicate)
    registry.register("quality.verify", _run_quality_verify)


def _extract_item_id(item: object) -> str:
    if isinstance(item, Path):
        return item.stem

    if isinstance(item, str):
        value = item.strip()
        path_like = Path(value)
        if path_like.suffix == ".md":
            return path_like.stem
        return value

    if isinstance(item, dict):
        candidate = item.get("id") or item.get("input_id") or item.get("path")
        if isinstance(candidate, Path):
            return candidate.stem
        if isinstance(candidate, str):
            candidate = candidate.strip()
            path_like = Path(candidate)
            if path_like.suffix == ".md":
                return path_like.stem
            return candidate

    return ""


def _run_collector(account: str = "socialbuilders", dry_run: bool = False, **kwargs) -> ActionResult:
    """scripts/daily_collector.py의 DailyCollector를 래핑"""
    from scripts.daily_collector import DailyCollector

    try:
        collector = DailyCollector(account_id=account, dry_run=dry_run)
        result = collector.run()
        # items를 직접 접근 가능하도록 outputs에 추가
        return ActionResult(
            success=True,
            outputs={
                "result": result,
                "items": result.get("items", []),
            },
        )
    except Exception as e:
        logger.error(f"collector.run failed: {e}")
        return ActionResult(success=False, error=str(e))


def _run_generator(
    account: str = "socialbuilders",
    type: str = "longform",
    dry_run: bool = False,
    items: list[object] | None = None,
    **kwargs,
) -> ActionResult:
    """scripts/generate_content.py의 ContentGenerator를 래핑

    Args:
        account: 계정 ID
        type: 콘텐츠 타입 (longform, packs, image)
        dry_run: 실제 생성 없이 시뮬레이션
        items: 처리할 항목 목록 (배치 처리용, 없으면 전체 처리)
    """
    from scripts.generate_content import ContentGenerator

    try:
        generator = ContentGenerator(dry_run=dry_run)

        # items가 있으면 해당 항목만 처리 (배치 모드)
        if items:
            item_ids = [_extract_item_id(item) for item in items]

            # 유효한 ID만 필터링
            item_ids = [iid for iid in item_ids if iid]

            result = generator.run(
                content_types=[type],
                items=item_ids,
            )
            return ActionResult(
                success=True,
                outputs={
                    "result": result,
                    "processed_count": result.get("approved_items", 0),
                },
            )
        else:
            # 기존 동작: 전체 처리
            result = generator.run(content_types=[type])
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
    from picko.multimedia_io import parse_multimedia_input
    from picko.templates import ImageRenderer
    from scripts.render_media import get_pending_proposals

    try:
        vault_path = Path(get_config().vault.root)
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
    account: str = "socialbuilders",
    source_path: str = "Content/Packs/twitter",
    filter: str = "derivative_status=approved",
    publish_platform: str = "twitter",
    text_field: str = "tweet_text",
    update_content_status_to: str = "published",
    publish_log_status: str = "published",
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
        if publish_platform != "twitter":
            return ActionResult(success=False, error=f"Unsupported publish platform: {publish_platform}")

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
                outputs={
                    "published_count": 0,
                    "pending_count": len(notes),
                    "dry_run": True,
                },
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
                vault.update_frontmatter(
                    note_path,
                    {
                        "status": update_content_status_to,
                        f"{update_content_status_to}_at": now,
                    },
                )

                # Create/update publish log
                log_filename = f"pub_{note_path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                log_path = f"{publish_log_path}/{log_filename}"
                vault.ensure_dir(publish_log_path)

                log_meta = {
                    "id": f"pub_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "type": "publish_log",
                    "platform": publish_platform,
                    "source": str(note_path.relative_to(vault.root)),
                    "status": publish_log_status if result.success else "failed",
                    "created_at": now,
                    "tweet_id": result.tweet_id,
                    "published_url": result.tweet_url,
                    "error": result.error if not result.success else None,
                    "account": account,
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


def _run_engagement_sync(
    platforms: str | list[str] | None = None,
    days: int = 7,
    delay_minutes: int = 0,
    only_recently_published: bool = False,
    dry_run: bool = False,
    **kwargs,
) -> ActionResult:
    """Engagement 지표 동기화 액션.

    # NOTE: delay_minutes, only_recently_published are accepted but currently unused
    """
    from scripts.engagement_sync import EngagementSyncer

    try:
        normalized_platforms: list[str] | None
        if platforms is None:
            normalized_platforms = None
        elif isinstance(platforms, str):
            normalized_platforms = [platforms]
        else:
            normalized_platforms = platforms

        syncer = EngagementSyncer()
        results = syncer.sync_all(days=days, platforms=normalized_platforms, dry_run=dry_run)
        success_count = sum(1 for result in results if result.success)
        failed_count = len(results) - success_count

        return ActionResult(
            success=failed_count == 0,
            outputs={
                "synced_count": success_count,
                "failed_count": failed_count,
                "total": len(results),
            },
            error=f"{failed_count} engagement sync failures" if failed_count else "",
        )
    except Exception as e:
        logger.error(f"engagement.sync failed: {e}")
        return ActionResult(success=False, error=str(e))


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _quality_payload_from_state(state: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "primary": {
            "verdict": state.get("primary_verdict"),
            "confidence": state.get("primary_confidence"),
            "scores": state.get("primary_scores"),
            "reasoning": state.get("primary_reasoning"),
            "flags": state.get("primary_flags"),
        },
        "final_confidence": _to_float(state.get("final_confidence"), 0.0),
        "final_verdict": state.get("final_verdict", ""),
        "enhanced_verification": bool(state.get("enhanced_verification", False)),
        "verified_at": datetime.now().isoformat(),
    }

    if state.get("cross_check_verdict") is not None:
        payload["cross_check"] = {
            "verdict": state.get("cross_check_verdict"),
            "confidence": state.get("cross_check_confidence"),
            "agreement": state.get("cross_check_agreement"),
        }

    return payload


def _append_job_history(existing: Any, entry: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(existing, list):
        history = [item for item in existing if isinstance(item, dict)]
    else:
        history = []
    history.append(entry)
    return history


def _update_quality_note_frontmatter(item_id: str, state: dict[str, Any], dry_run: bool) -> bool:
    if not item_id or dry_run:
        return False

    from picko.vault_io import VaultIO

    note_path = f"{get_config().vault.inbox}/{item_id}.md"
    vault = VaultIO()

    try:
        meta, _ = vault.read_note(note_path)
    except FileNotFoundError:
        logger.debug(f"Skipping frontmatter update, note not found: {note_path}")
        return False
    except Exception as e:
        logger.warning(f"Failed to read note for quality update ({note_path}): {e}")
        return False

    verdict = str(state.get("final_verdict", "")).lower()
    if verdict == "needs_review":
        status = "pending"
    elif verdict == "approved":
        status = "approved"
    elif verdict == "rejected":
        status = "rejected"
    else:
        status = str(meta.get("status", "pending"))

    quality_payload = _quality_payload_from_state(state)
    job_history_entry = {
        "stage": "quality.verify",
        "status": status,
        "verdict": verdict or "unknown",
        "confidence": _to_float(state.get("final_confidence"), 0.0),
        "timestamp": datetime.now().isoformat(),
    }
    job_history = _append_job_history(meta.get("job_history"), job_history_entry)

    try:
        vault.update_frontmatter(
            note_path,
            {
                "quality": quality_payload,
                "job_history": job_history,
                "status": status,
            },
            merge=True,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to update quality frontmatter ({note_path}): {e}")
        return False


def _notify_needs_review(item_id: str, title: str, state: dict[str, Any], dry_run: bool) -> bool:
    if dry_run:
        return False

    verdict = str(state.get("final_verdict", "")).lower()
    if verdict != "needs_review":
        return False

    from picko.notification.bot import HumanReviewBot

    cfg = get_config()
    bot = HumanReviewBot(
        provider=cfg.notification.provider,
        timeout_hours=cfg.notification.review_timeout_hours,
    )

    if not bot.is_configured():
        logger.info("HumanReviewBot not configured, skipping needs_review notification")
        return False

    confidence = _to_float(state.get("final_confidence"), 0.0)
    reason = str(state.get("primary_reasoning") or "Quality verification requires human review")

    try:
        return asyncio.run(
            bot.notify_quality_review(
                item_id=item_id,
                title=title,
                confidence=confidence,
                reason=reason,
            )
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                bot.notify_quality_review(
                    item_id=item_id,
                    title=title,
                    confidence=confidence,
                    reason=reason,
                )
            )
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"Failed to send needs_review notification for {item_id}: {e}")
        return False


def _resolve_source_context(
    source_id: str | None,
    enhanced_verification: bool,
) -> tuple[Any | None, Any | None, bool]:
    if not source_id:
        return None, None, enhanced_verification

    from picko.source_manager import SourceManager

    source_manager: SourceManager | None = None
    source_meta = None
    effective_enhanced = enhanced_verification

    try:
        source_manager = SourceManager(PROJECT_ROOT / "config" / "sources.yml")
        source_meta = source_manager.get_by_id(source_id)
    except Exception as e:
        logger.warning(f"Failed to load source metadata for {source_id}: {e}")
        return None, None, enhanced_verification

    if source_meta and not enhanced_verification:
        is_new_source = source_meta.auto_discovered and source_meta.collected_count < 5
        if is_new_source:
            effective_enhanced = True
            logger.info(f"Auto-enabled enhanced_verification for new source: {source_id}")

    return source_manager, source_meta, effective_enhanced


def _decrement_source_collections_remaining(
    source_manager: Any | None,
    source_meta: Any | None,
    source_id: str | None,
) -> None:
    if not source_manager or not source_meta or not source_id:
        return
    if not source_meta.enhanced_verification:
        return

    try:
        current_remaining = source_meta.enhanced_verification.get("collections_remaining", 0)
        if current_remaining > 0:
            updated_ev = dict(source_meta.enhanced_verification)
            updated_ev["collections_remaining"] = current_remaining - 1
            source_manager.update_stats(str(source_id), enhanced_verification=updated_ev)
            logger.info(
                "Decremented collections_remaining for %s: %s -> %s",
                source_id,
                current_remaining,
                current_remaining - 1,
            )
    except Exception as e:
        logger.warning(f"Failed to update source metadata for {source_id}: {e}")


def _run_quality_verify_single(
    graph: Any,
    dry_run: bool,
    item_id: str,
    title: str,
    content: str,
    enhanced_verification: bool,
    thread_id: str | None,
    source_manager: Any | None,
    source_meta: Any | None,
    source_id: str | None,
) -> ActionResult:
    target_id = item_id or "unknown"
    state = graph.verify(
        item_id=target_id,
        title=title,
        content=content,
        enhanced_verification=enhanced_verification,
        thread_id=thread_id,
    )

    _decrement_source_collections_remaining(source_manager, source_meta, source_id)

    state_dict = dict(state)
    updated_frontmatter = _update_quality_note_frontmatter(target_id, state_dict, dry_run)
    notified = _notify_needs_review(
        target_id,
        title or target_id,
        state_dict,
        dry_run,
    )

    return ActionResult(
        success=True,
        outputs={
            "result": state,
            "frontmatter_updated": updated_frontmatter,
            "needs_review_notified": notified,
        },
    )


def _run_quality_verify_batch(
    graph: Any,
    account: str,
    items: list[object],
    threshold: float,
    dry_run: bool,
    enhanced_verification: bool,
) -> ActionResult:
    results: list[dict[str, Any]] = []
    verified: list[str] = []
    pending: list[str] = []
    rejected: list[str] = []
    frontmatter_updated_count = 0
    needs_review_notified_count = 0

    for item in items:
        target_id = _extract_item_id(item)
        if not target_id:
            target_id = "unknown"

        current_title = ""
        current_content = ""
        current_enhanced = enhanced_verification

        if isinstance(item, dict):
            raw_title = item.get("title", "")
            current_title = raw_title if isinstance(raw_title, str) else ""
            raw_content = item.get("content") or item.get("text", "")
            current_content = raw_content if isinstance(raw_content, str) else ""
            current_enhanced = bool(item.get("enhanced_verification", enhanced_verification))

        state = graph.verify(
            item_id=target_id,
            title=current_title,
            content=current_content,
            enhanced_verification=current_enhanced,
            thread_id=f"quality-{target_id}",
        )
        state_dict = dict(state)
        results.append(state_dict)

        if _update_quality_note_frontmatter(target_id, state_dict, dry_run):
            frontmatter_updated_count += 1
        if _notify_needs_review(target_id, current_title or target_id, state_dict, dry_run):
            needs_review_notified_count += 1

        verdict = state.get("final_verdict")
        confidence = float(state.get("final_confidence", 0.0))
        if verdict == "approved" or confidence >= threshold:
            verified.append(target_id)
        elif verdict == "needs_review":
            pending.append(target_id)
        else:
            rejected.append(target_id)

    return ActionResult(
        success=True,
        outputs={
            "results": results,
            "verified": verified,
            "pending": pending,
            "rejected": rejected,
            "total": len(items),
            "dry_run": dry_run,
            "account": account,
            "frontmatter_updated_count": frontmatter_updated_count,
            "needs_review_notified_count": needs_review_notified_count,
        },
    )


def _run_quality_verify(
    account: str = "socialbuilders",
    items: list[object] | None = None,
    threshold: float = 0.85,
    dry_run: bool = False,
    item_id: str = "",
    title: str = "",
    content: str = "",
    enhanced_verification: bool = False,
    thread_id: str | None = None,
    source_id: str | None = None,
    **kwargs,
) -> ActionResult:
    """Quality verification action wrapper.

    Supports both single-item invocation and batch invocation via `items`.

    When source_id is provided, auto-detects if enhanced_verification should be enabled
    based on source metadata (auto_discovered && collected_count < 5).
    """
    from picko.quality.graph import QualityGraph

    try:
        graph = QualityGraph()
        source_manager, source_meta, effective_enhanced = _resolve_source_context(
            source_id,
            enhanced_verification,
        )

        if not items:
            return _run_quality_verify_single(
                graph=graph,
                dry_run=dry_run,
                item_id=item_id,
                title=title,
                content=content,
                enhanced_verification=effective_enhanced,
                thread_id=thread_id,
                source_manager=source_manager,
                source_meta=source_meta,
                source_id=source_id,
            )

        return _run_quality_verify_batch(
            graph=graph,
            account=account,
            items=items,
            threshold=threshold,
            dry_run=dry_run,
            enhanced_verification=effective_enhanced,
        )
    except Exception as e:
        logger.error(f"quality.verify failed: {e}")
        return ActionResult(success=False, error=str(e))


def _check_duplicate(
    source: list[str] | list[dict[str, Any]],
    threshold: float = 0.9,
    embedding_field: str = "text",
    **kwargs,
) -> ActionResult:
    """임베딩 기반 중복 검사 액션

    Args:
        source: 검사할 아이템 목록 (경로 리스트 또는 딕셔너리 리스트)
        threshold: 중복 판정 임계값 (0-1, 코사인 유사도)
        embedding_field: 텍스트를 추출할 필드명 (딕셔너리인 경우)

    Returns:
        ActionResult with duplicates and unique items
    """
    from pathlib import Path

    import numpy as np

    from picko.embedding import get_embedding_manager
    from picko.vault_io import VaultIO

    try:
        embedder = get_embedding_manager()
        vault: VaultIO | None = None

        # 텍스트 추출
        items_with_embeddings = []

        for item in source:
            if isinstance(item, str):
                # 경로인 경우 파일에서 텍스트 읽기
                try:
                    path = Path(item)
                    if path.exists():
                        text = path.read_text(encoding="utf-8")[:2000]
                    elif "/" in item or "\\" in item or path.suffix == ".md":
                        if vault is None:
                            vault = VaultIO()
                        _, content = vault.read_note(item)
                        text = content[:2000]
                    else:
                        text = item
                except Exception:
                    text = item  # 텍스트 자체로 처리
            elif isinstance(item, dict):
                raw_text = item.get(embedding_field, "")
                text = raw_text if isinstance(raw_text, str) else str(raw_text)
            else:
                text = str(item)  # type: ignore[unreachable]
            if text:
                embedding = embedder.embed(text)
                items_with_embeddings.append(
                    {
                        "item": item,
                        "embedding": np.array(embedding),
                    }
                )

        # 중복 검사
        duplicates = []
        unique = []
        seen_embeddings: list[dict[str, Any]] = []

        for entry in items_with_embeddings:
            is_duplicate = False
            duplicate_of = None
            similarity = 0.0

            for seen in seen_embeddings:
                # 코사인 유사도 계산
                entry_embedding = cast(np.ndarray, entry["embedding"])
                seen_embedding = cast(np.ndarray, seen["embedding"])
                norm_entry = np.linalg.norm(entry_embedding)
                norm_seen = np.linalg.norm(seen_embedding)

                # zero-norm 가드: 둘 중 하나라도 0이면 유사도 0
                if norm_entry == 0 or norm_seen == 0:
                    similarity = 0.0
                else:
                    similarity = np.dot(entry_embedding, seen_embedding) / (norm_entry * norm_seen)

                if similarity >= threshold:
                    is_duplicate = True
                    duplicate_of = seen["item"]
                    break

            if is_duplicate:
                duplicates.append(
                    {
                        "item": entry["item"],
                        "duplicate_of": duplicate_of,
                        "similarity": float(similarity),
                    }
                )
            else:
                unique.append(entry["item"])
                seen_embeddings.append(entry)

        logger.info(f"Duplicate check: {len(duplicates)} duplicates, {len(unique)} unique")

        return ActionResult(
            success=True,
            outputs={
                "duplicates": duplicates,
                "unique": unique,
                "total": len(source),
                "duplicate_count": len(duplicates),
                "unique_count": len(unique),
            },
        )

    except Exception as e:
        logger.error(f"embedding.check_duplicate failed: {e}")
        return ActionResult(success=False, error=str(e))
