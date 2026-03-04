# tests/test_orchestrator_default_actions.py
"""기본 액션 래퍼 테스트"""

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import _extract_item_id, register_default_actions


class TestDefaultActions:
    def test_registers_expected_actions(self):
        registry = ActionRegistry()
        register_default_actions(registry)

        actions = registry.list_actions()
        assert "collector.run" in actions
        assert "generator.run" in actions
        assert "renderer.run" in actions
        assert "publisher.run" in actions
        assert "engagement.sync" in actions
        assert "quality.verify" in actions

    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_calls_quality_graph(self, MockQualityGraph):
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "item_1",
            "final_verdict": "approved",
            "final_confidence": 0.93,
        }
        MockQualityGraph.return_value = mock_graph

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "item_1",
                "title": "Sample title",
                "content": "Sample content",
                "enhanced_verification": True,
                "thread_id": "thread-item-1",
            },
        )

        assert result.success is True
        assert result.outputs["result"]["final_verdict"] == "approved"
        mock_graph.verify.assert_called_once_with(
            item_id="item_1",
            title="Sample title",
            content="Sample content",
            enhanced_verification=True,
            thread_id="thread-item-1",
        )

    @patch("picko.source_manager.SourceManager")
    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_auto_enhanced_for_new_source(self, MockQualityGraph, MockSourceManager):
        """New source (auto_discovered && collected_count < 5) should auto-enable enhanced_verification."""
        # Setup mock source manager
        mock_source = MagicMock()
        mock_source.auto_discovered = True
        mock_source.collected_count = 2
        mock_source.enhanced_verification = {
            "enabled": True,
            "collections_remaining": 3,
        }

        mock_manager = MagicMock()
        mock_manager.get_by_id.return_value = mock_source
        MockSourceManager.return_value = mock_manager

        # Setup mock quality graph
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "item_1",
            "final_verdict": "approved",
            "final_confidence": 0.95,
        }
        MockQualityGraph.return_value = mock_graph

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "item_1",
                "source_id": "new_source_123",
                "title": "Test title",
                "content": "Test content",
            },
        )

        assert result.success is True
        # Verify enhanced_verification was auto-enabled
        mock_graph.verify.assert_called_once()
        call_kwargs = mock_graph.verify.call_args[1]
        assert call_kwargs["enhanced_verification"] is True

    @patch("picko.source_manager.SourceManager")
    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_no_auto_enhanced_for_established_source(self, MockQualityGraph, MockSourceManager):
        """Established source (collected_count >= 5) should not auto-enable enhanced_verification."""
        # Setup mock source manager
        mock_source = MagicMock()
        mock_source.auto_discovered = True
        mock_source.collected_count = 10  # Established source
        mock_source.enhanced_verification = None

        mock_manager = MagicMock()
        mock_manager.get_by_id.return_value = mock_source
        MockSourceManager.return_value = mock_manager

        # Setup mock quality graph
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "item_1",
            "final_verdict": "approved",
            "final_confidence": 0.95,
        }
        MockQualityGraph.return_value = mock_graph

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "item_1",
                "source_id": "established_source",
                "title": "Test title",
                "content": "Test content",
            },
        )

        assert result.success is True
        # Verify enhanced_verification was NOT auto-enabled
        mock_graph.verify.assert_called_once()
        call_kwargs = mock_graph.verify.call_args[1]
        assert call_kwargs["enhanced_verification"] is False

    @patch("picko.source_manager.SourceManager")
    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_decrements_collections_remaining(self, MockQualityGraph, MockSourceManager):
        """After verification, collections_remaining should be decremented."""
        # Setup mock source manager
        mock_source = MagicMock()
        mock_source.auto_discovered = True
        mock_source.collected_count = 2
        mock_source.enhanced_verification = {
            "enabled": True,
            "collections_remaining": 3,
        }

        mock_manager = MagicMock()
        mock_manager.get_by_id.return_value = mock_source
        MockSourceManager.return_value = mock_manager

        # Setup mock quality graph
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "item_1",
            "final_verdict": "approved",
            "final_confidence": 0.95,
        }
        MockQualityGraph.return_value = mock_graph

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "item_1",
                "source_id": "new_source_123",
                "title": "Test title",
                "content": "Test content",
            },
        )

        assert result.success is True
        # Verify update_stats was called to decrement collections_remaining
        mock_manager.update_stats.assert_called_once()
        call_args = mock_manager.update_stats.call_args
        assert call_args[0][0] == "new_source_123"  # source_id
        # Check that enhanced_verification was updated with decremented count
        update_kwargs = call_args[1]
        assert "enhanced_verification" in update_kwargs
        assert update_kwargs["enhanced_verification"]["collections_remaining"] == 2

    @patch("picko.vault_io.VaultIO")
    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_updates_frontmatter_quality_and_job_history(self, MockQualityGraph, MockVaultIO):
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "input_abc123",
            "primary_verdict": "approved",
            "primary_confidence": 0.91,
            "primary_scores": {"factual": 9},
            "primary_reasoning": "Looks good",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "final_verdict": "approved",
            "final_confidence": 0.93,
            "enhanced_verification": False,
        }
        MockQualityGraph.return_value = mock_graph

        mock_vault = MagicMock()
        mock_vault.read_note.return_value = ({"job_history": []}, "content")
        MockVaultIO.return_value = mock_vault

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "input_abc123",
                "title": "Sample title",
                "content": "Sample content",
                "dry_run": False,
            },
        )

        assert result.success is True
        mock_vault.update_frontmatter.assert_called_once()
        called_path = mock_vault.update_frontmatter.call_args[0][0]
        called_updates = mock_vault.update_frontmatter.call_args[0][1]
        assert called_path.endswith("Inbox/Inputs/input_abc123.md")
        assert called_updates["quality"]["final_verdict"] == "approved"
        assert called_updates["status"] == "approved"
        assert called_updates["job_history"][-1]["stage"] == "quality.verify"

    @patch("picko.notification.bot.HumanReviewBot")
    @patch("picko.vault_io.VaultIO")
    @patch("picko.quality.graph.QualityGraph")
    def test_quality_verify_needs_review_notifies_and_preserves_pending(
        self, MockQualityGraph, MockVaultIO, MockHumanReviewBot
    ):
        mock_graph = MagicMock()
        mock_graph.verify.return_value = {
            "item_id": "input_pending1",
            "primary_verdict": "needs_review",
            "primary_confidence": 0.74,
            "primary_scores": {},
            "primary_reasoning": "uncertain facts",
            "primary_flags": ["fact_check_needed"],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "final_verdict": "needs_review",
            "final_confidence": 0.74,
            "enhanced_verification": False,
        }
        MockQualityGraph.return_value = mock_graph

        mock_vault = MagicMock()
        mock_vault.read_note.return_value = (
            {"status": "pending", "job_history": []},
            "content",
        )
        MockVaultIO.return_value = mock_vault

        mock_bot = MagicMock()
        mock_bot.is_configured.return_value = True
        mock_bot.notify_quality_review = AsyncMock(return_value=True)
        MockHumanReviewBot.return_value = mock_bot

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "quality.verify",
            {
                "item_id": "input_pending1",
                "title": "Needs review title",
                "content": "Needs review content",
                "dry_run": False,
            },
        )

        assert result.success is True
        called_updates = mock_vault.update_frontmatter.call_args[0][1]
        assert called_updates["status"] == "pending"
        mock_bot.notify_quality_review.assert_awaited_once()

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
        self,
        mock_write,
        mock_mkdir,
        mock_exists,
        mock_get_pending,
        mock_parse,
        mock_renderer_class,
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

    @patch("picko.orchestrator.vault_adapter.VaultAdapter")
    @patch("picko.vault_io.VaultIO")
    def test_publisher_run_dry_run_returns_pending_count(self, MockVaultIO, MockVaultAdapter):
        mock_vault = MagicMock()
        MockVaultIO.return_value = mock_vault

        mock_adapter = MagicMock()
        mock_adapter.list.return_value = [MagicMock()]
        MockVaultAdapter.return_value = mock_adapter

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "publisher.run",
            {
                "dry_run": True,
                "source_path": "Content/Packs/twitter",
                "filter": "derivative_status=approved",
            },
        )

        assert result.success is True
        assert result.outputs["dry_run"] is True
        assert result.outputs["pending_count"] == 1
        assert result.outputs["published_count"] == 0

    @patch("picko.publisher.TwitterPublisher")
    @patch("picko.orchestrator.vault_adapter.VaultAdapter")
    @patch("picko.vault_io.VaultIO")
    def test_publisher_run_updates_frontmatter_with_status_and_timestamp(
        self, MockVaultIO, MockVaultAdapter, MockTwitterPublisher
    ):
        mock_vault = MagicMock()
        mock_vault.root = Path("/vault")
        mock_vault.read_note.return_value = ({"tweet_text": "hello"}, "hello")
        MockVaultIO.return_value = mock_vault

        note_path = Path("/vault/Content/Packs/twitter/note1.md")
        mock_adapter = MagicMock()
        mock_adapter.list.return_value = [note_path]
        MockVaultAdapter.return_value = mock_adapter

        mock_publish_result = MagicMock()
        mock_publish_result.success = True
        mock_publish_result.tweet_id = "123"
        mock_publish_result.tweet_url = "https://twitter.com/example/status/123"
        mock_publish_result.error = None

        mock_publisher = MagicMock()
        mock_publisher.publish.return_value = mock_publish_result
        MockTwitterPublisher.return_value = mock_publisher

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "publisher.run",
            {
                "update_content_status_to": "published",
                "dry_run": False,
                "publish_platform": "twitter",
            },
        )

        assert result.success is True
        mock_vault.update_frontmatter.assert_called_once_with(
            note_path,
            {
                "status": "published",
                "published_at": ANY,
            },
        )

    def test_publisher_run_fails_on_unsupported_platform(self):
        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "publisher.run",
            {
                "publish_platform": "instagram",
            },
        )

        assert result.success is False
        assert "instagram" in result.error

    def test_extract_item_id_handles_path_string_dict_and_empty(self):
        assert _extract_item_id(Path("/vault/Inbox/note1.md")) == "note1"
        assert _extract_item_id("Inbox/note2.md") == "note2"
        assert _extract_item_id("plain-id") == "plain-id"
        assert _extract_item_id({"id": "abc"}) == "abc"
        assert _extract_item_id({"path": Path("/vault/foo.md")}) == "foo"
        assert _extract_item_id({}) == ""

    @patch("scripts.engagement_sync.EngagementSyncer")
    def test_engagement_sync_accepts_known_optional_args(self, MockSyncer):
        mock_syncer = MagicMock()
        mock_syncer.sync_all.return_value = []
        MockSyncer.return_value = mock_syncer

        registry = ActionRegistry()
        register_default_actions(registry)

        result = registry.execute(
            "engagement.sync",
            {
                "platforms": "twitter",
                "days": 1,
                "delay_minutes": 30,
                "only_recently_published": True,
                "dry_run": True,
            },
        )

        assert result.success is True
