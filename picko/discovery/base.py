"""
Base Discovery Collector for source discovery

Provides abstract base class and data structures for platform-specific adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from picko.logger import get_logger

logger = get_logger("discovery.base")


class SourceStatus(Enum):
    """소스 상태"""

    PENDING = "pending"  # 사람 검토 대기
    ACTIVE = "active"  # 활성 (자동 승인됨)
    REJECTED = "rejected"  # 거절됨
    PAUSED = "paused"  # 일시 중단


@dataclass
class SourceCandidate:
    """
    발견된 소스 후보

    Platform adapters return list of SourceCandidate objects.
    """

    handle: str  # 계정 핸들 (예: @ai_news)
    platform: str  # 플랫폼 (threads, reddit, mastodon)
    url: str  # 프로필 URL
    relevance_score: float  # 관련도 점수 (0.0-1.0)
    metadata: dict[str, Any] = field(default_factory=dict)  # 추가 정보

    # 선택적 필드
    display_name: str | None = None  # 표시 이름
    description: str | None = None  # 계정 설명
    followers: int | None = None  # 팔로워 수
    verified: bool = False  # 인증 여부

    # 발견 정보
    discovered_at: datetime = field(default_factory=datetime.now)
    discovered_keyword: str | None = None  # 발견 키워드
    source_type: str = "social"  # 소스 타입

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "handle": self.handle,
            "platform": self.platform,
            "url": self.url,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "display_name": self.display_name,
            "description": self.description,
            "followers": self.followers,
            "verified": self.verified,
            "discovered_at": self.discovered_at.isoformat(),
            "discovered_keyword": self.discovered_keyword,
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceCandidate":
        """딕셔너리에서 생성"""
        discovered_at = data.get("discovered_at")
        if isinstance(discovered_at, str):
            discovered_at = datetime.fromisoformat(discovered_at)
        elif discovered_at is None:
            discovered_at = datetime.now()

        return cls(
            handle=data["handle"],
            platform=data["platform"],
            url=data["url"],
            relevance_score=data["relevance_score"],
            metadata=data.get("metadata", {}),
            display_name=data.get("display_name"),
            description=data.get("description"),
            followers=data.get("followers"),
            verified=data.get("verified", False),
            discovered_at=discovered_at,
            discovered_keyword=data.get("discovered_keyword"),
            source_type=data.get("source_type", "social"),
        )


class BaseDiscoveryCollector(ABC):
    """
    소스 발견 추상 클래스

    Platform-specific adapters must implement:
    - search(keyword) -> list[SourceCandidate]
    """

    def __init__(self, platform: str, config: dict[str, Any] | None = None):
        """
        Initialize BaseDiscoveryCollector

        Args:
            platform: 플랫폼 이름 (threads, reddit, mastodon)
            config: 플랫폼별 설정
        """
        self.platform = platform
        self.config = config or {}

        logger.info(f"{self.__class__.__name__} initialized for platform: {platform}")

    @abstractmethod
    async def search(self, keyword: str) -> list[SourceCandidate]:
        """
        키워드로 소스 검색

        Args:
            keyword: 검색 키워드

        Returns:
            발견된 소스 후보 목록
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        API 사용 가능 여부 확인

        Returns:
            API 키 설정 등 필요한 구성이 완료되었는지
        """
        pass

    def get_rate_limit_info(self) -> dict[str, Any]:
        """
        레이트 리밋 정보 반환

        Returns:
            레이트 리밋 정보 (remaining, reset_time 등)
        """
        return {
            "platform": self.platform,
            "available": True,
            "remaining": None,
            "reset_time": None,
        }

    def _create_candidate(
        self,
        handle: str,
        url: str,
        relevance_score: float,
        **kwargs: Any,
    ) -> SourceCandidate:
        """
        SourceCandidate 생성 헬퍼

        Args:
            handle: 계정 핸들
            url: 프로필 URL
            relevance_score: 관련도 점수
            **kwargs: 추가 필드

        Returns:
            SourceCandidate 인스턴스
        """
        return SourceCandidate(
            handle=handle,
            platform=self.platform,
            url=url,
            relevance_score=relevance_score,
            **kwargs,
        )
