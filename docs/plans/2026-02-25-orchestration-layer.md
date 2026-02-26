# Orchestration Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Vault 상태 기반 워크플로우 오케스트레이션 레이어 구현 (Phase 1: VaultAdapter + ActionRegistry + WorkflowEngine + CLI)

**Architecture:** 기존 `vault_io.py`의 `VaultIO` 위에 frontmatter 집계 쿼리를 제공하는 `VaultAdapter`, 기존 스크립트를 래핑하는 `ActionRegistry`, YAML 워크플로우를 순차 실행하는 `WorkflowEngine`으로 구성. 기존 모듈은 일절 수정하지 않음.

**Tech Stack:** Python 3.13, PyYAML, python-frontmatter, pytest, 기존 picko 모듈

---

## Task 1: VaultAdapter — 필터 파서

**Files:**
- Create: `picko/orchestrator/__init__.py`
- Create: `picko/orchestrator/vault_adapter.py`
- Test: `tests/test_vault_adapter.py`

### Step 1: Write the failing test

```python
# tests/test_vault_adapter.py
"""VaultAdapter 필터 파싱 및 Vault 쿼리 테스트"""

import frontmatter

from picko.orchestrator.vault_adapter import VaultAdapter
from picko.vault_io import VaultIO


class TestParseFilter:
    """필터 문자열 파싱 테스트"""

    def test_equal_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("writing_status=auto_ready")
        assert conditions == [("writing_status", "==", "auto_ready")]

    def test_not_equal_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("writing_status!=completed")
        assert conditions == [("writing_status", "!=", "completed")]

    def test_greater_than_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("score>0.8")
        assert conditions == [("score", ">", "0.8")]

    def test_multiple_filters(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter(
            "writing_status=auto_ready,score>0.5"
        )
        assert len(conditions) == 2
        assert conditions[0] == ("writing_status", "==", "auto_ready")
        assert conditions[1] == ("score", ">", "0.5")

    def test_empty_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("")
        assert conditions == []
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_vault_adapter.py::TestParseFilter -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'picko.orchestrator'`

### Step 3: Write minimal implementation

```python
# picko/orchestrator/__init__.py
"""오케스트레이션 레이어"""
```

```python
# picko/orchestrator/vault_adapter.py
"""Vault frontmatter 쿼리 어댑터"""

import re
from pathlib import Path
from typing import Any

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

    def list(self, path: str, filter_expr: str = "") -> list[Path]:
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

    def _parse_filter(self, filter_expr: str) -> list[tuple[str, str, str]]:
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

    def _matches(
        self, meta: dict, conditions: list[tuple[str, str, str]]
    ) -> bool:
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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_vault_adapter.py::TestParseFilter -v`
Expected: PASS (5 tests)

### Step 5: Commit

```bash
git add picko/orchestrator/__init__.py picko/orchestrator/vault_adapter.py tests/test_vault_adapter.py
git commit -m "feat(orchestrator): add VaultAdapter filter parser"
```

---

## Task 2: VaultAdapter — Vault 쿼리 (count, list, field)

**Files:**
- Modify: `picko/orchestrator/vault_adapter.py` (이미 구현 포함)
- Test: `tests/test_vault_adapter.py`

### Step 1: Write the failing test

`tests/test_vault_adapter.py`에 아래 클래스 추가:

```python
class TestVaultQuery:
    """VaultAdapter의 count/list/field 테스트"""

    def _write_note(self, vault_dir, rel_path, metadata, content=""):
        """헬퍼: frontmatter가 있는 마크다운 파일 생성"""
        full_path = vault_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content)
        post.metadata = metadata
        full_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return full_path

    def test_count_with_filter(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "score": 0.9},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "pending", "score": 0.5},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note3.md",
            {"writing_status": "auto_ready", "score": 0.7},
        )

        vault = VaultIO(vault_root=vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count("Inbox/Inputs", "writing_status=auto_ready") == 2
        assert adapter.count("Inbox/Inputs", "score>0.8") == 1
        assert adapter.count("Inbox/Inputs", "") == 3

    def test_list_returns_paths(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready"},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "pending"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        result = adapter.list("Inbox/Inputs", "writing_status=auto_ready")
        assert len(result) == 1
        assert result[0].name == "note1.md"

    def test_field_returns_value(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "title": "Test Note"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.field("Inbox/Inputs/note1.md", "writing_status") == "auto_ready"
        assert adapter.field("Inbox/Inputs/note1.md", "title") == "Test Note"
        assert adapter.field("Inbox/Inputs/note1.md", "nonexistent") is None

    def test_count_empty_directory(self, temp_vault_dir):
        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count("Inbox/Inputs", "writing_status=auto_ready") == 0

    def test_multiple_conditions_and(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "score": 0.9},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "auto_ready", "score": 0.3},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count(
            "Inbox/Inputs", "writing_status=auto_ready,score>0.5"
        ) == 1
```

