"""
Tests for Discovery Orchestrator.

Tests orchestration of platform adapters, human review gates,
and source registration.
"""

from unittest.mock import MagicMock

import pytest

from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate
from picko.discovery.gates import HumanConfirmationGate
from picko.discovery.orchestrator import SourceDiscoveryOrchestrator


@pytest.fixture
def mock_source_manager():
    """Create mock SourceManager for tests."""
    manager = MagicMock()
    manager.get_by_id.return_value = None
    return manager


class MockAdapter(BaseDiscoveryCollector):
    """Mock adapter for testing."""

    def __init__(
        self,
        platform: str,
        is_available_result: bool = True,
        search_results: list[SourceCandidate] | None = None,
        search_error: Exception | None = None,
    ):
        super().__init__(platform)
        self._is_available = is_available_result
        self._search_results = search_results or []
        self._search_error = search_error
        self._rate_limit_info = {"remaining": 100, "reset_time": None}

    async def search(self, keyword: str) -> list[SourceCandidate]:
        if self._search_error:
            raise self._search_error
        return self._search_results

    def is_available(self) -> bool:
        return self._is_available

    def get_rate_limit_info(self) -> dict:
        return self._rate_limit_info


def create_candidate(
    handle: str,
    platform: str,
    score: float = 0.8,
    url: str | None = None,
) -> SourceCandidate:
    """Helper to create SourceCandidate."""
    return SourceCandidate(
        handle=handle,
        platform=platform,
        url=url or f"https://{platform}.com/{handle}",
        relevance_score=score,
        discovered_keyword="test",
    )


class TestOrchestratorInit:
    """Orchestrator initialization tests."""

    def test_init_default(self, mock_source_manager):
        """Default initialization."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        assert orchestrator.adapters == []
        assert orchestrator.gate is not None
        assert orchestrator.source_manager is not None

    def test_init_with_adapters(self, mock_source_manager):
        """Initialize with adapters."""
        adapter1 = MockAdapter("reddit")
        adapter2 = MockAdapter("mastodon")

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[adapter1, adapter2],
            source_manager=mock_source_manager,
        )

        assert len(orchestrator.adapters) == 2
        assert orchestrator.adapters[0].platform == "reddit"
        assert orchestrator.adapters[1].platform == "mastodon"

    def test_init_with_custom_gate(self, mock_source_manager):
        """Initialize with custom gate."""
        gate = HumanConfirmationGate(auto_approve_threshold=0.95)
        orchestrator = SourceDiscoveryOrchestrator(
            gate=gate,
            source_manager=mock_source_manager,
        )

        assert orchestrator.gate.auto_approve_threshold == 0.95

    def test_add_adapter(self, mock_source_manager):
        """Add adapter after initialization."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)
        adapter = MockAdapter("reddit")

        orchestrator.add_adapter(adapter)

        assert len(orchestrator.adapters) == 1
        assert orchestrator.adapters[0].platform == "reddit"


