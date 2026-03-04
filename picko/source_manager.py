"""
소스 메타데이터 관리 모듈
sources.yml CRUD + V2 확장 필드 지원
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from picko.logger import setup_logger

logger = setup_logger("source_manager")


@dataclass
class SourceMeta:
    """소스 메타데이터 — 기존 필드 + V2 확장 필드"""

    # 기존 필수 필드
    id: str
    type: str  # "rss" | "newsletter"
    url: str
    category: str
    enabled: bool = True

    # V2 확장 필드 (모두 optional)
    auto_discovered: bool = False
    status: str = "active"  # "active" | "pending" | "rejected"
    added_at: str | None = None
    discovered_at: str | None = None
    discovered_by: str | None = None
    discovery_keyword: str | None = None
    quality_score: float | None = None
    relevance_scores: dict[str, float] | None = None
    last_collected: str | None = None
    collected_count: int = 0
    signal_noise_ratio: float | None = None

    # 뉴스레터 전용
    platform: str | None = None  # "substack" | "buttondown" | etc
    rss_url: str | None = None
    subscribers: int | None = None

    # Subsystem B 전용 필드 (007-agentic)
    human_review_required: bool = False
    api_provider: str | None = None  # "threads_api", "reddit_api", "mastodon_api"
    account_handle: str | None = None  # "@ai_news"
    last_api_sync: str | None = None
    enhanced_verification: dict[str, Any] | None = None  # {enabled, collections_remaining, elevated_threshold}

    def to_dict(self, include_v2: bool = True) -> dict[str, Any]:
        """딕셔너리로 변환. 기존 형식 유지를 위해 V2 필드는 optional"""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "url": self.url,
            "category": self.category,
            "enabled": self.enabled,
        }
        if include_v2:
            # V2 필드는 값이 있을 때만 추가 (불필요한 null 제거)
            if self.auto_discovered:
                result["auto_discovered"] = self.auto_discovered
            if self.status != "active":
                result["status"] = self.status
            if self.added_at:
                result["added_at"] = self.added_at
            if self.discovered_at:
                result["discovered_at"] = self.discovered_at
            if self.discovered_by:
                result["discovered_by"] = self.discovered_by
            if self.discovery_keyword:
                result["discovery_keyword"] = self.discovery_keyword
            if self.quality_score is not None:
                result["quality_score"] = self.quality_score
            if self.relevance_scores:
                result["relevance_scores"] = self.relevance_scores
            if self.last_collected:
                result["last_collected"] = self.last_collected
            if self.collected_count > 0:
                result["collected_count"] = self.collected_count
            if self.signal_noise_ratio is not None:
                result["signal_noise_ratio"] = self.signal_noise_ratio
            # 뉴스레터 전용 필드
            if self.platform:
                result["platform"] = self.platform
            if self.rss_url:
                result["rss_url"] = self.rss_url
            if self.subscribers is not None:
                result["subscribers"] = self.subscribers
            # Subsystem B 전용 필드
            if self.human_review_required:
                result["human_review_required"] = self.human_review_required
            if self.api_provider:
                result["api_provider"] = self.api_provider
            if self.account_handle:
                result["account_handle"] = self.account_handle
            if self.last_api_sync:
                result["last_api_sync"] = self.last_api_sync
            if self.enhanced_verification:
                result["enhanced_verification"] = self.enhanced_verification

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceMeta":
        """딕셔너리에서 SourceMeta 생성 (누락 필드는 기본값)"""
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "rss"),
            url=data.get("url", ""),
            category=data.get("category", "general"),
            enabled=data.get("enabled", True),
            auto_discovered=data.get("auto_discovered", False),
            status=data.get("status", "active"),
            added_at=data.get("added_at"),
            discovered_at=data.get("discovered_at"),
            discovered_by=data.get("discovered_by"),
            discovery_keyword=data.get("discovery_keyword"),
            quality_score=data.get("quality_score"),
            relevance_scores=data.get("relevance_scores"),
            last_collected=data.get("last_collected"),
            collected_count=data.get("collected_count", 0),
            signal_noise_ratio=data.get("signal_noise_ratio"),
            platform=data.get("platform"),
            rss_url=data.get("rss_url"),
            subscribers=data.get("subscribers"),
            # Subsystem B 전용 필드
            human_review_required=data.get("human_review_required", False),
            api_provider=data.get("api_provider"),
            account_handle=data.get("account_handle"),
            last_api_sync=data.get("last_api_sync"),
            enhanced_verification=data.get("enhanced_verification"),
        )


class SourceManager:
    """sources.yml CRUD + 메타데이터 갱신"""

    def __init__(self, sources_path: Path):
        self.path = Path(sources_path)
        self._sources: list[SourceMeta] | None = None
        self._categories: dict[str, Any] = {}

    def load(self) -> list[SourceMeta]:
        """기존 형식도 V2 형식도 모두 로드 (누락 필드는 기본값)"""
        if self._sources is not None:
            return self._sources

        if not self.path.exists():
            logger.warning(f"Sources file not found: {self.path}")
            self._sources = []
            return self._sources

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 소스 로드
            raw_sources = data.get("sources", [])
            self._sources = [SourceMeta.from_dict(s) for s in raw_sources]

            # 카테고리 로드
            self._categories = data.get("categories", {})

            logger.info(f"Loaded {len(self._sources)} sources from {self.path}")
            return self._sources

        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
            self._sources = []
            return self._sources

    def save(self, sources: list[SourceMeta] | None = None) -> None:
        """소스 저장. 기존 필드만 있는 소스는 기존 형태로 저장 (불필요한 null 필드 제거)"""
        if sources is not None:
            self._sources = sources

        if self._sources is None:
            return

        # 기존 파일 읽어서 categories 등 다른 섹션 보존
        existing_data: dict[str, Any] = {}
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or {}
            except Exception:
                pass

        # 소스 직렬화
        raw_sources = []
        for source in self._sources:
            # auto_discovered=False인 기존 소스는 V2 필드 제외
            include_v2 = source.auto_discovered or source.status != "active"
            raw_sources.append(source.to_dict(include_v2=include_v2))

        data = {
            "sources": raw_sources,
            "categories": existing_data.get("categories", self._categories),
        }

        # 백업 생성
        backup_path = self.path.with_suffix(".yml.bak")
        if self.path.exists():
            import shutil

            shutil.copy2(self.path, backup_path)

        # 저장
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved {len(self._sources)} sources to {self.path}")

    def get_by_id(self, source_id: str) -> SourceMeta | None:
        """ID로 소스 조회"""
        sources = self.load()
        for source in sources:
            if source.id == source_id:
                return source
        return None

    def get_by_url(self, url: str) -> SourceMeta | None:
        """URL로 소스 조회"""
        sources = self.load()
        for source in sources:
            if source.url == url or source.rss_url == url:
                return source
        return None

    def get_active(self) -> list[SourceMeta]:
        """활성 소스만 반환"""
        sources = self.load()
        return [s for s in sources if s.enabled and s.status == "active"]

    def get_pending(self) -> list[SourceMeta]:
        """pending 상태 소스 반환"""
        sources = self.load()
        return [s for s in sources if s.status == "pending"]

    def add_candidate(self, source: SourceMeta, status: str = "pending") -> None:
        """발견된 후보를 pending 상태로 추가"""
        sources = self.load()

        # 중복 확인
        existing = self.get_by_url(source.url)
        if existing:
            logger.info(f"Source already exists: {source.url}")
            return

        # 메타데이터 설정
        source.status = status
        source.auto_discovered = True
        source.discovered_at = datetime.now().strftime("%Y-%m-%d")

        sources.append(source)
        self.save(sources)
        logger.info(f"Added candidate: {source.id} (status={status})")

    def approve(self, source_id: str) -> bool:
        """소스 승인"""
        sources = self.load()
        for source in sources:
            if source.id == source_id:
                source.status = "active"
                source.enabled = True
                source.added_at = datetime.now().strftime("%Y-%m-%d")
                self.save(sources)
                logger.info(f"Approved source: {source_id}")
                return True
        logger.warning(f"Source not found: {source_id}")
        return False

    def reject(self, source_id: str) -> bool:
        """소스 거부"""
        sources = self.load()
        for source in sources:
            if source.id == source_id:
                source.status = "rejected"
                source.enabled = False
                self.save(sources)
                logger.info(f"Rejected source: {source_id}")
                return True
        logger.warning(f"Source not found: {source_id}")
        return False

    def update_stats(self, source_id: str, **kwargs) -> bool:
        """소스 메타데이터 갱신"""
        sources = self.load()
        for source in sources:
            if source.id == source_id:
                for key, value in kwargs.items():
                    if hasattr(source, key):
                        setattr(source, key, value)
                self.save(sources)
                logger.debug(f"Updated stats for {source_id}: {kwargs}")
                return True
        logger.warning(f"Source not found: {source_id}")
        return False

    def disable(self, source_id: str) -> bool:
        """소스 비활성화"""
        return self.update_stats(source_id, enabled=False)

    def enable(self, source_id: str) -> bool:
        """소스 활성화"""
        return self.update_stats(source_id, enabled=True)

    def get_categories(self) -> dict[str, Any]:
        """카테고리 설정 반환"""
        if not self._categories:
            self.load()
        return self._categories

    def get_urls(self) -> set[str]:
        """모든 소스 URL 집합 반환 (중복 체크용)"""
        sources = self.load()
        urls = set()
        for s in sources:
            urls.add(s.url)
            if s.rss_url:
                urls.add(s.rss_url)
        return urls
