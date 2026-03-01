"""Workflow definition tests for agentic pipeline."""

from pathlib import Path

import yaml


def test_agentic_pipeline_workflow_exists():
    workflow_path = Path("config/workflows/agentic_pipeline.yml")
    assert workflow_path.exists()


def test_agentic_pipeline_has_quality_step():
    workflow_path = Path("config/workflows/agentic_pipeline.yml")
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])

    actions = [step.get("action") for step in steps]
    assert "quality.verify" in actions


def test_agentic_pipeline_uses_dynamic_steps():
    workflow_path = Path("config/workflows/agentic_pipeline.yml")
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])

    assert any("dynamic_steps" in step for step in steps)
