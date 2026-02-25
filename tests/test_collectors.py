"""
컬렉터 단위 테스트
RSSCollector, PerplexityCollector, BaseCollector 인터페이스
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from picko.collectors import BaseCollector, CollectedItem
from picko.collectors.perplexity import PerplexityCollector
from picko.collectors.rss import RSSCollector
from picko.source_manager import SourceMeta


@pytest.fixture
def sample_sources():
    """샘플 소스 목록"""
    return [
        SourceMeta(
            id="techcrunch",
            type="rss",
            url="https://techcrunch.com/feed/",
            category="tech_news",
            enabled=True,
        ),
        SourceMeta(
            id="hacker_news",
            type="rss",
            url="https://hnrss.org/frontpage",
            category="tech_community",
            enabled=True,
        ),
        SourceMeta(
            id="disabled_source",
            type="rss",
            url="https://disabled.com/feed",
            category="test",
            enabled=False,
        ),
    ]


class TestCollectedItem:
    """CollectedItem dataclass 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        item = CollectedItem(
            url="https://example.com/article",
            title="Test Article",
            body="Article content here",
            source_id="test_source",
            source_type="rss",
            published_at="2026-02-25",
            category="test",
        )
        data = item.to_dict()

        assert data["source_id"] == "test_source"
        assert data["source"] == "test_source"
        assert data["source_url"] == "https://example.com/article"
        assert data["title"] == "Test Article"
        assert data["text"] == "Article content here"
        assert data["publish_date"] == "2026-02-25"
        assert data["category"] == "test"

    def test_metadata_passthrough(self):
        """메타데이터 전달"""
        item = CollectedItem(
            url="https://example.com",
            title="Test",
            body="Content",
            source_id="test",
            source_type="rss",
            metadata={"custom_field": "value"},
        )
        data = item.to_dict()

        assert data["custom_field"] == "value"


class TestRSSCollector:
    """RSSCollector 테스트"""

    def test_init(self, sample_sources):
        """초기화"""
        collector = RSSCollector(sources=sample_sources)
        assert len(collector.sources) == 3
        assert collector.max_items_per_feed == 20

    def test_name(self, sample_sources):
        """컬렉터 이름"""
        collector = RSSCollector(sources=sample_sources)
        assert collector.name() == "rss"

    @patch("picko.collectors.rss.feedparser.parse")
    def test_collect_filters_disabled(self, mock_parse, sample_sources):
        """비활성 소스 필터링"""
        mock_parse.return_value = MagicMock(entries=[])

        collector = RSSCollector(sources=sample_sources)
        items = collector.collect("test_account")

        # enabled=False인 소스는 호출되지 않음
        # 2개의 활성 소스만 호출됨
        assert mock_parse.call_count == 2

    @patch("picko.collectors.rss.feedparser.parse")
    def test_collect_success(self, mock_parse, sample_sources):
        """수집 성공"""
        # Create proper mock entries
        entry1 = MagicMock()
        entry1.link = "https://example.com/article1"
        entry1.title = "Article 1"
        entry1.summary = "Summary 1"
        entry1.published = "Mon, 24 Feb 2026 10:00:00 GMT"
        entry1.get = lambda key, default=None: getattr(entry1, key, default)

        entry2 = MagicMock()
        entry2.link = "https://example.com/article2"
        entry2.title = "Article 2"
        entry2.summary = "Summary 2"
        entry2.published = None
        entry2.get = lambda key, default=None: getattr(entry2, key, default)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]
        mock_parse.return_value = mock_feed

        collector = RSSCollector(sources=sample_sources[:1])  # 하나만
        items = collector.collect("test_account")

        assert len(items) == 2
        assert items[0].title == "Article 1"
        assert items[0].source_type == "rss"

    def test_from_config(self):
        """설정에서 생성"""
        config = [
            {
                "id": "test",
                "type": "rss",
                "url": "https://example.com/feed",
                "category": "test",
                "enabled": True,
            }
        ]
        collector = RSSCollector.from_config(config)

        assert len(collector.sources) == 1
        assert collector.sources[0].id == "test"


