"""
컬렉터 모듈
다양한 콘텐츠 소스에서 수집하기 위한 인터페이스와 구현체
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollectedItem:
    """모든 컬렉터가 반환하는 통일 아이템"""

    url: str
    title: str
    body: str
    source_id: str
    source_type: str  # "rss" | "perplexity" | "newsletter"
    published_at: str | None = None
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (기존 파이프라인 호환)"""
        return {
            "source_id": self.source_id,
            "source": self.source_id,
            "source_url": self.url,
            "title": self.title,
            "text": self.body,
            "publish_date": self.published_at,
            "category": self.category,
            "source_type": self.source_type,
            **self.metadata,
        }


class BaseCollector(ABC):
    """컬렉터 추상 기본 클래스"""

    @abstractmethod
    def collect(self, account_id: str) -> list[CollectedItem]:
        """
        수집 실행

        Args:
            account_id: 계정 ID (계정별 필터링용)

        Returns:
            수집된 아이템 리스트
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """컬렉터 식별 이름"""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.name()}>"
