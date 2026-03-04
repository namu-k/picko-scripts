import sys
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts import simple_rss_collector as src


def test_sanitize_filename_and_hash():
    value = src.sanitize_filename('A <bad> "title" / with * chars')
    assert "<" not in value
    assert "/" not in value
    assert src.generate_hash("https://example.com")


def test_parse_published_date_returns_none_for_invalid():
    assert src.parse_published_date({"published": "not-a-date"}) is None


def test_fetch_feed_normalizes_fields(monkeypatch):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    feed = SimpleNamespace(
        entries=[
            {
                "title": "Item A",
                "link": "https://example.com/a",
                "summary": "sum",
                "author": "me",
                "published": now,
                "tags": [{"term": "ai"}],
            },
            {
                "title": "Item B",
                "link": "https://example.com/b",
                "description": "desc",
            },
        ]
    )
    monkeypatch.setattr("scripts.simple_rss_collector.feedparser.parse", lambda url: feed)

    items = src.fetch_feed("https://feed", hours=None)

    assert len(items) == 2
    assert items[0]["tags"] == ["ai"]
    assert items[1]["summary"] == "desc"


def test_load_feeds_from_config_and_fallback(tmp_path):
    cfg = tmp_path / "sources.yml"
    cfg.write_text(
        """
sources:
  - id: s1
    type: rss
    url: https://example.com/feed
    enabled: true
    category: test
""".strip(),
        encoding="utf-8",
    )
    feeds = src.load_feeds_from_config(str(cfg))
    assert feeds[0]["id"] == "s1"

    fallback = src.load_feeds_from_config(str(tmp_path / "missing.yml"))
    assert fallback == src.DEFAULT_FEEDS


def test_main_dry_run_collects_without_writing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.simple_rss_collector.fetch_feed",
        lambda url, hours=None: [
            {
                "title": "A",
                "link": "https://x",
                "summary": "s",
                "published": None,
                "author": "",
                "tags": [],
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.simple_rss_collector.DEFAULT_FEEDS",
        [{"id": "f1", "name": "Feed", "url": "https://x", "category": "test"}],
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "simple_rss_collector",
            "--dry-run",
            "--output",
            str(tmp_path),
            "--max-items",
            "1",
        ],
    )
    result = src.main()

    assert result["feeds"] == 1
    assert result["total_items"] == 1
    assert result["saved_files"] == 0
