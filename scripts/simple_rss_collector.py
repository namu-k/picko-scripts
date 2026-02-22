"""
Simple RSS Collector - 독립형 RSS 수집기

기존 Picko의 복잡한 파이프라인 없이, RSS 피드만 긁어서 마크다운 파일로 저장합니다.
Windows 작업 스케줄러 또는 cron으로 주기적 실행할 수 있습니다.

Usage:
    python scripts/simple_rss_collector.py
    python scripts/simple_rss_collector.py --output ./inbox/rss
    python scripts/simple_rss_collector.py --config ./my_feeds.yml
    python scripts/simple_rss_collector.py --hours 24  # 최근 24시간만
    python scripts/simple_rss_collector.py --no-by-date  # 날짜별 폴더 생성 비활성화
"""

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import TypedDict

import feedparser


# 기본 RSS 피드 목록
class FeedMeta(TypedDict):
    id: str
    name: str
    url: str
    category: str


class FeedItem(TypedDict):
    title: str
    link: str
    summary: str
    published: str | None
    author: str
    tags: list[str]


DEFAULT_FEEDS: list[FeedMeta] = [
    {
        "id": "techcrunch",
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech_news",
    },
    {
        "id": "hacker_news",
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech_community",
    },
    {
        "id": "ai_news",
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "category": "ai",
    },
]


def sanitize_filename(text: str, max_length: int = 80) -> str:
    """파일명으로 사용할 수 있게 문자열 정리"""
    # 특수문자 제거
    cleaned = re.sub(r'[<>:"/\\|?*#]', "", text)
    # 공백을 언더스코어로
    cleaned = re.sub(r"\s+", "_", cleaned)
    # 길이 제한
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned.strip("_")


def generate_hash(content: str) -> str:
    """중복 체크용 해시 생성"""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def parse_published_date(entry: Mapping[str, object]) -> datetime | None:
    """RSS 엔트리에서 발행일 추출 (daily_collector 패턴과 유사)"""

    for key in ("published", "updated"):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue

    return None


def fetch_feed(feed_url: str, hours: int | None = None) -> list[FeedItem]:
    """
    RSS 피드에서 항목 수집

    Args:
        feed_url: RSS 피드 URL
        hours: 최근 N시간 항목만 수집 (None이면 전체)

    Returns:
        수집된 항목 리스트
    """
    feed = feedparser.parse(feed_url)
    items: list[FeedItem] = []

    cutoff_time = None
    if hours:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    entries = getattr(feed, "entries", None)
    if not isinstance(entries, list):
        entries = []

    for entry in entries:
        if not isinstance(entry, Mapping):
            continue

        published = parse_published_date(entry)

        # 시간 필터
        if cutoff_time and published and published < cutoff_time:
            continue

        tags: list[str] = []
        tags_raw = entry.get("tags")
        if isinstance(tags_raw, list):
            for tag in tags_raw:
                if not isinstance(tag, Mapping):
                    continue
                term = tag.get("term")
                if isinstance(term, str) and term.strip():
                    tags.append(term.strip())

        title = entry.get("title")
        link = entry.get("link")
        summary = entry.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = entry.get("description")

        author = entry.get("author")
        if not isinstance(author, str) or not author.strip():
            author = entry.get("dc_creator")

        item: FeedItem = {
            "title": title if isinstance(title, str) and title.strip() else "Untitled",
            "link": link if isinstance(link, str) else "",
            "summary": summary if isinstance(summary, str) else "",
            "published": published.isoformat() if published else None,
            "author": author if isinstance(author, str) and author.strip() else "",
            "tags": tags,
        }
        items.append(item)

    return items


def create_markdown(item: FeedItem, feed: FeedMeta) -> str:
    """마크다운 파일 내용 생성"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    frontmatter = f"""---
title: "{item["title"].replace('"', '\\"')}"
source: "{feed["name"]}"
source_id: "{feed["id"]}"
category: "{feed["category"]}"
link: "{item["link"]}"
collected_at: "{now}"
published_at: "{item["published"] or "unknown"}"
author: "{item["author"] or "unknown"}"
tags: {json.dumps(item["tags"]) if item["tags"] else "[]"}
url_hash: "{hashlib.md5(item["link"].encode()).hexdigest()[:12]}"
---

"""
    content = f"""# {item["title"]}

