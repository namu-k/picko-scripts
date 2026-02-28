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
        self._step_outputs: dict[str, dict[str, Any]] = {}
        self._dry_run = False

    def run(self, workflow_path: Path, dry_run: bool = False) -> WorkflowResult:
        """워크플로우 파일을 로드하고 실행"""
        self._dry_run = dry_run
        workflow = self._load(workflow_path)
        logger.info(f"Running workflow: {workflow.get('name', 'unknown')}")

        result = WorkflowResult()

        for step_def in workflow.get("steps", []):
            # batch 섹션이 있으면 배치 처리 사용
            if "batch" in step_def:
                step_result = self._execute_step_with_batch(step_def)
            else:
                step_result = self._execute_step(step_def)

            result.step_results.append(step_result)

            if not step_result.skipped:
                self._step_outputs[step_def["name"]] = step_result.outputs

        return result

    def _load(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    def _execute_step(self, step_def: dict[str, Any]) -> StepResult:
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
        if "dry_run" not in resolved_args:
            resolved_args["dry_run"] = self._dry_run

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

    def _resolve_args(self, args: dict[str, Any]) -> dict[str, Any]:
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

    def _execute_step_with_batch(self, step_def: dict[str, Any]) -> StepResult:
        """배치 처리가 포함된 step 실행"""
        from picko.orchestrator.batch import BatchProcessor

        name = step_def["name"]
        action_name = step_def.get("action", "")
        condition = step_def.get("condition")
        args = step_def.get("args", {})
        batch_config = step_def.get("batch")

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

        # batch 설정 파싱
        if not batch_config:
            # 배치 없이 일반 실행
            return self._execute_step(step_def)

        # batch source 해석
        source_expr = batch_config.get("source", [])
        batch_size = batch_config.get("size", 10)
        delay_str = batch_config.get("delay", "0s")

        # delay 파싱 (예: "10s" -> 10.0)
        delay_seconds = self._parse_delay(delay_str)

        # source 표현식 평가
        evaluator = ExprEvaluator(
            vault_adapter=self._vault,
            step_outputs=self._step_outputs,
        )
        items = evaluator.evaluate(source_expr) if isinstance(source_expr, str) else source_expr

        if not items:
            logger.info(f"Step '{name}' skipped (no items to process)")
            return StepResult(name=name, skipped=True, outputs={"processed": 0})

        # 배치 처리
        processor = BatchProcessor(size=batch_size, delay_seconds=delay_seconds)
        all_outputs = []
        errors = []

        def process_batch(batch: list[Any]) -> dict[str, Any]:
            """단일 배치 처리"""
            batch_args = dict(args)
            batch_args["items"] = batch
            resolved_args = self._resolve_args(batch_args)
            if "dry_run" not in resolved_args:
                resolved_args["dry_run"] = self._dry_run
            action_result: ActionResult = self._actions.execute(action_name, resolved_args)
            return {
                "success": action_result.success,
                "outputs": action_result.outputs,
                "error": action_result.error,
            }

        batch_result = processor.run(items, process_batch)

        # 결과 집계 - 배치 처리 결과와 개별 배치 결과 모두 확인
        for result in batch_result.results:
            if result and result.get("outputs"):
                all_outputs.append(result["outputs"])
            if result and result.get("error"):
                errors.append(result["error"])

        # BatchProcessor에서 발생한 예외도 errors에 추가
        errors.extend(batch_result.errors)

        # 성공 여부: 에러가 없고, 모든 배치가 성공해야 함
        all_batches_success = all(result.get("success", False) if result else False for result in batch_result.results)
        success = len(errors) == 0 and all_batches_success

        logger.info(
            f"Step '{name}' batch complete: "
            f"{batch_result.total_batches} batches, "
            f"{len(errors)} errors, "
            f"success={success}"
        )

        return StepResult(
            name=name,
            success=success,
            outputs={
                "batch_results": all_outputs,
                "total_batches": batch_result.total_batches,
                "total_items": batch_result.total_items,
                "errors": errors if errors else None,
            },
            error="; ".join(str(e) for e in errors) if errors else "",
        )

    def _parse_delay(self, delay_str: str) -> float:
        """delay 문자열 파싱 (예: '10s', '1m', '500ms')"""
        if not delay_str:
            return 0.0

        delay_str = delay_str.strip().lower()

        try:
            if delay_str.endswith("ms"):
                return float(delay_str[:-2]) / 1000
            elif delay_str.endswith("s"):
                return float(delay_str[:-1])
            elif delay_str.endswith("m"):
                return float(delay_str[:-1]) * 60
            else:
                return float(delay_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid delay format '{delay_str}': {e}")
            return 0.0