**주의:** `test_count_with_filter`의 `vault_dir` → `temp_vault_dir`로 통일. `temp_vault_dir` fixture는 conftest.py에 이미 있음.

### Step 2: Run test to verify it fails

Run: `pytest tests/test_vault_adapter.py::TestVaultQuery -v`
Expected: PASS — 이미 Task 1에서 구현 완료. 실패하면 VaultIO 연동 문제이므로 디버깅.

### Step 3: Fix any issues

`_matches` 메서드가 숫자 비교에서 frontmatter의 값이 이미 float일 수 있음. `str(actual) != value` 비교가 `0.9 != "0.9"` 같은 경우를 처리하도록 확인.

### Step 4: Run full test suite

Run: `pytest tests/test_vault_adapter.py -v`
Expected: PASS (전체)

### Step 5: Commit

```bash
git add tests/test_vault_adapter.py
git commit -m "test(orchestrator): add VaultAdapter query integration tests"
```

---

## Task 3: ActionRegistry — 액션 등록 및 실행

**Files:**
- Create: `picko/orchestrator/actions.py`
- Test: `tests/test_orchestrator_actions.py`

### Step 1: Write the failing test

```python
# tests/test_orchestrator_actions.py
"""ActionRegistry 테스트"""

import pytest

from picko.orchestrator.actions import ActionRegistry, ActionResult


class TestActionRegistry:
    def test_register_and_execute(self):
        registry = ActionRegistry()

        def my_action(**kwargs) -> ActionResult:
            return ActionResult(
                success=True,
                outputs={"count": kwargs.get("n", 0)},
            )

        registry.register("test.action", my_action)
        result = registry.execute("test.action", {"n": 42})

        assert result.success is True
        assert result.outputs["count"] == 42

    def test_execute_unknown_action(self):
        registry = ActionRegistry()
        with pytest.raises(KeyError, match="Unknown action"):
            registry.execute("nonexistent", {})

    def test_action_failure_returns_result(self):
        registry = ActionRegistry()

        def failing_action(**kwargs) -> ActionResult:
            raise ValueError("something broke")

        registry.register("test.fail", failing_action)
        result = registry.execute("test.fail", {})

        assert result.success is False
        assert "something broke" in result.error

    def test_list_actions(self):
        registry = ActionRegistry()
        registry.register("a.run", lambda **kw: ActionResult(success=True))
        registry.register("b.run", lambda **kw: ActionResult(success=True))

        assert sorted(registry.list_actions()) == ["a.run", "b.run"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_orchestrator_actions.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: Write minimal implementation

```python
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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_orchestrator_actions.py -v`
Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add picko/orchestrator/actions.py tests/test_orchestrator_actions.py
git commit -m "feat(orchestrator): add ActionRegistry with error wrapping"
```

---

## Task 4: 표현식 평가기

**Files:**
- Create: `picko/orchestrator/expr.py`
- Test: `tests/test_orchestrator_expr.py`

### Step 1: Write the failing test