> Source: [{feed["name"]}]({item["link"]})

{item["summary"]}

---
*Collected at {now}*
"""
    return frontmatter + content


def load_feeds_from_config(config_path: str) -> list[FeedMeta]:
    """YAML 설정에서 피드 로드 (기존 Picko 설정 호환)"""
    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        feeds: list[FeedMeta] = []
        for source in config.get("sources", []):
            if source.get("type") == "rss" and source.get("enabled", True):
                feeds.append(
                    {
                        "id": source["id"],
                        "name": source.get("name", source["id"]),
                        "url": source["url"],
                        "category": source.get("category", "general"),
                    }
                )
        return feeds
    except Exception as e:
        print(f"[WARN] Could not load config from {config_path}: {e}")
        return DEFAULT_FEEDS


def main():
    parser = argparse.ArgumentParser(description="Simple RSS Collector - RSS 피드를 마크다운 파일로 저장")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./inbox/rss",
        help="출력 폴더 경로 (기본: ./inbox/rss)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="RSS 피드 설정 파일 (YAML, 기존 sources.yml 호환)",
    )
    parser.add_argument(
        "--hours",
        "-H",
        type=int,
        default=None,
        help="최근 N시간 항목만 수집 (기본: 제한 없음)",
    )
    parser.add_argument(
        "--max-items",
        "-m",
        type=int,
        default=50,
        help="피드당 최대 항목 수 (기본: 50)",
    )

    by_date_group = parser.add_mutually_exclusive_group()
    by_date_group.add_argument(
        "--by-date",
        dest="by_date",
        action="store_true",
        help="날짜별 폴더 생성 (YYYY-MM-DD) (기본값)",
    )
    by_date_group.add_argument(
        "--no-by-date",
        dest="by_date",
        action="store_false",
        help="날짜별 폴더 생성 비활성화 (한 폴더에 누적)",
    )
    parser.set_defaults(by_date=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 저장 없이 수집 결과만 출력",
    )

    args = parser.parse_args()

    # 피드 목록 로드
    if args.config:
        feeds = load_feeds_from_config(args.config)
    else:
        feeds = DEFAULT_FEEDS

    print(f"[INFO] Loading {len(feeds)} RSS feeds...")
    print(f"[INFO] Output folder: {args.output}")

    # 출력 폴더 생성
    output_path = Path(args.output)
    if not args.dry_run:
        if args.by_date:
            today = datetime.now().strftime("%Y-%m-%d")
            output_path = output_path / today
        output_path.mkdir(parents=True, exist_ok=True)

    # 수집 통계
    total_items = 0
    saved_files = 0
    errors: list[str] = []

    # 각 피드 수집
    for feed in feeds:
        print(f"\n[FEED] {feed['name']} ({feed['url']})")

        try:
            items = fetch_feed(feed["url"], hours=args.hours)
            items = items[: args.max_items]  # 최대 항목 제한

            print(f"  - Found {len(items)} items")

            for item in items:
                total_items += 1

                if args.dry_run:
                    print(f"    - {item['title'][:60]}...")
                    continue

                # 파일명 생성
                filename = sanitize_filename(item["title"])
                hash_suffix = generate_hash(item["link"])
                filepath = output_path / f"{filename}_{hash_suffix}.md"

                # 중복 체크 (이미 파일이 있으면 스킵)
                if filepath.exists():
                    print(f"    * Skip (exists): {item['title'][:50]}...")
                    continue

                # 마크다운 생성 및 저장
                content = create_markdown(item, feed)
                filepath.write_text(content, encoding="utf-8")
                saved_files += 1
                print(f"    + Saved: {filepath.name}")

        except Exception as e:
            error_msg = f"{feed['id']}: {str(e)}"
            errors.append(error_msg)
            print(f"  - ERROR: {e}")

    # 결과 출력
    print("\n" + "=" * 50)
    print("COLLECTION COMPLETE")
    print("=" * 50)
    print(f"Feeds processed: {len(feeds)}")
    print(f"Total items found: {total_items}")
    print(f"Files saved: {saved_files}")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors:
            print(f"  - {err}")
    print(f"Output: {output_path.absolute()}")

    return {
        "feeds": len(feeds),
        "total_items": total_items,
        "saved_files": saved_files,
        "errors": errors,
    }


if __name__ == "__main__":
    main()