class TestOrchestratorDiscover:
    """Orchestrator discover method tests."""

    @pytest.mark.asyncio
    async def test_discover_returns_candidates_from_all_adapters(self, mock_source_manager):
        """Discovery returns candidates from all available adapters."""
        reddit_candidates = [
            create_candidate("r_machinelearning", "reddit", 0.9),
            create_candidate("r_artificial", "reddit", 0.85),
        ]
        mastodon_candidates = [
            create_candidate("@ai_news@mastodon.social", "mastodon", 0.8),
        ]

        reddit_adapter = MockAdapter("reddit", search_results=reddit_candidates)
        mastodon_adapter = MockAdapter("mastodon", search_results=mastodon_candidates)

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[reddit_adapter, mastodon_adapter],
            source_manager=mock_source_manager,
        )

        results = await orchestrator.discover("AI")

        # Social platforms always require review
        assert len(results["pending"]) == 3
        assert len(results["approved"]) == 0

    @pytest.mark.asyncio
    async def test_discover_skips_unavailable_adapters(self, mock_source_manager):
        """Unavailable adapters are skipped."""
        available_adapter = MockAdapter(
            "reddit",
            is_available_result=True,
            search_results=[create_candidate("r_test", "reddit")],
        )
        unavailable_adapter = MockAdapter(
            "mastodon",
            is_available_result=False,
            search_results=[create_candidate("@test", "mastodon")],
        )

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[available_adapter, unavailable_adapter],
            source_manager=mock_source_manager,
        )

        results = await orchestrator.discover("test")

        # Only reddit adapter contributed
        assert len(results["pending"]) == 1
        assert results["pending"][0].platform == "reddit"

    @pytest.mark.asyncio
    async def test_discover_handles_adapter_errors(self, mock_source_manager):
        """Adapter errors are caught and logged."""
        working_adapter = MockAdapter("reddit", search_results=[create_candidate("r_test", "reddit")])
        failing_adapter = MockAdapter("mastodon", search_error=Exception("API error"))

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[working_adapter, failing_adapter],
            source_manager=mock_source_manager,
        )

        results = await orchestrator.discover("test")

        # Reddit should still work despite mastodon failure
        assert len(results["pending"]) == 1
        assert results["pending"][0].platform == "reddit"

    @pytest.mark.asyncio
    async def test_discover_with_auto_approve(self, mock_source_manager):
        """Auto-approve only works for non-social platforms with high relevance."""
        # Create a non-social platform candidate (web/rss type)
        # Using a trusted domain-like platform to test auto-approve
        candidates = [
            create_candidate(
                "techcrunch",
                "web",
                0.95,
                url="https://techcrunch.com/ai",
            ),  # High score, non-social
        ]

        # Create a custom gate that allows "techcrunch.com" as trusted
        gate = HumanConfirmationGate(trusted_domains={"techcrunch.com"})

        adapter = MockAdapter("web", search_results=candidates)
        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[adapter],
            source_manager=mock_source_manager,
            gate=gate,
        )

        # With auto_approve=True, high-score trusted domain goes to approved
        results = await orchestrator.discover("AI", auto_approve=True)

        # techcrunch.com is trusted + score 0.95 >= 0.9 -> auto-approved
        assert len(results["approved"]) == 1
        assert len(results["pending"]) == 0

    @pytest.mark.asyncio
    async def test_discover_returns_empty_for_no_adapters(self, mock_source_manager):
        """Empty results when no adapters configured."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        results = await orchestrator.discover("test")

        assert results["approved"] == []
        assert results["pending"] == []
        assert results["rejected"] == []

    @pytest.mark.asyncio
    async def test_discover_no_duplicates_across_adapters(self, mock_source_manager):
        """Same source from different adapters creates separate entries."""
        # Different platforms can have same handle
        reddit_candidates = [create_candidate("ai_news", "reddit", 0.9)]
        mastodon_candidates = [create_candidate("ai_news", "mastodon", 0.8)]

        reddit_adapter = MockAdapter("reddit", search_results=reddit_candidates)
        mastodon_adapter = MockAdapter("mastodon", search_results=mastodon_candidates)

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[reddit_adapter, mastodon_adapter],
            source_manager=mock_source_manager,
        )

        results = await orchestrator.discover("AI")

        # Both should be present (different platforms)
        assert len(results["pending"]) == 2


class TestOrchestratorRegisterSources:
    """Orchestrator register_approved_sources tests."""

    @pytest.mark.asyncio
    async def test_register_sources_creates_entries(self):
        """Register sources creates source manager entries."""
        candidates = [
            create_candidate("r_machinelearning", "reddit", 0.9),
        ]

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = None  # No existing source

        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        registered = await orchestrator.register_approved_sources(candidates)

        assert registered == 1
        mock_source_manager.add_candidate.assert_called_once()

        # Verify source data structure
        call_args = mock_source_manager.add_candidate.call_args
        source_meta = call_args[0][0]  # First positional argument (SourceMeta)
        assert source_meta.id == "reddit_r_machinelearning"
        assert source_meta.platform == "reddit"
        assert source_meta.auto_discovered is True
        assert source_meta.human_review_required is False

    @pytest.mark.asyncio
    async def test_register_sources_skips_existing(self):
        """Existing sources are skipped."""
        candidates = [
            create_candidate("r_machinelearning", "reddit", 0.9),
        ]

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = {"id": "existing"}  # Already exists

        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        registered = await orchestrator.register_approved_sources(candidates)

        assert registered == 0
        mock_source_manager.add_candidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_sources_with_enhanced_verification(self):
        """Enhanced verification is added to new sources."""
        candidates = [
            create_candidate("r_test", "reddit", 0.85),
        ]

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = None

        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        await orchestrator.register_approved_sources(
            candidates,
            enhanced_verification=True,
            collections_remaining=5,
        )

        call_args = mock_source_manager.add_candidate.call_args
        source_meta = call_args[0][0]
        assert source_meta.enhanced_verification is not None
        assert source_meta.enhanced_verification["enabled"] is True
        assert source_meta.enhanced_verification["collections_remaining"] == 5
        assert source_meta.enhanced_verification["elevated_threshold"] == 0.92

    @pytest.mark.asyncio
    async def test_register_sources_without_enhanced_verification(self):
        """Enhanced verification can be disabled."""
        candidates = [
            create_candidate("r_test", "reddit", 0.85),
        ]

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = None

        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        await orchestrator.register_approved_sources(
            candidates,
            enhanced_verification=False,
        )

        call_args = mock_source_manager.add_candidate.call_args
        source_meta = call_args[0][0]
        assert source_meta.enhanced_verification is None

    @pytest.mark.asyncio
    async def test_register_sources_handles_errors(self):
        """Registration errors are caught and logged."""
        candidates = [
            create_candidate("r_test", "reddit", 0.85),
        ]

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = None
        mock_source_manager.add_candidate.side_effect = Exception("DB error")

        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        # Should not raise
        registered = await orchestrator.register_approved_sources(candidates)

        assert registered == 0


class TestOrchestratorHelpers:
    """Orchestrator helper method tests."""

    def test_generate_source_id(self, mock_source_manager):
        """Source ID generation."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        candidate = create_candidate("@ai_news@mastodon.social", "mastodon")
        source_id = orchestrator._generate_source_id(candidate)

        assert source_id == "mastodon_ai_newsmastodon.social"

    def test_generate_source_id_removes_special_chars(self, mock_source_manager):
        """Source ID removes @ and /."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        candidate = create_candidate("@user/name", "reddit")
        source_id = orchestrator._generate_source_id(candidate)

        assert "@" not in source_id
        assert "/" not in source_id

    def test_get_api_provider(self, mock_source_manager):
        """API provider mapping."""
        orchestrator = SourceDiscoveryOrchestrator(source_manager=mock_source_manager)

        assert orchestrator._get_api_provider("reddit") == "reddit_api"
        assert orchestrator._get_api_provider("mastodon") == "mastodon_api"
        assert orchestrator._get_api_provider("threads") == "threads_api"
        assert orchestrator._get_api_provider("unknown") == "unknown_api"

    def test_get_adapter_status(self, mock_source_manager):
        """Adapter status reporting."""
        available = MockAdapter("reddit", is_available_result=True)
        unavailable = MockAdapter("mastodon", is_available_result=False)

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[available, unavailable],
            source_manager=mock_source_manager,
        )

        status = orchestrator.get_adapter_status()

        assert len(status) == 2
        assert status[0]["platform"] == "reddit"
        assert status[0]["available"] is True
        assert status[1]["platform"] == "mastodon"
        assert status[1]["available"] is False


class TestOrchestratorIntegration:
    """Integration tests for full discovery flow."""

    @pytest.mark.asyncio
    async def test_full_discovery_flow(self):
        """Complete discovery to registration flow."""
        # Setup adapters with candidates
        # Social platforms - always require review
        reddit_candidates = [
            create_candidate("r_machinelearning", "reddit", 0.92),
            create_candidate("r_artificial", "reddit", 0.88),
        ]
        mastodon_candidates = [
            create_candidate("@ai@mastodon.social", "mastodon", 0.75),
        ]

        reddit_adapter = MockAdapter("reddit", search_results=reddit_candidates)
        mastodon_adapter = MockAdapter("mastodon", search_results=mastodon_candidates)

        mock_source_manager = MagicMock()
        mock_source_manager.get_by_id.return_value = None

        orchestrator = SourceDiscoveryOrchestrator(
            adapters=[reddit_adapter, mastodon_adapter],
            source_manager=mock_source_manager,
        )

        # 1. Discover sources - social platforms always require review
        results = await orchestrator.discover("AI")

        # All 3 social platform candidates go to pending
        assert len(results["pending"]) == 3
        assert len(results["approved"]) == 0

        # 2. Even with auto_approve=True, social platforms still require review
        # because auto_approve_eligible is False for social platforms
        results_auto = await orchestrator.discover("AI", auto_approve=True)
        assert len(results_auto["pending"]) == 3
        assert len(results_auto["approved"]) == 0

        # 3. Register pending sources (they're still valid candidates, just need review)
        registered = await orchestrator.register_approved_sources(results["pending"])

        assert registered == 3
