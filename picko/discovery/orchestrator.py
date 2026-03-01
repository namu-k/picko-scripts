"""
Discovery Orchestrator for source discovery.

Coordinates multiple platform adapters and applies human review gates.
"""

from pathlib import Path
from typing import Any

from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate
from picko.discovery.gates import HumanConfirmationGate
from picko.logger import get_logger
from picko.source_manager import SourceManager, SourceMeta

logger = get_logger("discovery.orchestrator")


class SourceDiscoveryOrchestrator:
    """
    Orchestrates source discovery across multiple platforms.

    Coordinates adapters, applies human review gates, and manages
    source registration.
    """

    source_manager: SourceManager | None

    def __init__(
        self,
        adapters: list[BaseDiscoveryCollector] | None = None,
        gate: HumanConfirmationGate | None = None,
        source_manager: SourceManager | None = None,
        sources_path: str | Path | None = None,
    ):
        """
        Initialize Discovery Orchestrator.

        Args:
            adapters: List of platform adapters
            gate: Human confirmation gate (creates default if not provided)
            source_manager: Source manager for registering new sources
            sources_path: Path to sources.yml (required if source_manager not provided)
        """
        self.adapters = adapters or []
        self.gate = gate or HumanConfirmationGate()

        if source_manager:
            self.source_manager = source_manager
        elif sources_path:
            self.source_manager = SourceManager(Path(sources_path))
        else:
            # No source manager - registration will be disabled
            self.source_manager = None

        logger.info(f"Discovery orchestrator initialized: {len(self.adapters)} adapters")

    def add_adapter(self, adapter: BaseDiscoveryCollector) -> None:
        """Add a platform adapter."""
        self.adapters.append(adapter)
        logger.debug(f"Added adapter for platform: {adapter.platform}")

    async def discover(
        self,
        keyword: str,
        auto_approve: bool = False,
    ) -> dict[str, list[SourceCandidate]]:
        """
        Run discovery across all configured adapters.

        Args:
            keyword: Search keyword
            auto_approve: If True, auto-approve sources that would otherwise need review
                          (only for sources where gate.auto_approve_eligible is True)

        Returns:
            Dict with 'approved', 'pending', 'rejected' lists
        """
        results: dict[str, list[SourceCandidate]] = {
            "approved": [],
            "pending": [],
            "rejected": [],
        }

        if not self.adapters:
            logger.warning("No discovery adapters configured")
            return results

        for adapter in self.adapters:
            # Safely check adapter availability
            try:
                available = adapter.is_available()
            except Exception as e:
                logger.warning(f"Adapter {adapter.platform} is_available() raised: {e}")
                continue

            if not available:
                logger.debug(f"Skipping {adapter.platform}: not available")
                continue

            try:
                candidates = await adapter.search(keyword)

                # Validate candidates is iterable
                if not candidates:
                    continue
                if not isinstance(candidates, (list, tuple)):
                    logger.warning(
                        f"Adapter {adapter.platform} returned non-iterable: {type(candidates)}"
                    )  # mypy can't figure out unreachable
                    continue

                for candidate in candidates:
                    # Use full gate evaluation to distinguish auto-reject vs auto-approve
                    decision = self.gate.evaluate(
                        platform=candidate.platform,
                        domain=None,  # Social platforms don't have domains
                        relevance_score=candidate.relevance_score,
                        metadata=candidate.metadata,
                    )

                    if decision.requires_review:
                        # Source needs human review
                        if auto_approve and decision.auto_approve_eligible:
                            # Override: auto-approve eligible sources when flag set
                            results["approved"].append(candidate)
                            logger.info(
                                f"Source auto-approved (override): {candidate.handle} " f"({candidate.platform})"
                            )
                        else:
                            results["pending"].append(candidate)
                            logger.info(
                                f"Source pending review: {candidate.handle} "
                                f"({candidate.platform}) - {decision.reason}"
                            )
                    else:
                        # No review required - could be auto-approve or auto-reject
                        if decision.auto_approve_eligible:
                            results["approved"].append(candidate)
                            logger.info(
                                f"Source auto-approved: {candidate.handle} "
                                f"({candidate.platform}) - {decision.reason}"
                            )
                        else:
                            # Auto-reject (e.g., low score)
                            results["rejected"].append(candidate)
                            logger.info(
                                f"Source rejected: {candidate.handle} " f"({candidate.platform}) - {decision.reason}"
                            )

            except Exception as e:
                logger.error(f"Discovery failed for {adapter.platform}: {e}")

        # Log summary
        logger.info(
            f"Discovery complete for '{keyword}': "
            f"{len(results['approved'])} approved, "
            f"{len(results['pending'])} pending, "
            f"{len(results['rejected'])} rejected"
        )

        return results

    async def register_approved_sources(
        self,
        candidates: list[SourceCandidate],
        enhanced_verification: bool = True,
        collections_remaining: int = 5,
    ) -> int:
        """
        Register approved sources to source manager.

        Args:
            candidates: List of approved candidates
            enhanced_verification: Enable enhanced verification mode
            collections_remaining: Number of collections before normal verification

        Returns:
            Number of sources registered
        """
        if not self.source_manager:
            logger.warning("No source manager configured - skipping registration")
            return 0

        registered = 0

        for candidate in candidates:
            try:
                source_id = self._generate_source_id(candidate)

                # Check if source already exists
                existing = self.source_manager.get_by_id(source_id)
                if existing:
                    logger.debug(f"Source already exists: {source_id}")
                    continue

                # Create SourceMeta from candidate
                source_meta = SourceMeta(
                    id=source_id,
                    type="social",
                    url=candidate.url,
                    category="discovered",
                    enabled=True,
                    status="active",
                    auto_discovered=True,
                    discovered_at=candidate.discovered_at.strftime("%Y-%m-%d"),
                    discovered_by="discovery_orchestrator",
                    discovery_keyword=candidate.discovered_keyword,
                    quality_score=candidate.relevance_score,
                    platform=candidate.platform,
                    human_review_required=False,  # Already approved
                    api_provider=self._get_api_provider(candidate.platform),
                    account_handle=candidate.handle,
                    last_api_sync=candidate.discovered_at.strftime("%Y-%m-%d"),
                )

                # Add enhanced verification for new sources
                if enhanced_verification:
                    source_meta.enhanced_verification = {
                        "enabled": True,
                        "collections_remaining": collections_remaining,
                        "elevated_threshold": 0.92,
                    }

                self.source_manager.add_candidate(source_meta, status="active")
                registered += 1

                logger.info(f"Registered source: {source_id}")

            except Exception as e:
                logger.error(f"Failed to register source: {e}")

        return registered

    def _generate_source_id(self, candidate: SourceCandidate) -> str:
        """Generate unique source ID from candidate."""
        # Format: platform_handle (e.g., reddit_machinelearning)
        handle_clean = candidate.handle.replace("@", "").replace("/", "_")
        return f"{candidate.platform}_{handle_clean}"

    def _get_api_provider(self, platform: str) -> str:
        """Get API provider name for platform."""
        # Normalize platform to lowercase for consistent mapping
        platform_lower = platform.lower()
        mapping = {
            "reddit": "reddit_api",
            "mastodon": "mastodon_api",
            "threads": "threads_api",
        }
        return mapping.get(platform_lower, f"{platform_lower}_api")

    def get_adapter_status(self) -> list[dict[str, Any]]:
        """Get status of all adapters."""
        return [
            {
                "platform": adapter.platform,
                "available": adapter.is_available(),
                "rate_limit": adapter.get_rate_limit_info(),
            }
            for adapter in self.adapters
        ]
