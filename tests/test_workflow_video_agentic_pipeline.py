"""Workflow definition tests for video agentic pipeline."""

from pathlib import Path

import yaml


def test_video_agentic_pipeline_workflow_exists():
    workflow_path = Path("config/workflows/video_agentic_pipeline.yml")
    assert workflow_path.exists()


def test_video_agentic_pipeline_has_final_evaluator_step():
    workflow_path = Path("config/workflows/video_agentic_pipeline.yml")
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])

    actions = [step.get("action") for step in steps]
    assert "video.plan.generate" in actions
    assert "video.evaluate.final" in actions
