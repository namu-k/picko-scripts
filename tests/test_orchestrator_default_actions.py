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
        assert "renderer.run" in actions

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

    @patch("scripts.render_media.get_pending_proposals")
    def test_renderer_run_no_pending(self, mock_get_pending):
        mock_get_pending.return_value = []

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute("renderer.run", {"status": "pending"})

        assert result.success is True
        assert result.outputs["rendered"] == 0

    @patch("picko.templates.ImageRenderer")
    @patch("picko.multimedia_io.parse_multimedia_input")
    @patch("scripts.render_media.get_pending_proposals")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.write_text")
    def test_renderer_run_with_pending(
        self, mock_write, mock_mkdir, mock_exists, mock_get_pending, mock_parse, mock_renderer_class
    ):
        # Setup mock data
        mock_get_pending.return_value = [{"id": "test_001", "status": "pending"}]
        mock_exists.return_value = True  # 파일이 존재한다고 가정

        mock_input = MagicMock()
        mock_input.concept = "Test Concept"
        mock_input.overlay_text = "Test Quote"
        mock_input.channels = ["instagram"]
        mock_input.account = "socialbuilders"
        mock_parse.return_value = mock_input

        mock_renderer = MagicMock()
        mock_renderer.render_image.return_value = "<html>test</html>"
        mock_renderer_class.return_value = mock_renderer

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute("renderer.run", {"status": "pending", "dry_run": False})

        assert result.success is True
        assert result.outputs["rendered"] == 1
