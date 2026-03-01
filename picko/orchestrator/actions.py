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


@dataclass
class FallbackConfig:
    """Step fallback configuration."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FallbackConfig":
        action = data.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("fallback.action must be a non-empty string")

        raw_args = data.get("args", {})
        args = raw_args if isinstance(raw_args, dict) else {}
        return cls(action=action, args=args)


@dataclass
class ActionConfig:
    """Typed workflow step configuration."""

    name: str
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    batch: dict[str, Any] | None = None
    dynamic_steps: list[dict[str, Any]] = field(default_factory=list)
    fallback: FallbackConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionConfig":
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("step.name must be a non-empty string")

        action = data.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("step.action must be a non-empty string")

        raw_args = data.get("args", {})
        args = raw_args if isinstance(raw_args, dict) else {}

        condition = data.get("condition")
        if condition is not None and not isinstance(condition, str):
            condition = str(condition)

        raw_batch = data.get("batch")
        batch = raw_batch if isinstance(raw_batch, dict) else None

        raw_dynamic = data.get("dynamic_steps", [])
        dynamic_steps = raw_dynamic if isinstance(raw_dynamic, list) else []

        fallback_data = data.get("fallback")
        fallback = FallbackConfig.from_dict(fallback_data) if isinstance(fallback_data, dict) else None

        return cls(
            name=name,
            action=action,
            args=args,
            condition=condition,
            batch=batch,
            dynamic_steps=dynamic_steps,
            fallback=fallback,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "action": self.action,
            "args": self.args,
        }

        if self.condition:
            data["condition"] = self.condition
        if self.batch is not None:
            data["batch"] = self.batch
        if self.dynamic_steps:
            data["dynamic_steps"] = self.dynamic_steps
        if self.fallback:
            data["fallback"] = {
                "action": self.fallback.action,
                "args": self.fallback.args,
            }
        return data


class ActionRegistry:
    """액션 이름 → 실행 함수 매핑"""

    def __init__(self):
        self._actions: dict[str, Callable[..., ActionResult]] = {}

    def register(self, name: str, fn: Callable[..., ActionResult]):
        """액션 등록"""
        self._actions[name] = fn
        logger.debug(f"Registered action: {name}")

    def execute(self, name: str, args: dict[str, Any] | None = None) -> ActionResult:
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
