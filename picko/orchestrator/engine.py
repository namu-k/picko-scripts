# picko/orchestrator/engine.py
"""워크플로우 엔진 — YAML 워크플로우를 로드하고 순차 실행"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from picko.logger import get_logger
from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.expr import ExprEvaluator

logger = get_logger("orchestrator.engine")


@dataclass
class StepResult:
    """단일 step 실행 결과"""

    name: str
    success: bool = False
    skipped: bool = False
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class WorkflowResult:
    """워크플로우 전체 실행 결과"""

    step_results: list[StepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(r.success or r.skipped for r in self.step_results)


class WorkflowEngine:
    """YAML 워크플로우를 로드하고 step을 순차 실행"""

    def __init__(
        self,
        vault_adapter: Any,
        action_registry: ActionRegistry,
    ):
        self._vault = vault_adapter
        self._actions = action_registry
        self._step_outputs: dict[str, dict] = {}

    def run(self, workflow_path: Path) -> WorkflowResult:
        """워크플로우 파일을 로드하고 실행"""
        workflow = self._load(workflow_path)
        logger.info(f"Running workflow: {workflow.get('name', 'unknown')}")

        result = WorkflowResult()

        for step_def in workflow.get("steps", []):
            step_result = self._execute_step(step_def)
            result.step_results.append(step_result)

            if not step_result.skipped:
                self._step_outputs[step_def["name"]] = step_result.outputs

        return result

    def _load(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    def _execute_step(self, step_def: dict) -> StepResult:
        name = step_def["name"]
        action_name = step_def.get("action", "")
        condition = step_def.get("condition")
        args = step_def.get("args", {})

        # condition 평가
        if condition:
            evaluator = ExprEvaluator(
                vault_adapter=self._vault,
                step_outputs=self._step_outputs,
            )
            cond_result = evaluator.evaluate(condition)
            if not cond_result:
                logger.info(f"Step '{name}' skipped (condition false)")
                return StepResult(name=name, skipped=True)

        # args 내 표현식 해석
        resolved_args = self._resolve_args(args)

        # 액션 실행
        try:
            action_result: ActionResult = self._actions.execute(action_name, resolved_args)
            return StepResult(
                name=name,
                success=action_result.success,
                outputs=action_result.outputs,
                error=action_result.error,
            )
        except KeyError as e:
            logger.error(f"Step '{name}' failed: {e}")
            return StepResult(name=name, error=str(e))

    def _resolve_args(self, args: dict) -> dict:
        """args 내 ${{ }} 표현식을 해석"""
        evaluator = ExprEvaluator(
            vault_adapter=self._vault,
            step_outputs=self._step_outputs,
        )
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str) and "${{" in value:
                resolved[key] = evaluator.evaluate(value)
            else:
                resolved[key] = value
        return resolved