```python
# tests/test_orchestrator_expr.py
"""표현식 평가기 테스트"""

import pytest

from picko.orchestrator.expr import ExprEvaluator


class TestExprEvaluator:
    def test_vault_count_expression(self):
        """${{ vault.count(...) > 0 }} 평가"""
        mock_vault = type("V", (), {
            "count": lambda self, path, f: 3,
        })()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate(
            "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}"
        )
        assert result is True

    def test_vault_count_zero(self):
        mock_vault = type("V", (), {
            "count": lambda self, path, f: 0,
        })()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate(
            "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}"
        )
        assert result is False

    def test_step_output_reference(self):
        evaluator = ExprEvaluator(
            vault_adapter=None,
            step_outputs={"collect": {"items": ["a", "b", "c"]}},
        )
        result = evaluator.evaluate("${{ steps.collect.outputs.items }}")
        assert result == ["a", "b", "c"]

    def test_plain_string_passthrough(self):
        evaluator = ExprEvaluator(vault_adapter=None, step_outputs={})
        result = evaluator.evaluate("just a string")
        assert result == "just a string"

    def test_vault_list_expression(self):
        mock_vault = type("V", (), {
            "list": lambda self, path, f: ["/a.md", "/b.md"],
        })()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate(
            "${{ vault.list('Content/Longform', 'derivative_status=approved') }}"
        )
        assert result == ["/a.md", "/b.md"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_orchestrator_expr.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: Write minimal implementation

```python
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

import re
from typing import Any

from picko.logger import get_logger

logger = get_logger("orchestrator.expr")

# ${{ ... }} 패턴
_EXPR_PATTERN = re.compile(r"^\$\{\{\s*(.+?)\s*\}\}$")

# vault.method('arg1', 'arg2') 패턴
_VAULT_CALL_PATTERN = re.compile(
    r"vault\.(\w+)\(\s*'([^']*)'\s*(?:,\s*'([^']*)'\s*)?\)"
)

# 비교 연산: expr > N, expr < N, expr >= N, expr <= N, expr == N
_COMPARE_PATTERN = re.compile(
    r"(.+?)\s*(>=|<=|>|<|==|!=)\s*(\S+)\s*$"
)

# steps.name.outputs.key 패턴
_STEPS_PATTERN = re.compile(r"steps\.(\w+)\.outputs\.(\w+)")


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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_orchestrator_expr.py -v`
Expected: PASS (5 tests)

### Step 5: Commit

```bash
git add picko/orchestrator/expr.py tests/test_orchestrator_expr.py
git commit -m "feat(orchestrator): add safe expression evaluator for workflow conditions"
```

---

## Task 5: WorkflowEngine — YAML 로드 및 step 실행

**Files:**
- Create: `picko/orchestrator/engine.py`
- Test: `tests/test_orchestrator_engine.py`

### Step 1: Write the failing test

```python
# tests/test_orchestrator_engine.py
"""WorkflowEngine 테스트"""

from pathlib import Path

import yaml

from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.engine import WorkflowEngine, WorkflowResult


