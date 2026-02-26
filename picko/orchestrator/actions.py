# picko/orchestrator/actions.py
"""액션 레지스트리 — 기존 스크립트를 워크플로우 액션으로 래핑"""

from dataclasses import dataclass, field
from typing import Any, Callable

from picko.logger import get_logger

logger = get_logger("orchestrator.actions")


@dataclass
class ActionResult:
    """액션 실행 결과"""

    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class ActionRegistry:
    """액션 이름 → 실행 함수 매핑"""

    def __init__(self):
        self._actions: dict[str, Callable[..., ActionResult]] = {}

    def register(self, name: str, fn: Callable[..., ActionResult]):
        """액션 등록"""
        self._actions[name] = fn
        logger.debug(f"Registered action: {name}")

    def execute(self, name: str, args: dict | None = None) -> ActionResult:
        """액션 실행. 예외 발생 시 ActionResult(success=False)로 래핑."""
        if name not in self._actions:
            raise KeyError(f"Unknown action: {name}")

        args = args or {}
        try:
            return self._actions[name](**args)
        except Exception as e:
            logger.error(f"Action '{name}' failed: {e}")
            return ActionResult(success=False, error=str(e))

    def list_actions(self) -> list[str]:
        """등록된 액션 이름 목록"""
        return list(self._actions.keys())