class TestPerplexityCollector:
    """PerplexityCollector 테스트"""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """임시 입력/아카이브 디렉토리"""
        input_dir = tmp_path / "input"
        archive_dir = tmp_path / "archive"
        input_dir.mkdir()
        archive_dir.mkdir()
        return input_dir, archive_dir

    def test_init(self, temp_dirs):
        """초기화"""
        input_dir, archive_dir = temp_dirs
        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)

        assert collector.input_dir == input_dir
        assert collector.archive_dir == archive_dir
        assert "*.md" in collector.file_patterns

    def test_name(self, temp_dirs):
        """컬렉터 이름"""
        input_dir, archive_dir = temp_dirs
        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)
        assert collector.name() == "perplexity"

    def test_collect_empty(self, temp_dirs):
        """빈 디렉토리 수집"""
        input_dir, archive_dir = temp_dirs
        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)
        items = collector.collect("test_account")

        assert len(items) == 0

    def test_collect_md_file(self, temp_dirs):
        """마크다운 파일 수집"""
        input_dir, archive_dir = temp_dirs

        # 테스트 파일 생성
        test_file = input_dir / "test_result.md"
        test_file.write_text(
            """# Test Perplexity Result

This is a test result from Perplexity.
Check out https://example.com for more info.

Date: 2026-02-25
""",
            encoding="utf-8",
        )

        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)
        items = collector.collect("test_account")

        assert len(items) == 1
        assert items[0].title == "Test Perplexity Result"
        assert items[0].source_type == "perplexity"
        assert "example.com" in items[0].url

        # 파일이 archive로 이동했는지 확인
        assert not test_file.exists()
        assert len(list(archive_dir.glob("*.md"))) == 1

    def test_collect_html_file(self, temp_dirs):
        """HTML 파일 수집"""
        input_dir, archive_dir = temp_dirs

        # 테스트 HTML 파일 생성
        test_file = input_dir / "test_result.html"
        test_file.write_text(
            """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Test Perplexity HTML</h1>
<main>
<p>This is test content from Perplexity HTML.</p>
<a href="https://example.com">Link</a>
</main>
</body>
</html>""",
            encoding="utf-8",
        )

        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)
        items = collector.collect("test_account")

        assert len(items) == 1
        assert "Test Perplexity HTML" in items[0].title

    def test_from_config(self):
        """설정에서 생성"""
        config = {
            "input_dir": "Inbox/Perplexity",
            "archive_dir": "Archive/Perplexity",
            "file_patterns": ["*.md"],
        }
        collector = PerplexityCollector.from_config(config)

        assert str(collector.input_dir) == "Inbox/Perplexity"
        assert str(collector.archive_dir) == "Archive/Perplexity"
        assert collector.file_patterns == ["*.md"]

    def test_clean_content_removes_frontmatter(self, temp_dirs):
        """frontmatter 제거"""
        input_dir, archive_dir = temp_dirs
        collector = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)

        content = """---
title: Test
date: 2026-02-25
---

# Real Content

This is the actual content."""

        cleaned = collector._clean_content(content)
        assert not cleaned.startswith("---")
        assert "# Real Content" in cleaned


class TestBaseCollector:
    """BaseCollector 인터페이스 테스트"""

    def test_abstract_methods(self):
        """추상 메서드 구현 필요"""
        with pytest.raises(TypeError):
            BaseCollector()

    def test_concrete_implementation(self):
        """구체 구현"""

        class TestCollector(BaseCollector):
            def collect(self, account_id: str) -> list[CollectedItem]:
                return [
                    CollectedItem(
                        url="https://test.com",
                        title="Test",
                        body="Content",
                        source_id="test",
                        source_type="test",
                    )
                ]

            def name(self) -> str:
                return "test"

        collector = TestCollector()
        items = collector.collect("test_account")

        assert len(items) == 1
        assert collector.name() == "test"

    def test_repr(self):
        """문자열 표현"""

        class TestCollector(BaseCollector):
            def collect(self, account_id: str) -> list[CollectedItem]:
                return []

            def name(self) -> str:
                return "test"

        collector = TestCollector()
        assert "TestCollector:test" in repr(collector)
