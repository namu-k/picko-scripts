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
