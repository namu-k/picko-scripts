# tests/test_orchestrator_engine.py
"""WorkflowEngine 테스트"""

import yaml

from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.engine import WorkflowEngine


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

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {"name": "step1", "action": "test.run", "args": {"x": 1}},
            ],
        )

        engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
        result = engine.run(workflow_path)

        assert len(result.step_results) == 1
        assert result.step_results[0].success is True
        assert call_log == [{"x": 1, "dry_run": False}]

    def test_condition_false_skips_step(self, tmp_path):
        registry = ActionRegistry()
        call_log = []

        def mock_action(**kwargs):
            call_log.append(True)
            return ActionResult(success=True)

        registry.register("test.run", mock_action)

        # vault.count() 가 0 반환 → condition false → skip
        mock_vault = type(
            "V",
            (),
            {
                "count": lambda self, p, f: 0,
            },
        )()

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "step1",
                    "action": "test.run",
                    "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
                },
            ],
        )

        engine = WorkflowEngine(vault_adapter=mock_vault, action_registry=registry)
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

        mock_vault = type(
            "V",
            (),
            {
                "count": lambda self, p, f: 5,
            },
        )()

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "step1",
                    "action": "test.run",
                    "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
                },
            ],
        )

        engine = WorkflowEngine(vault_adapter=mock_vault, action_registry=registry)
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

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {"name": "first", "action": "a.run"},
                {"name": "second", "action": "b.run"},
            ],
        )

        engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
        result = engine.run(workflow_path)

        assert order == ["a", "b"]
        assert len(result.step_results) == 2
        assert all(r.success for r in result.step_results)

    def test_dynamic_steps_execute_when_condition_true(self, tmp_path):
        registry = ActionRegistry()
        calls: list[str] = []

        def base_action(**kwargs):
            calls.append("base")
            return ActionResult(success=True, outputs={"ok": True})

        def dynamic_action(**kwargs):
            calls.append("dynamic")
            return ActionResult(success=True, outputs={"ran": True})

        registry.register("base.run", base_action)
        registry.register("dynamic.run", dynamic_action)

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "base_step",
                    "action": "base.run",
                    "dynamic_steps": [
                        {
                            "name": "dyn_step",
                            "action": "dynamic.run",
                            "condition": "${{ steps.base_step.outputs.ok }}",
                        }
                    ],
                }
            ],
        )

        engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
        result = engine.run(workflow_path)

        assert [r.name for r in result.step_results] == ["base_step", "dyn_step"]
        assert calls == ["base", "dynamic"]

    def test_dynamic_steps_skip_when_condition_false(self, tmp_path):
        registry = ActionRegistry()
        calls: list[str] = []

        def base_action(**kwargs):
            calls.append("base")
            return ActionResult(success=True)

        def dynamic_action(**kwargs):
            calls.append("dynamic")
            return ActionResult(success=True)

        registry.register("base.run", base_action)
        registry.register("dynamic.run", dynamic_action)

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "base_step",
                    "action": "base.run",
                    "dynamic_steps": [
                        {
                            "name": "dyn_step",
                            "action": "dynamic.run",
                            "condition": "${{ steps.base_step.outputs.missing }}",
                        }
                    ],
                }
            ],
        )

        engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
        result = engine.run(workflow_path)

        assert [r.name for r in result.step_results] == ["base_step", "dyn_step"]
        assert result.step_results[1].skipped is True
        assert calls == ["base"]
