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

    @patch("scripts.daily_collector.DailyCollector")
    def test_collector_run_calls_daily_collector(self, MockCollector):
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"collected": 5}
        MockCollector.return_value = mock_instance

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute("collector.run", {"account": "socialbuilders"})

        assert result.success is True
        MockCollector.assert_called_once_with(account_id="socialbuilders", dry_run=False)
        mock_instance.run.assert_called_once()

    @patch("scripts.generate_content.ContentGenerator")
    def test_generator_run_calls_content_generator(self, MockGenerator):
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"generated": 3}
        MockGenerator.return_value = mock_instance

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute("generator.run", {"account": "socialbuilders", "type": "longform"})

        assert result.success is True
