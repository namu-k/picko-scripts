# tests/test_orchestrator_integration.py
"""오케스트레이션 통합 테스트 — 전체 파이프라인을 mock으로 검증"""

from unittest.mock import MagicMock, patch

import frontmatter
import yaml

from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.default_actions import register_default_actions
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
        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "generate",
                    "action": "generator.run",
                    "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
                },
            ],
        )

        engine = WorkflowEngine(vault_adapter=adapter, action_registry=registry)
        result = engine.run(workflow_path)

        assert result.success is True
        assert call_log == ["generated"]

    def test_condition_skips_when_no_matching_notes(self, temp_vault_dir, tmp_path):
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

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "generate",
                    "action": "generator.run",
                    "condition": "${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}",
                },
            ],
        )

        engine = WorkflowEngine(vault_adapter=adapter, action_registry=registry)
        result = engine.run(workflow_path)

        assert result.success is True
        assert result.step_results[0].skipped is True
        assert call_log == []

    @patch("scripts.generate_content.ContentGenerator")
    def test_batch_source_path_items_are_converted_to_stem_ids(self, MockGenerator, temp_vault_dir, tmp_path):
        self._write_note(
            temp_vault_dir,
            "Content/Longform/article1.md",
            {"derivative_status": "approved"},
            "sample",
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        registry = ActionRegistry()
        register_default_actions(registry)

        call_log = []
        mock_generator_instance = MagicMock()

        def _mock_run(**kwargs):
            call_log.append(kwargs.get("items", []))
            return {"approved_items": len(kwargs.get("items", []))}

        mock_generator_instance.run.side_effect = _mock_run
        MockGenerator.return_value = mock_generator_instance

        workflow_path = self._write_workflow(
            tmp_path,
            [
                {
                    "name": "generate_packs",
                    "action": "generator.run",
                    "args": {"account": "socialbuilders", "type": "packs"},
                    "condition": "${{ vault.count('Content/Longform', 'derivative_status=approved') > 0 }}",
                    "batch": {
                        "source": "${{ vault.list('Content/Longform', 'derivative_status=approved') }}",
                        "size": 5,
                        "delay": "0s",
                    },
                },
            ],
        )

        engine = WorkflowEngine(vault_adapter=adapter, action_registry=registry)
        result = engine.run(workflow_path)

        assert result.success is True
        assert call_log
        assert "article1" in call_log[0]