class TestWorkflowEngine:
    def _write_workflow(self, tmp_path, steps):
        """헬퍼: 워크플로우 YAML 파일 생성"""
        workflow = {
            "name": "test_workflow",
            "description": "test",
            "steps": steps,
        }
        path = tmp_path / "test.yml"
        path.write_text(yaml.dump(workflow), encoding="utf-8")
        return path

    def test_simple_step_execution(self, tmp_path):
        registry = ActionRegistry()
        call_log = []

        def mock_action(**kwargs):
            call_log.append(kwargs)
            return ActionResult(success=True, outputs={"done": True})

        registry.register("test.run", mock_action)

        workflow_path = self._write_workflow(tmp_path, [
            {"name": "step1", "action": "test.run", "args": {"x": 1}},
        ])

        engine = WorkflowEngine(
            vault_adapter=None, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert len(result.step_results) == 1
        assert result.step_results[0].success is True
        assert call_log == [{"x": 1}]

    def test_condition_false_skips_step(self, tmp_path):
        registry = ActionRegistry()
        call_log = []

        def mock_action(**kwargs):
            call_log.append(True)
            return ActionResult(success=True)

        registry.register("test.run", mock_action)

        # vault.count() 가 0 반환 → condition false → skip
        mock_vault = type("V", (), {
            "count": lambda self, p, f: 0,
        })()

        workflow_path = self._write_workflow(tmp_path, [
            {
                "name": "step1",
                "action": "test.run",
                "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
            },
        ])

        engine = WorkflowEngine(
            vault_adapter=mock_vault, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert len(result.step_results) == 1
        assert result.step_results[0].skipped is True
        assert call_log == []

    def test_condition_true_runs_step(self, tmp_path):
        registry = ActionRegistry()
        call_log = []

        def mock_action(**kwargs):
            call_log.append(True)
            return ActionResult(success=True)

        registry.register("test.run", mock_action)

        mock_vault = type("V", (), {
            "count": lambda self, p, f: 5,
        })()

        workflow_path = self._write_workflow(tmp_path, [
            {
                "name": "step1",
                "action": "test.run",
                "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
            },
        ])

        engine = WorkflowEngine(
            vault_adapter=mock_vault, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert result.step_results[0].skipped is False
        assert call_log == [True]

    def test_multi_step_sequential(self, tmp_path):
        registry = ActionRegistry()
        order = []

        def action_a(**kwargs):
            order.append("a")
            return ActionResult(success=True, outputs={"val": 1})

        def action_b(**kwargs):
            order.append("b")
            return ActionResult(success=True, outputs={"val": 2})

        registry.register("a.run", action_a)
        registry.register("b.run", action_b)

        workflow_path = self._write_workflow(tmp_path, [
            {"name": "first", "action": "a.run"},
            {"name": "second", "action": "b.run"},
        ])

        engine = WorkflowEngine(
            vault_adapter=None, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert order == ["a", "b"]
        assert len(result.step_results) == 2
        assert all(r.success for r in result.step_results)
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_orchestrator_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: Write minimal implementation

```python
# picko/orchestrator/engine.py
"""워크플로우 엔진 — YAML 워크플로우를 로드하고 순차 실행"""

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
        return all(
            r.success or r.skipped for r in self.step_results
        )


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

    def _load(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

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
            action_result: ActionResult = self._actions.execute(
                action_name, resolved_args
            )
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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_orchestrator_engine.py -v`
Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add picko/orchestrator/engine.py tests/test_orchestrator_engine.py
git commit -m "feat(orchestrator): add WorkflowEngine with condition evaluation"
```

---

## Task 6: 기본 액션 등록 (collector.run, generator.run)

**Files:**
- Create: `picko/orchestrator/default_actions.py`
- Test: `tests/test_orchestrator_default_actions.py`

### Step 1: Write the failing test

```python
# tests/test_orchestrator_default_actions.py
"""기본 액션 래퍼 테스트"""

from unittest.mock import MagicMock, patch

from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import register_default_actions


class TestDefaultActions:
    def test_registers_expected_actions(self):
        registry = ActionRegistry()
        register_default_actions(registry)

        actions = registry.list_actions()
        assert "collector.run" in actions
        assert "generator.run" in actions

    @patch("picko.orchestrator.default_actions.DailyCollector")
    def test_collector_run_calls_daily_collector(self, MockCollector):
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"collected": 5}
        MockCollector.return_value = mock_instance

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "collector.run", {"account": "socialbuilders"}
        )

        assert result.success is True
        MockCollector.assert_called_once_with(
            account_id="socialbuilders", dry_run=False
        )
        mock_instance.run.assert_called_once()

    @patch("picko.orchestrator.default_actions.ContentGenerator")
    def test_generator_run_calls_content_generator(self, MockGenerator):
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"generated": 3}
        MockGenerator.return_value = mock_instance

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "generator.run", {"account": "socialbuilders", "type": "longform"}
        )

        assert result.success is True
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_orchestrator_default_actions.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: Write minimal implementation

