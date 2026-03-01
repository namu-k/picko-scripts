"""End-to-end tests for agentic pipeline workflows."""

from pathlib import Path

import yaml

from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.engine import WorkflowEngine


def _write_workflow(tmp_path: Path, steps: list[dict[str, object]]) -> Path:
    workflow = {
        "name": "agentic_test",
        "description": "e2e",
        "steps": steps,
    }
    path = tmp_path / "agentic.yml"
    path.write_text(yaml.dump(workflow), encoding="utf-8")
    return path


def test_e2e_fallback_on_fetcher_failure(tmp_path):
    registry = ActionRegistry()
    calls: list[str] = []

    def failing_fetch(**kwargs):
        calls.append("primary")
        return ActionResult(success=False, error="fetch failed")

    def backup_fetch(**kwargs):
        calls.append("fallback")
        return ActionResult(success=True, outputs={"items": [{"id": "x1"}]})

    registry.register("fetch.primary", failing_fetch)
    registry.register("fetch.backup", backup_fetch)

    workflow_path = _write_workflow(
        tmp_path,
        [
            {
                "name": "discover",
                "action": "fetch.primary",
                "fallback": {"action": "fetch.backup"},
            }
        ],
    )

    engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
    result = engine.run(workflow_path)

    assert calls == ["primary", "fallback"]
    assert result.step_results[0].success is True
    assert result.step_results[0].outputs["items"][0]["id"] == "x1"


def test_e2e_low_confidence_routes_to_pending(tmp_path):
    registry = ActionRegistry()

    def collect(**kwargs):
        return ActionResult(success=True, outputs={"items": [{"id": "item_1", "text": "low"}]})

    def quality_verify(**kwargs):
        return ActionResult(
            success=True,
            outputs={
                "verified": [],
                "pending": ["item_1"],
                "rejected": [],
                "results": [],
            },
        )

    def generator(**kwargs):
        return ActionResult(success=True, outputs={"generated": 1})

    registry.register("collector.run", collect)
    registry.register("quality.verify", quality_verify)
    registry.register("generator.run", generator)

    workflow_path = _write_workflow(
        tmp_path,
        [
            {"name": "collect", "action": "collector.run"},
            {
                "name": "quality",
                "action": "quality.verify",
                "args": {"items": "${{ steps.collect.outputs.items }}"},
                "dynamic_steps": [
                    {
                        "name": "generate",
                        "action": "generator.run",
                        "condition": "${{ steps.quality.outputs.verified }}",
                    }
                ],
            },
        ],
    )

    engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
    result = engine.run(workflow_path)

    assert result.step_results[0].name == "collect"
    assert result.step_results[1].name == "quality"
    assert result.step_results[2].name == "generate"
    assert result.step_results[2].skipped is True
    assert result.step_results[1].outputs["pending"] == ["item_1"]


def test_e2e_high_confidence_auto_approve(tmp_path):
    registry = ActionRegistry()

    def collect(**kwargs):
        return ActionResult(success=True, outputs={"items": [{"id": "item_1", "text": "high"}]})

    def quality_verify(**kwargs):
        return ActionResult(
            success=True,
            outputs={
                "verified": ["item_1"],
                "pending": [],
                "rejected": [],
                "results": [],
            },
        )

    def generator(**kwargs):
        return ActionResult(success=True, outputs={"generated": 1})

    registry.register("collector.run", collect)
    registry.register("quality.verify", quality_verify)
    registry.register("generator.run", generator)

    workflow_path = _write_workflow(
        tmp_path,
        [
            {"name": "collect", "action": "collector.run"},
            {
                "name": "quality",
                "action": "quality.verify",
                "args": {"items": "${{ steps.collect.outputs.items }}"},
                "dynamic_steps": [
                    {
                        "name": "generate",
                        "action": "generator.run",
                        "condition": "${{ steps.quality.outputs.verified }}",
                    }
                ],
            },
        ],
    )

    engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
    result = engine.run(workflow_path)

    assert result.step_results[2].name == "generate"
    assert result.step_results[2].success is True
    assert result.step_results[1].outputs["verified"] == ["item_1"]


def test_e2e_enhanced_verification_mode(tmp_path):
    registry = ActionRegistry()
    observed: dict[str, object] = {}

    def quality_verify(**kwargs):
        observed["enhanced_verification"] = kwargs.get("enhanced_verification")
        return ActionResult(
            success=True,
            outputs={"verified": ["item_1"], "pending": [], "rejected": []},
        )

    registry.register("quality.verify", quality_verify)

    workflow_path = _write_workflow(
        tmp_path,
        [
            {
                "name": "quality",
                "action": "quality.verify",
                "args": {
                    "item_id": "item_1",
                    "title": "new source post",
                    "content": "content",
                    "enhanced_verification": True,
                },
            }
        ],
    )

    engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
    result = engine.run(workflow_path)

    assert result.step_results[0].success is True
    assert observed["enhanced_verification"] is True


def test_e2e_checkpoint_thread_id_passed(tmp_path):
    registry = ActionRegistry()
    observed: dict[str, object] = {}

    def quality_verify(**kwargs):
        observed["thread_id"] = kwargs.get("thread_id")
        return ActionResult(success=True, outputs={"result": {"item_id": "item_1"}})

    registry.register("quality.verify", quality_verify)

    workflow_path = _write_workflow(
        tmp_path,
        [
            {
                "name": "quality",
                "action": "quality.verify",
                "args": {
                    "item_id": "item_1",
                    "title": "title",
                    "content": "content",
                    "thread_id": "quality-thread-item-1",
                },
            }
        ],
    )

    engine = WorkflowEngine(vault_adapter=None, action_registry=registry)
    result = engine.run(workflow_path)

    assert result.step_results[0].success is True
    assert observed["thread_id"] == "quality-thread-item-1"
