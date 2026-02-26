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
