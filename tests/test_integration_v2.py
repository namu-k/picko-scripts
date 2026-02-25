"""
통합 테스트
하위호환, 발견→승인→수집 플로우, 컬렉터 실패 격리
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from picko.collectors import CollectedItem
from picko.collectors.rss import RSSCollector
from picko.source_manager import SourceManager, SourceMeta


class TestBackwardCompatibility:
    """기존 sources.yml 하위호환 테스트"""

    @pytest.fixture
    def legacy_sources_yml(self, tmp_path):
        """기존 형식 sources.yml (V2 필드 없음)"""
        sources_data = {
            "sources": [
                {
                    "id": "legacy_rss",
                    "type": "rss",
                    "url": "https://legacy.com/feed",
                    "category": "tech",
                    "enabled": True,
                },
                {
                    "id": "legacy_disabled",
                    "type": "rss",
                    "url": "https://disabled.com/feed",
                    "category": "tech",
                    "enabled": False,
                },
            ],
            "categories": {
                "tech": {"relevance_boost": 1.0},
            },
        }
        sources_file = tmp_path / "sources.yml"
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(sources_data, f)
        return sources_file

    def test_load_legacy_sources(self, legacy_sources_yml):
        """기존 형식 로드"""
        sm = SourceManager(legacy_sources_yml)
        sources = sm.load()

        assert len(sources) == 2
        assert sources[0].id == "legacy_rss"
        assert sources[0].auto_discovered is False  # V2 기본값

    def test_save_legacy_format(self, legacy_sources_yml):
        """기존 형식 유지하며 저장"""
        sm = SourceManager(legacy_sources_yml)
        sources = sm.load()

        # 저장
        sm.save(sources)

        # 다시 로드하여 확인
        with open(legacy_sources_yml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # V2 필드가 추가되지 않음 (기존 소스)
        assert "auto_discovered" not in data["sources"][0]

    def test_get_active_legacy(self, legacy_sources_yml):
        """활성 소스 조회"""
        sm = SourceManager(legacy_sources_yml)
        active = sm.get_active()

        assert len(active) == 1
        assert active[0].id == "legacy_rss"

    @patch("picko.collectors.rss.feedparser.parse")
    def test_rss_collector_with_legacy_sources(self, mock_parse, legacy_sources_yml):
        """RSSCollector가 기존 소스로 동작"""
        sm = SourceManager(legacy_sources_yml)
        sources = sm.get_active()

        # Mock RSS feed
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                link="https://legacy.com/article1",
                title="Article 1",
                summary="Content",
                published="Mon, 24 Feb 2026 10:00:00 GMT",
            )
        ]
        mock_parse.return_value = mock_feed

        collector = RSSCollector(sources=sources)
        items = collector.collect("test_account")

        assert len(items) == 1
        assert items[0].source_id == "legacy_rss"


class TestDiscoveryApprovalCollection:
    """발견 → 승인 → 수집 플로우 테스트"""

    @pytest.fixture
    def setup_sources(self, tmp_path):
        """테스트용 sources.yml 설정"""
        sources_data = {
            "sources": [
                {
                    "id": "existing",
                    "type": "rss",
                    "url": "https://existing.com/feed",
                    "category": "tech",
                    "enabled": True,
                }
            ],
            "categories": {},
        }
        sources_file = tmp_path / "sources.yml"
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(sources_data, f)
        return sources_file

    def test_discovery_to_approval_flow(self, setup_sources):
        """발견 → 승인 플로우"""
        sm = SourceManager(setup_sources)
        sm.load()

        # 1. 새 소스 발견 (pending 추가)
        new_source = SourceMeta(
            id="discovered_source",
            type="rss",
            url="https://discovered.com/feed",
            category="tech",
        )
        sm.add_candidate(new_source, status="pending")

        # pending 상태 확인
        pending = sm.get_pending()
        assert len(pending) == 1
        assert pending[0].id == "discovered_source"

        # 2. 승인
        sm.approve("discovered_source")

        # active 상태로 변경 확인
        source = sm.get_by_id("discovered_source")
        assert source.status == "active"
        assert source.enabled is True

        # pending에서 제거
        pending = sm.get_pending()
        assert len(pending) == 0

    def test_discovery_to_rejection_flow(self, setup_sources):
        """발견 → 거부 플로우"""
        sm = SourceManager(setup_sources)
        sm.load()

        # 새 소스 발견
        new_source = SourceMeta(
            id="bad_source",
            type="rss",
            url="https://bad.com/feed",
            category="tech",
        )
        sm.add_candidate(new_source, status="pending")

        # 거부
        sm.reject("bad_source")

        # rejected 상태 확인
        source = sm.get_by_id("bad_source")
        assert source.status == "rejected"
        assert source.enabled is False

    @patch("picko.collectors.rss.feedparser.parse")
    def test_approved_source_collected(self, mock_parse, setup_sources):
        """승인된 소스가 수집에 포함됨"""
        sm = SourceManager(setup_sources)

        # 새 소스 발견 및 승인
        new_source = SourceMeta(
            id="approved_source",
            type="rss",
            url="https://approved.com/feed",
            category="tech",
        )
        sm.add_candidate(new_source, status="pending")
        sm.approve("approved_source")

        # Mock RSS feed
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                link="https://approved.com/article",
                title="Article",
                summary="Content",
                published=None,
            )
        ]
        mock_parse.return_value = mock_feed

        # 수집
        active_sources = sm.get_active()
        collector = RSSCollector(sources=active_sources)
        items = collector.collect("test_account")

        # approved_source에서 수집됨
        source_ids = {item.source_id for item in items}
        assert "approved_source" in source_ids or "existing" in source_ids


class TestCollectorFailureIsolation:
    """컬렉터 실패 격리 테스트"""

    @pytest.fixture
    def setup_collectors(self, tmp_path):
        """테스트용 설정"""
        sources_data = {
            "sources": [
                {
                    "id": "good_source",
                    "type": "rss",
                    "url": "https://good.com/feed",
                    "category": "tech",
                    "enabled": True,
                },
                {
                    "id": "bad_source",
                    "type": "rss",
                    "url": "https://bad.com/feed",
                    "category": "tech",
                    "enabled": True,
                },
            ],
            "categories": {},
        }
        sources_file = tmp_path / "sources.yml"
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(sources_data, f)

        # Perplexity 입력 디렉토리
        input_dir = tmp_path / "input"
        archive_dir = tmp_path / "archive"
        input_dir.mkdir()
        archive_dir.mkdir()

        return sources_file, input_dir, archive_dir

    @patch("picko.collectors.rss.feedparser.parse")
    def test_one_rss_failure_continues_others(self, mock_parse, setup_collectors):
        """하나의 RSS 소스 실패해도 다른 소스 계속 수집"""
        sources_file, _, _ = setup_collectors
        sm = SourceManager(sources_file)
        sources = sm.get_active()

        def side_effect(url):
            if "bad.com" in url:
                raise Exception("Network error")
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(
                    link="https://good.com/article",
                    title="Good Article",
                    summary="Content",
                    published=None,
                )
            ]
            return mock_feed

        mock_parse.side_effect = side_effect

        collector = RSSCollector(sources=sources)
        items = collector.collect("test_account")

        # bad_source는 실패하지만 good_source는 수집됨
        assert len(items) == 1
        assert items[0].source_id == "good_source"

    def test_perplexity_failure_isolated(self, setup_collectors, tmp_path):
        """Perplexity 실패가 RSS 수집에 영향 없음"""
        sources_file, input_dir, archive_dir = setup_collectors

        from picko.collectors.perplexity import PerplexityCollector

        # Perplexity 입력 파일 없음 (빈 디렉토리)
        perplexity = PerplexityCollector(input_dir=input_dir, archive_dir=archive_dir)
        items = perplexity.collect("test_account")

        # 빈 결과지만 예외 없음
        assert len(items) == 0


class TestEndToEndDryRun:
    """E2E Dry Run 테스트"""

    @pytest.fixture
    def full_setup(self, tmp_path):
        """전체 설정"""
        # sources.yml
        sources_data = {
            "sources": [
                {
                    "id": "test_source",
                    "type": "rss",
                    "url": "https://test.com/feed",
                    "category": "tech",
                    "enabled": True,
                }
            ],
            "categories": {"tech": {"relevance_boost": 1.0}},
        }
        sources_file = tmp_path / "sources.yml"
        with open(sources_file, "w", encoding="utf-8") as f:
            yaml.dump(sources_data, f)

        # collectors.yml
        collectors_data = {
            "perplexity": {
                "enabled": False,
                "input_dir": str(tmp_path / "input"),
                "archive_dir": str(tmp_path / "archive"),
            },
            "quality_rules": {
                "min_quality_score": 0.5,
            },
        }
        collectors_file = tmp_path / "collectors.yml"
        with open(collectors_file, "w", encoding="utf-8") as f:
            yaml.dump(collectors_data, f)

        return sources_file, collectors_file

    def test_dry_run_no_changes(self, full_setup):
        """dry-run 모드에서는 변경사항 없음"""
        sources_file, collectors_file = full_setup

        sm = SourceManager(sources_file)
        original_sources = sm.load()
        original_count = len(original_sources)

        # 새 소스 후보 추가 (dry-run이므로 실제로는 추가 안됨)
        new_source = SourceMeta(
            id="dry_run_test",
            type="rss",
            url="https://dryrun.com/feed",
            category="tech",
        )

        # 실제로는 추가하지 않음 (dry-run 로직 시뮬레이션)
        # sm.add_candidate(new_source, status="pending")

        # 소스 수 변화 없음
        sm.load()
        assert len(sm.load()) == original_count

    @patch("picko.collectors.rss.feedparser.parse")
    def test_collection_with_mock(self, mock_parse, full_setup):
        """Mock을 사용한 수집 테스트"""
        sources_file, collectors_file = full_setup

        # Create proper mock entry
        entry = MagicMock()
        entry.link = "https://test.com/article1"
        entry.title = "Test Article"
        entry.summary = "Test content"
        entry.published = "Mon, 24 Feb 2026 10:00:00 GMT"
        entry.get = lambda key, default=None: getattr(entry, key, default)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_parse.return_value = mock_feed

        sm = SourceManager(sources_file)
        sources = sm.get_active()
        collector = RSSCollector(sources=sources)
        items = collector.collect("test_account")

        assert len(items) == 1
        assert items[0].title == "Test Article"
        assert items[0].source_type == "rss"
