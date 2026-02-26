# picko/orchestrator/expr.py
"""
안전한 표현식 평가기

지원하는 표현식:
- ${{ vault.count(path, filter) }}
- ${{ vault.count(path, filter) > N }}
- ${{ vault.list(path, filter) }}
- ${{ vault.field(path, field) }}
- ${{ steps.<name>.outputs.<key> }}
- 일반 문자열 (그대로 반환)
"""

from __future__ import annotations

import re
from typing import Any

from picko.logger import get_logger

logger = get_logger("orchestrator.expr")

# ${{ ... }} 패턴
_EXPR_PATTERN = re.compile(r"^\$\{\{\s*(.+?)\s*\}\}$")

# vault.method('arg1', 'arg2') 패턴
_VAULT_CALL_PATTERN = re.compile(r"vault\.(\w+)\(\s*'([^']*)'\s*(?:,\s*'([^']*)'\s*)?\)")

# 비교 연산: expr > N, expr < N, expr >= N, expr <= N, expr == N
_COMPARE_PATTERN = re.compile(r"(.+?)\s*(>=|<=|>|<|==|!=)\s*(\S+)\s*$")

# steps.name.outputs.key 패턴
_STEPS_PATTERN = re.compile(r"steps\.(\w+)\.outputs\.(\w+)")

# steps.name.outputs 전체 참조 패턴 (Phase 2)
_STEPS_OUTPUTS_PATTERN = re.compile(r"steps\.(\w+)\.outputs$")


class ExprEvaluator:
    """${{ }} 표현식을 안전하게 평가"""

    def __init__(self, vault_adapter: Any, step_outputs: dict[str, dict]):
        self._vault = vault_adapter
        self._steps = step_outputs

    def evaluate(self, expr: str) -> Any:
        """
        표현식 평가.

        - ${{ ... }}이면 내부 표현식 파싱 후 실행
        - 그 외 문자열은 그대로 반환
        """
        match = _EXPR_PATTERN.match(expr.strip())
        if not match:
            return expr

        inner = match.group(1).strip()
        return self._evaluate_inner(inner)

    def _evaluate_inner(self, inner: str) -> Any:
        # 비교 연산이 있는지 먼저 확인
        cmp_match = _COMPARE_PATTERN.match(inner)
        if cmp_match:
            left_expr = cmp_match.group(1).strip()
            op = cmp_match.group(2)
            right_val = cmp_match.group(3)

            left = self._evaluate_inner(left_expr)
            return self._compare(left, op, right_val)

        # vault.method() 호출
        vault_match = _VAULT_CALL_PATTERN.match(inner)
        if vault_match:
            method = vault_match.group(1)
            arg1 = vault_match.group(2)
            arg2 = vault_match.group(3) or ""
            return self._call_vault(method, arg1, arg2)

        # steps.name.outputs 전체 참조 (Phase 2)
        steps_outputs_match = _STEPS_OUTPUTS_PATTERN.match(inner)
        if steps_outputs_match:
            step_name = steps_outputs_match.group(1)
            return self._steps.get(step_name, {}).get("outputs", {})

        # steps.name.outputs.key 참조
        steps_match = _STEPS_PATTERN.match(inner)
        if steps_match:
            step_name = steps_match.group(1)
            output_key = steps_match.group(2)
            return self._steps.get(step_name, {}).get(output_key)
        logger.warning(f"Unrecognized expression: {inner}")
        return None

    def _call_vault(self, method: str, arg1: str, arg2: str) -> Any:
        if self._vault is None:
            logger.warning("VaultAdapter not available")
            return None

        fn = getattr(self._vault, method, None)
        if fn is None:
            logger.warning(f"Unknown vault method: {method}")
            return None

        if arg2:
            return fn(arg1, arg2)
        return fn(arg1)

    def _compare(self, left: Any, op: str, right_str: str) -> bool:
        try:
            left_num = float(left)
            right_num = float(right_str)
        except (ValueError, TypeError):
            return False

        if op == ">":
            return left_num > right_num
        elif op == "<":
            return left_num < right_num
        elif op == ">=":
            return left_num >= right_num
        elif op == "<=":
            return left_num <= right_num
        elif op == "==":
            return left_num == right_num
        elif op == "!=":
            return left_num != right_num
        return False
