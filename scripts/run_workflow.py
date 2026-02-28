# scripts/run_workflow.py
"""
워크플로우 실행 CLI

Usage:
    python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml
    python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from picko.logger import get_logger
from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import register_default_actions
from picko.orchestrator.engine import WorkflowEngine
from picko.orchestrator.vault_adapter import VaultAdapter
from picko.vault_io import VaultIO

logger = get_logger("run_workflow")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="워크플로우 실행")
    parser.add_argument("--workflow", required=True, help="워크플로우 YAML 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="액션 실행을 dry-run 모드로 전파")

    args = parser.parse_args(argv)
    workflow_path = Path(args.workflow)

    if not workflow_path.exists():
        logger.error(f"Workflow file not found: {workflow_path}")
        sys.exit(1)

    # 컴포넌트 조립
    vault = VaultIO()
    vault_adapter = VaultAdapter(vault)
    registry = ActionRegistry()
    register_default_actions(registry)

    engine = WorkflowEngine(
        vault_adapter=vault_adapter,
        action_registry=registry,
    )

    # 실행
    logger.info(f"Running workflow: {workflow_path}")
    result = engine.run(workflow_path, dry_run=args.dry_run)

    # 결과 출력
    for step_result in result.step_results:
        status = "SKIP" if step_result.skipped else ("OK" if step_result.success else "FAIL")
        logger.info(f"  [{status}] {step_result.name}")
        if step_result.error:
            logger.error(f"    Error: {step_result.error}")

    if result.success:
        logger.info("Workflow completed successfully")
    else:
        logger.error("Workflow completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
