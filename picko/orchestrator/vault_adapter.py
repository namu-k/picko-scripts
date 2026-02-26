# picko/orchestrator/vault_adapter.py
"""Vault frontmatter 쿼리 어댑터"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

from picko.logger import get_logger
from picko.vault_io import VaultIO

logger = get_logger("orchestrator.vault_adapter")

# 필터 연산자: !=를 =보다 먼저 매칭해야 함
_FILTER_OPS = ["!=", ">=", "<=", ">", "<", "="]


class VaultAdapter:
    """Vault frontmatter를 쿼리하는 어댑터"""

    def __init__(self, vault_io: VaultIO):
        self._vault = vault_io

    def count(self, path: str, filter_expr: str = "") -> int:
        """조건에 맞는 노트 수 반환"""
        return len(self.list(path, filter_expr))

    def list(self, path: str, filter_expr: str = "") -> List[Path]:
        """조건에 맞는 노트 경로 목록 반환"""
        notes = self._vault.list_notes(path)
        if not filter_expr:
            return notes

        conditions = self._parse_filter(filter_expr)
        matched = []
        for note_path in notes:
            try:
                meta = self._vault.read_frontmatter(note_path)
                if self._matches(meta, conditions):
                    matched.append(note_path)
            except Exception as e:
                logger.warning(f"Error reading {note_path}: {e}")
        return matched

    def field(self, note_path: str, field_name: str) -> Any:
        """특정 노트의 frontmatter 필드 값 반환"""
        meta = self._vault.read_frontmatter(note_path)
        return meta.get(field_name)

    def _parse_filter(self, filter_expr: str) -> List[Tuple[str, str, str]]:
        """
        필터 문자열을 (field, op, value) 튜플 리스트로 파싱

        Examples:
            "writing_status=auto_ready" → [("writing_status", "==", "auto_ready")]
            "score>0.8,status!=done" → [("score", ">", "0.8"), ("status", "!=", "done")]
        """
        if not filter_expr.strip():
            return []

        conditions = []
        for part in filter_expr.split(","):
            part = part.strip()
            if not part:
                continue

            for op in _FILTER_OPS:
                if op in part:
                    field, value = part.split(op, 1)
                    # "=" → "==" 으로 정규화
                    normalized_op = "==" if op == "=" else op
                    conditions.append((field.strip(), normalized_op, value.strip()))
                    break

        return conditions

    def _matches(self, meta: dict, conditions: List[Tuple[str, str, str]]) -> bool:
        """frontmatter가 모든 조건을 만족하는지 확인 (AND)"""
        for field, op, value in conditions:
            actual = meta.get(field)
            if actual is None:
                return False

            if op == "==":
                if str(actual) != value:
                    return False
            elif op == "!=":
                if str(actual) == value:
                    return False
            elif op in (">", "<", ">=", "<="):
                try:
                    actual_num = float(actual)
                    value_num = float(value)
                except (ValueError, TypeError):
                    return False
                if op == ">" and not (actual_num > value_num):
                    return False
                elif op == "<" and not (actual_num < value_num):
                    return False
                elif op == ">=" and not (actual_num >= value_num):
                    return False
                elif op == "<=" and not (actual_num <= value_num):
                    return False

        return True
