"""
SourceManager 단위 테스트
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from picko.source_manager import SourceManager, SourceMeta


@pytest.fixture
def temp_sources_yml(tmp_path):
    """임시 sources.yml 파일"""
    sources_data = {
        "sources": [
            {
                "id": "techcrunch",
                "type": "rss",
                "url": "https://techcrunch.com/feed/",
                "category": "tech_news",
                "enabled": True,
            },
            {
                "id": "hacker_news",
                "type": "rss",
                "url": "https://hnrss.org/frontpage",
                "category": "tech_community",
                "enabled": True,
            },
        ],
        "categories": {
            "tech_news": {"relevance_boost": 1.0},
            "tech_community": {"relevance_boost": 0.8},
        },
    }

    sources_file = tmp_path / "sources.yml"
    with open(sources_file, "w", encoding="utf-8") as f:
        yaml.dump(sources_data, f)

    return sources_file


@pytest.fixture
def temp_sources_yml_v2(tmp_path):
    """V2 필드가 포함된 sources.yml"""
    sources_data = {
        "sources": [
            {
                "id": "yc_blog",
                "type": "rss",
                "url": "https://www.ycombinator.com/blog/rss",
                "category": "startup",
                "enabled": True,
                "auto_discovered": True,
                "discovered_at": "2026-02-20",
                "discovery_keyword": "스타트업",
                "quality_score": 0.92,
            },
        ],
        "categories": {},
    }

    sources_file = tmp_path / "sources_v2.yml"
    with open(sources_file, "w", encoding="utf-8") as f:
        yaml.dump(sources_data, f)

    return sources_file


class TestSourceMeta:
    """SourceMeta dataclass 테스트"""

    def test_from_dict_basic(self):
        """기존 형식 딕셔너리에서 생성"""
        data = {
            "id": "test",
            "type": "rss",
            "url": "https://example.com/feed",
            "category": "test",
        }
        meta = SourceMeta.from_dict(data)

        assert meta.id == "test"
        assert meta.type == "rss"
        assert meta.url == "https://example.com/feed"
        assert meta.enabled is True  # 기본값
        assert meta.auto_discovered is False  # V2 기본값

    def test_from_dict_v2_fields(self):
        """V2 필드 포함 딕셔너리에서 생성"""
        data = {
            "id": "test",
            "type": "rss",
            "url": "https://example.com/feed",
            "category": "test",
            "auto_discovered": True,
            "quality_score": 0.85,
            "discovered_at": "2026-02-25",
        }
        meta = SourceMeta.from_dict(data)

        assert meta.auto_discovered is True
        assert meta.quality_score == 0.85
        assert meta.discovered_at == "2026-02-25"

    def test_to_dict_basic(self):
        """기본 필드만 딕셔너리로 변환"""
        meta = SourceMeta(
            id="test",
            type="rss",
            url="https://example.com/feed",
            category="test",
        )
        data = meta.to_dict(include_v2=False)

        assert "id" in data
        assert "type" in data
        assert "url" in data
        assert "category" in data
        assert "auto_discovered" not in data

    def test_to_dict_v2(self):
        """V2 필드 포함 딕셔너리로 변환"""
        meta = SourceMeta(
            id="test",
            type="rss",
            url="https://example.com/feed",
            category="test",
            auto_discovered=True,
            quality_score=0.9,
        )
        data = meta.to_dict(include_v2=True)

        assert data["auto_discovered"] is True
        assert data["quality_score"] == 0.9


class TestSourceManager:
    """SourceManager 클래스 테스트"""

    def test_load_basic(self, temp_sources_yml):
        """기존 형식 sources.yml 로드"""
        sm = SourceManager(temp_sources_yml)
        sources = sm.load()

        assert len(sources) == 2
        assert sources[0].id == "techcrunch"
        assert sources[1].id == "hacker_news"

    def test_load_v2_fields(self, temp_sources_yml_v2):
        """V2 필드 포함 sources.yml 로드"""
        sm = SourceManager(temp_sources_yml_v2)
        sources = sm.load()

        assert len(sources) == 1
        assert sources[0].auto_discovered is True
        assert sources[0].quality_score == 0.92

    def test_get_by_id(self, temp_sources_yml):
        """ID로 소스 조회"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        source = sm.get_by_id("techcrunch")
        assert source is not None
        assert source.url == "https://techcrunch.com/feed/"

        not_found = sm.get_by_id("nonexistent")
        assert not_found is None

    def test_get_active(self, temp_sources_yml):
        """활성 소스만 반환"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        active = sm.get_active()
        assert len(active) == 2

    def test_get_urls(self, temp_sources_yml):
        """모든 URL 집합 반환"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        urls = sm.get_urls()
        assert "https://techcrunch.com/feed/" in urls
        assert "https://hnrss.org/frontpage" in urls

    def test_add_candidate(self, temp_sources_yml):
        """후보 추가"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        new_source = SourceMeta(
            id="new_source",
            type="rss",
            url="https://new.example.com/feed",
            category="test",
        )
        sm.add_candidate(new_source, status="pending")

        sources = sm.load()
        pending = sm.get_pending()
        assert len(pending) == 1
        assert pending[0].id == "new_source"
        assert pending[0].status == "pending"

    def test_approve(self, temp_sources_yml):
        """소스 승인"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        # 후보 추가
        new_source = SourceMeta(
            id="new_source",
            type="rss",
            url="https://new.example.com/feed",
            category="test",
        )
        sm.add_candidate(new_source, status="pending")

        # 승인
        result = sm.approve("new_source")
        assert result is True

        # 상태 확인
        source = sm.get_by_id("new_source")
        assert source.status == "active"
        assert source.enabled is True

    def test_reject(self, temp_sources_yml):
        """소스 거부"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        # 후보 추가
        new_source = SourceMeta(
            id="new_source",
            type="rss",
            url="https://new.example.com/feed",
            category="test",
        )
        sm.add_candidate(new_source, status="pending")

        # 거부
        result = sm.reject("new_source")
        assert result is True

        # 상태 확인
        source = sm.get_by_id("new_source")
        assert source.status == "rejected"
        assert source.enabled is False

    def test_update_stats(self, temp_sources_yml):
        """통계 갱신"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        sm.update_stats("techcrunch", quality_score=0.9, collected_count=10)

        source = sm.get_by_id("techcrunch")
        assert source.quality_score == 0.9
        assert source.collected_count == 10

    def test_get_categories(self, temp_sources_yml):
        """카테고리 설정 반환"""
        sm = SourceManager(temp_sources_yml)
        sm.load()

        categories = sm.get_categories()
        assert "tech_news" in categories
        assert "tech_community" in categories

    def test_backward_compatibility(self, temp_sources_yml):
        """하위호환: 기존 형식 저장 후 다시 로드"""
        sm = SourceManager(temp_sources_yml)
        sources = sm.load()

        # 저장
        sm.save(sources)

        # 다시 로드
        sm2 = SourceManager(temp_sources_yml)
        sources2 = sm2.load()

        assert len(sources2) == 2
        assert sources2[0].id == "techcrunch"
