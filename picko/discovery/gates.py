"""
Human Confirmation Gate for source discovery

Determines whether human review is required for discovered sources.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from picko.logger import get_logger

logger = get_logger("discovery.gates")


class PlatformType(Enum):
    """플랫폼 타입"""

    # 소셜 미디어 (항상 사람 검토)
    THREADS = "threads"
    REDDIT = "reddit"
    MASTODON = "mastodon"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    BLUESKY = "bluesky"

    # RSS/웹 (조건부 자동 승인 가능)
    RSS = "rss"
    WEB = "web"
    NEWSLETTER = "newsletter"


@dataclass
class GateDecision:
    """Gate 결정 결과"""

    requires_review: bool
    reason: str
    auto_approve_eligible: bool = False


# 소셜 플랫폼 목록 (항상 사람 검토 필요)
SOCIAL_PLATFORMS = {
    PlatformType.THREADS,
    PlatformType.REDDIT,
    PlatformType.MASTODON,
    PlatformType.INSTAGRAM,
    PlatformType.FACEBOOK,
    PlatformType.LINKEDIN,
    PlatformType.TWITTER,
    PlatformType.BLUESKY,
}

# 신뢰 도메인 목록 (높은 점수 시 자동 승인 가능)
TRUSTED_DOMAINS = {
    # 메이저 뉴스
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com",
    "venturebeat.com",
    "engadget.com",
    # AI 특화
    "openai.com",
    "deepmind.com",
    "anthropic.com",
    "huggingface.co",
    # 학술/연구
    "arxiv.org",
    "nature.com",
    "science.org",
}

# 자동 승인 임계값
AUTO_APPROVE_THRESHOLD = 0.9
AUTO_REJECT_THRESHOLD = 0.3


class HumanConfirmationGate:
    """
    사람 검토 필요 여부 판단

    규칙:
    1. 소셜 플랫폼 (Threads, Reddit, Mastodon 등): 항상 사람 검토
    2. 신뢰 도메인 RSS + 높은 점수 (>= 0.9): 자동 승인 가능
    3. 그 외: 사람 검토
    """

    def __init__(
        self,
        trusted_domains: set[str] | None = None,
        auto_approve_threshold: float = AUTO_APPROVE_THRESHOLD,
        auto_reject_threshold: float = AUTO_REJECT_THRESHOLD,
    ):
        """
        Initialize HumanConfirmationGate

        Args:
            trusted_domains: 신뢰 도메인 목록 (기본값 사용 시 None)
            auto_approve_threshold: 자동 승인 임계값
            auto_reject_threshold: 자동 거절 임계값
        """
        self.trusted_domains = trusted_domains or TRUSTED_DOMAINS
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_reject_threshold = auto_reject_threshold

        logger.info(
            f"HumanConfirmationGate initialized: "
            f"trusted_domains={len(self.trusted_domains)}, "
            f"auto_approve>={self.auto_approve_threshold}"
        )

    def requires_review(
        self,
        platform: str | PlatformType,
        domain: str | None = None,
        relevance_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        사람 검토 필요 여부 판단

        Args:
            platform: 플랫폼 (문자열 또는 PlatformType)
            domain: 도메인 (RSS/웹 소스용)
            relevance_score: 관련도 점수 (0.0-1.0)
            metadata: 추가 메타데이터

        Returns:
            사람 검토 필요 여부
        """
        decision = self.evaluate(platform, domain, relevance_score, metadata)
        return decision.requires_review

    def evaluate(
        self,
        platform: str | PlatformType,
        domain: str | None = None,
        relevance_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> GateDecision:
        """
        상세 평가 결과 반환

        Args:
            platform: 플랫폼 (문자열 또는 PlatformType)
            domain: 도메인 (RSS/웹 소스용)
            relevance_score: 관련도 점수 (0.0-1.0)
            metadata: 추가 메타데이터

        Returns:
            GateDecision 객체
        """
        # PlatformType 변환
        platform_type = self._normalize_platform(platform)

        # 1. 소셜 플랫폼: 항상 사람 검토
        if platform_type in SOCIAL_PLATFORMS:
            logger.debug(f"Social platform requires review: {platform_type.value}")
            return GateDecision(
                requires_review=True,
                reason=f"Social platform ({platform_type.value}) always requires human review",
                auto_approve_eligible=False,
            )

        # 2. 매우 낮은 점수: 자동 거절 (검토 없이)
        if relevance_score <= self.auto_reject_threshold:
            logger.debug(f"Low score auto-reject: {relevance_score}")
            return GateDecision(
                requires_review=False,
                reason=f"Score too low ({relevance_score:.2f} <= {self.auto_reject_threshold})",
                auto_approve_eligible=False,
            )

        # 3. 신뢰 도메인 + 높은 점수: 자동 승인 가능
        if domain and self._is_trusted_domain(domain):
            if relevance_score >= self.auto_approve_threshold:
                logger.debug(f"Trusted domain + high score auto-approve: {domain}, {relevance_score}")
                return GateDecision(
                    requires_review=False,
                    reason=f"Trusted domain ({domain}) with high score ({relevance_score:.2f})",
                    auto_approve_eligible=True,
                )

        # 4. 그 외: 사람 검토
        return GateDecision(
            requires_review=True,
            reason=f"Default review required (platform={platform_type.value}, score={relevance_score:.2f})",
            auto_approve_eligible=False,
        )

    def is_social_platform(self, platform: str | PlatformType) -> bool:
        """소셜 플랫폼 여부 확인"""
        platform_type = self._normalize_platform(platform)
        return platform_type in SOCIAL_PLATFORMS

    def is_trusted_domain(self, domain: str) -> bool:
        """신뢰 도메인 여부 확인"""
        return self._is_trusted_domain(domain)

    def add_trusted_domain(self, domain: str) -> None:
        """신뢰 도메인 추가"""
        self.trusted_domains.add(domain.lower())
        logger.info(f"Added trusted domain: {domain}")

    def remove_trusted_domain(self, domain: str) -> bool:
        """신뢰 도메인 제거"""
        domain_lower = domain.lower()
        if domain_lower in self.trusted_domains:
            self.trusted_domains.remove(domain_lower)
            logger.info(f"Removed trusted domain: {domain}")
            return True
        return False

    def _normalize_platform(self, platform: str | PlatformType) -> PlatformType:
        """플랫폼 문자열을 PlatformType으로 변환"""
        if isinstance(platform, PlatformType):
            return platform

        platform_lower = platform.lower().strip()
        try:
            return PlatformType(platform_lower)
        except ValueError:
            # 알 수 없는 플랫폼은 WEB으로 처리
            logger.debug(f"Unknown platform '{platform}', treating as WEB")
            return PlatformType.WEB

    def _is_trusted_domain(self, domain: str) -> bool:
        """신뢰 도메인 확인 (서브도메인 포함)"""
        if not domain:
            return False

        domain_lower = domain.lower()

        # 정확히 일치
        if domain_lower in self.trusted_domains:
            return True

        # 서브도메인 확인 (예: blog.openai.com → openai.com)
        for trusted in self.trusted_domains:
            if domain_lower.endswith(f".{trusted}"):
                return True

        return False
