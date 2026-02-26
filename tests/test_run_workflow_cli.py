# tests/test_run_workflow_cli.py
"""run_workflow CLI 테스트"""

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
    def test_main_runs_workflow(self, MockVaultIO, MockVaultAdapter, MockEngine, tmp_path):
        from picko.orchestrator.engine import WorkflowResult

        mock_engine_instance = MagicMock()
        mock_engine_instance.run.return_value = WorkflowResult()
        MockEngine.return_value = mock_engine_instance

        workflow_path = self._write_workflow(tmp_path)

        from scripts.run_workflow import main

        main(["--workflow", str(workflow_path)])

        mock_engine_instance.run.assert_called_once()
