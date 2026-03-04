# picko/orchestrator/expr.py
"""
안전한 표현식 평가기

지원하는 표현식:
- ${{ vault.count(path, filter) }}
- ${{ vault.count(path, filter) > N }}
- ${{ vault.list(path, filter) }}
- ${{ vault.field(path, field) }}
- ${{ steps.<name>.outputs.<key> }}
- ${{ contains_topic(steps.<name>.outputs.<key>, 'topic') }}
- ${{ score_range(steps.<name>.outputs.<key>, min, max) }}
- ${{ has_quality_flag(steps.<name>.outputs.<key>, 'flag') }}
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

# custom helper operators (Phase 4)
_CONTAINS_TOPIC_PATTERN = re.compile(r"contains_topic\(\s*(.+?)\s*,\s*'([^']+)'\s*\)$")
_SCORE_RANGE_PATTERN = re.compile(r"score_range\(\s*(.+?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)$")
_HAS_QUALITY_FLAG_PATTERN = re.compile(r"has_quality_flag\(\s*(.+?)\s*,\s*'([^']+)'\s*\)$")


class ExprEvaluator:
    """${{ }} 표현식을 안전하게 평가"""

    def __init__(self, vault_adapter: Any, step_outputs: dict[str, dict[str, Any]]):
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

        # custom helper: contains_topic(source, 'topic')
        contains_topic_match = _CONTAINS_TOPIC_PATTERN.match(inner)
        if contains_topic_match:
            source_expr = contains_topic_match.group(1).strip()
            topic = contains_topic_match.group(2)
            source = self._evaluate_inner(source_expr)
            return self._contains_topic(source, topic)

        # custom helper: score_range(value, min, max)
        score_range_match = _SCORE_RANGE_PATTERN.match(inner)
        if score_range_match:
            value_expr = score_range_match.group(1).strip()
            min_score = float(score_range_match.group(2))
            max_score = float(score_range_match.group(3))
            value = self._evaluate_inner(value_expr)
            return self._score_range(value, min_score, max_score)

        # custom helper: has_quality_flag(flags, 'flag')
        quality_flag_match = _HAS_QUALITY_FLAG_PATTERN.match(inner)
        if quality_flag_match:
            flags_expr = quality_flag_match.group(1).strip()
            flag_name = quality_flag_match.group(2)
            flags = self._evaluate_inner(flags_expr)
            return self._has_quality_flag(flags, flag_name)

        # steps.name.outputs 전체 참조 (Phase 2)
        steps_outputs_match = _STEPS_OUTPUTS_PATTERN.match(inner)
        if steps_outputs_match:
            step_name = steps_outputs_match.group(1)
            return self._steps.get(step_name, {})  # BUGFIX: outputs stored directly, not nested under "outputs"

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

    def _contains_topic(self, source: Any, topic: str) -> bool:
        needle = topic.strip().lower()
        if not needle:
            return False

        if isinstance(source, str):
            return needle in source.lower()

        if isinstance(source, dict):
            for key, value in source.items():
                if str(key).lower() == needle:
                    return True
                if isinstance(value, str) and value.lower() == needle:
                    return True
            return False

        if isinstance(source, (list, tuple, set)):
            for item in source:
                if isinstance(item, str) and item.lower() == needle:
                    return True
                if isinstance(item, dict):
                    for key, value in item.items():
                        if str(key).lower() == needle:
                            return True
                        if isinstance(value, str) and value.lower() == needle:
                            return True
        return False

    def _score_range(self, value: Any, min_score: float, max_score: float) -> bool:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return False

        lower = min(min_score, max_score)
        upper = max(min_score, max_score)
        return lower <= score <= upper

    def _has_quality_flag(self, flags: Any, flag_name: str) -> bool:
        needle = flag_name.strip().lower()
        if not needle:
            return False

        if isinstance(flags, dict):
            for key, value in flags.items():
                if str(key).lower() == needle:
                    return bool(value)
            return False

        if isinstance(flags, (list, tuple, set)):
            return any(str(item).lower() == needle for item in flags)

        if isinstance(flags, str):
            values = [item.strip().lower() for item in flags.split(",") if item.strip()]
            return needle in values

        return False

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