```python
# picko/orchestrator/default_actions.py
"""기본 액션 등록 — 기존 스크립트를 액션으로 래핑"""

from picko.logger import get_logger
from picko.orchestrator.actions import ActionRegistry, ActionResult

logger = get_logger("orchestrator.default_actions")


def register_default_actions(registry: ActionRegistry):
    """기본 Picko 액션을 레지스트리에 등록"""
    registry.register("collector.run", _run_collector)
    registry.register("generator.run", _run_generator)


def _run_collector(
    account: str = "socialbuilders", dry_run: bool = False, **kwargs
) -> ActionResult:
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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_orchestrator_default_actions.py -v`
Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add picko/orchestrator/default_actions.py tests/test_orchestrator_default_actions.py
git commit -m "feat(orchestrator): add default action wrappers for collector and generator"
```

---

## Task 7: run_workflow CLI

**Files:**
- Create: `scripts/run_workflow.py`
- Test: `tests/test_run_workflow_cli.py`

### Step 1: Write the failing test

```python
# tests/test_run_workflow_cli.py
"""run_workflow CLI 테스트"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml


class TestRunWorkflowCLI:
    def _write_workflow(self, tmp_path, steps=None):
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        path = wf_dir / "test_pipeline.yml"
        workflow = {
            "name": "test_pipeline",
            "description": "test",
            "steps": steps or [],
        }
        path.write_text(yaml.dump(workflow), encoding="utf-8")
        return path

    @patch("scripts.run_workflow.WorkflowEngine")
    @patch("scripts.run_workflow.VaultAdapter")
    @patch("scripts.run_workflow.VaultIO")
    def test_main_runs_workflow(
        self, MockVaultIO, MockVaultAdapter, MockEngine, tmp_path
    ):
        from picko.orchestrator.engine import WorkflowResult

        mock_engine_instance = MagicMock()
        mock_engine_instance.run.return_value = WorkflowResult()
        MockEngine.return_value = mock_engine_instance

        workflow_path = self._write_workflow(tmp_path)

        from scripts.run_workflow import main

        main(["--workflow", str(workflow_path)])

        mock_engine_instance.run.assert_called_once()
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_run_workflow_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: Write minimal implementation

```python
# scripts/run_workflow.py
"""
워크플로우 실행 CLI

Usage:
    python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml
    python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml --dry-run
"""

import argparse
import sys
from pathlib import Path

from picko.logger import setup_logger
from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import register_default_actions
from picko.orchestrator.engine import WorkflowEngine
from picko.orchestrator.vault_adapter import VaultAdapter
from picko.vault_io import VaultIO

logger = setup_logger("run_workflow")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="워크플로우 실행")
    parser.add_argument(
        "--workflow", required=True, help="워크플로우 YAML 파일 경로"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="실제 실행 없이 조건만 평가"
    )

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
    result = engine.run(workflow_path)

    # 결과 출력
    for step_result in result.step_results:
        status = "SKIP" if step_result.skipped else (
            "OK" if step_result.success else "FAIL"
        )
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
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_run_workflow_cli.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add scripts/run_workflow.py tests/test_run_workflow_cli.py
git commit -m "feat(orchestrator): add run_workflow CLI entry point"
```

---

## Task 8: 샘플 워크플로우 YAML + 통합 테스트

**Files:**
- Create: `config/workflows/daily_pipeline.yml`
- Create: `config/workflows/approved_packs.yml`
- Create: `config/workflows/image_generation.yml`
- Test: `tests/test_orchestrator_integration.py`

### Step 1: Write sample workflow files

```yaml
# config/workflows/daily_pipeline.yml
name: daily_pipeline
description: 일일 콘텐츠 수집 → auto_ready 항목 longform 생성

steps:
  - name: collect
    action: collector.run
    args:
      account: socialbuilders

  - name: generate_longform
    action: generator.run
    args:
      account: socialbuilders
      type: longform
    condition: "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}"
```

```yaml
# config/workflows/approved_packs.yml
name: approved_packs
description: 승인된 longform → packs 생성

steps:
  - name: generate_packs
    action: generator.run
    args:
      account: socialbuilders
      type: packs
    condition: "${{ vault.count('Content/Longform', 'derivative_status=approved') > 0 }}"
```

```yaml
# config/workflows/image_generation.yml
name: image_generation
description: 승인된 콘텐츠 → 이미지 프롬프트 생성 → 렌더링

steps:
  - name: generate_image_prompts
    action: generator.run
    args:
      account: socialbuilders
      type: image
    condition: "${{ vault.count('Content/Longform', 'image_status=approved') > 0 }}"

  - name: render_media
    action: renderer.run
    args:
      status: pending
    condition: "${{ vault.count('Inbox/Multimedia', 'render_status=pending') > 0 }}"
```

### Step 2: Write integration test

```python
# tests/test_orchestrator_integration.py
"""오케스트레이션 통합 테스트 — 전체 파이프라인을 mock으로 검증"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import frontmatter
import yaml

from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.engine import WorkflowEngine
from picko.orchestrator.vault_adapter import VaultAdapter
from picko.vault_io import VaultIO


