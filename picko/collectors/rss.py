"""
RSS 컬렉터
기존 DailyCollector._ingest() / _fetch_rss() 로직 추출
"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from picko.collectors import BaseCollector, CollectedItem
from picko.logger import setup_logger
from picko.source_manager import SourceMeta

logger = setup_logger("rss_collector")


class RSSCollector(BaseCollector):
    """RSS 피드 수집기"""

    def __init__(self, sources: list[SourceMeta], max_items_per_feed: int = 20):
        """
        Args:
            sources: 수집할 소스 목록
            max_items_per_feed: 피드당 최대 아이템 수
        """
        self.sources = sources
        self.max_items_per_feed = max_items_per_feed

    def collect(self, account_id: str) -> list[CollectedItem]:
        """RSS 피드에서 아이템 수집"""
        items = []

        for source in self.sources:
            if not source.enabled:
                continue

            if source.type != "rss":
                continue

            try:
                feed_items = self._fetch_feed(source)
                items.extend(feed_items)
                logger.info(f"[{source.id}] Fetched {len(feed_items)} items")
            except Exception as e:
                logger.warning(f"[{source.id}] Failed to fetch RSS: {e}")

        return items

    def _fetch_feed(self, source: SourceMeta) -> list[CollectedItem]:
        """단일 RSS 피드 파싱"""
        url = source.rss_url or source.url
        feed = feedparser.parse(url)
        items = []

        for entry in feed.entries[: self.max_items_per_feed]:
            item = CollectedItem(
                url=entry.get("link", ""),
                title=entry.get("title", ""),
                body=entry.get("summary", ""),
                source_id=source.id,
                source_type="rss",
                published_at=self._parse_date(entry.get("published")),
                category=source.category,
                metadata={
                    "feed_url": url,
                },
            )
            items.append(item)

        return items

    def _parse_date(self, date_str: Any) -> str | None:
        """날짜 문자열 파싱"""
        if not date_str:
            return None

        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            try:
                # ISO 형식 시도
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return None

    def name(self) -> str:
        return "rss"

    @classmethod
    def from_config(cls, sources_config: list[dict[str, Any]]) -> "RSSCollector":
        """설정 딕셔너리에서 RSSCollector 생성"""
        sources = [SourceMeta.from_dict(s) for s in sources_config]
        return cls(sources=sources)