class TestOrchestratorIntegration:
    def _write_note(self, vault_dir, rel_path, metadata, content=""):
        full_path = vault_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content)
        post.metadata = metadata
        full_path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _write_workflow(self, tmp_path, steps):
        path = tmp_path / "workflow.yml"
        workflow = {"name": "test", "description": "test", "steps": steps}
        path.write_text(yaml.dump(workflow), encoding="utf-8")
        return path

    def test_condition_based_on_vault_state(self, temp_vault_dir, tmp_path):
        """Vault에 auto_ready 노트가 있을 때만 generator 실행"""
        # Vault에 노트 작성
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        # 액션 등록
        registry = ActionRegistry()
        call_log = []

        def mock_generator(**kwargs):
            call_log.append("generated")
            return ActionResult(success=True)

        registry.register("generator.run", mock_generator)

        # 워크플로우 실행
        workflow_path = self._write_workflow(tmp_path, [
            {
                "name": "generate",
                "action": "generator.run",
                "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
            },
        ])

        engine = WorkflowEngine(
            vault_adapter=adapter, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert result.success is True
        assert call_log == ["generated"]

    def test_condition_skips_when_no_matching_notes(
        self, temp_vault_dir, tmp_path
    ):
        """Vault에 조건에 맞는 노트가 없으면 step skip"""
        # Vault에 pending 노트만 있음
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "pending"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        registry = ActionRegistry()
        call_log = []

        def mock_generator(**kwargs):
            call_log.append("generated")
            return ActionResult(success=True)

        registry.register("generator.run", mock_generator)

        workflow_path = self._write_workflow(tmp_path, [
            {
                "name": "generate",
                "action": "generator.run",
                "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
            },
        ])

        engine = WorkflowEngine(
            vault_adapter=adapter, action_registry=registry
        )
        result = engine.run(workflow_path)

        assert result.success is True
        assert result.step_results[0].skipped is True
        assert call_log == []
```

### Step 3: Run test

Run: `pytest tests/test_orchestrator_integration.py -v`
Expected: PASS (2 tests)

### Step 4: Commit

```bash
git add config/workflows/daily_pipeline.yml config/workflows/approved_packs.yml config/workflows/image_generation.yml tests/test_orchestrator_integration.py
git commit -m "feat(orchestrator): add sample workflows and integration tests"
```

---

## Task 9: 전체 테스트 통과 확인 + 최종 커밋

**Files:** 없음 (검증만)

### Step 1: 전체 테스트 실행

Run: `pytest tests/test_vault_adapter.py tests/test_orchestrator_actions.py tests/test_orchestrator_expr.py tests/test_orchestrator_engine.py tests/test_orchestrator_default_actions.py tests/test_run_workflow_cli.py tests/test_orchestrator_integration.py -v`
Expected: ALL PASS

### Step 2: 기존 테스트 회귀 확인

Run: `pytest tests/ -v --ignore=tests/benchmarks -x`
Expected: 기존 테스트에 영향 없음

### Step 3: Lint 확인

Run: `black picko/orchestrator/ scripts/run_workflow.py tests/test_vault_adapter.py tests/test_orchestrator_*.py tests/test_run_workflow_cli.py`
Run: `isort picko/orchestrator/ scripts/run_workflow.py`

### Step 4: 최종 정리 커밋 (필요시)

```bash
git add -A
git commit -m "style: format orchestrator module"
```

---

## 파일 생성 요약

| 유형 | 파일 |
|------|------|
| 모듈 | `picko/orchestrator/__init__.py` |
| 모듈 | `picko/orchestrator/vault_adapter.py` |
| 모듈 | `picko/orchestrator/actions.py` |
| 모듈 | `picko/orchestrator/expr.py` |
| 모듈 | `picko/orchestrator/engine.py` |
| 모듈 | `picko/orchestrator/default_actions.py` |
| 스크립트 | `scripts/run_workflow.py` |
| 설정 | `config/workflows/daily_pipeline.yml` |
| 설정 | `config/workflows/approved_packs.yml` |
| 설정 | `config/workflows/image_generation.yml` |
| 테스트 | `tests/test_vault_adapter.py` |
| 테스트 | `tests/test_orchestrator_actions.py` |
| 테스트 | `tests/test_orchestrator_expr.py` |
| 테스트 | `tests/test_orchestrator_engine.py` |
| 테스트 | `tests/test_orchestrator_default_actions.py` |
| 테스트 | `tests/test_run_workflow_cli.py` |
| 테스트 | `tests/test_orchestrator_integration.py` |
