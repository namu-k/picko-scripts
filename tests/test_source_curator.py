"""
SourceCurator 단위 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from picko.source_manager import SourceManager, SourceMeta
from scripts.source_curator import CurationReport, SourceCurator


@pytest.fixture
def temp_sources_yml(tmp_path):
    """임시 sources.yml with quality scores"""
    sources_data = {
        "sources": [
            {
                "id": "high_quality",
                "type": "rss",
                "url": "https://high.com/feed",
                "category": "test",
                "enabled": True,
                "quality_score": 0.95,
                "collected_count": 100,
            },
            {
                "id": "medium_quality",
                "type": "rss",
                "url": "https://medium.com/feed",
                "category": "test",
                "enabled": True,
                "quality_score": 0.7,
                "collected_count": 10,
            },
            {
                "id": "low_quality",
                "type": "rss",
                "url": "https://low.com/feed",
                "category": "test",
                "enabled": True,
                "quality_score": 0.3,
                "collected_count": 5,
            },
            {
                "id": "pending_source",
                "type": "rss",
                "url": "https://pending.com/feed",
                "category": "test",
                "enabled": False,
                "status": "pending",
            },
            {
                "id": "inactive_source",
                "type": "rss",
                "url": "https://inactive.com/feed",
                "category": "test",
                "enabled": True,
                "last_collected": "2026-01-01",  # 55일 전
            },
        ],
        "categories": {},
    }
    sources_file = tmp_path / "sources.yml"
    with open(sources_file, "w", encoding="utf-8") as f:
        yaml.dump(sources_data, f)
    return sources_file


@pytest.fixture
def temp_collectors_yml(tmp_path):
    """임시 collectors.yml"""
    config_data = {
        "quality_rules": {
            "min_relevance_score": 0.6,
            "min_quality_score": 0.5,
            "max_inactive_days": 30,
            "min_signal_noise_ratio": 0.2,
            "trusted_threshold_quality": 0.9,
            "trusted_threshold_count": 50,
        }
    }
    config_file = tmp_path / "collectors.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_file


class TestCurationReport:
    """CurationReport dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        report = CurationReport(timestamp="2026-02-25T10:00:00")

        assert report.total_sources == 0
        assert report.active_sources == 0
        assert report.low_quality_sources == []
        assert report.inactive_sources == []


class TestSourceCurator:
    """SourceCurator 클래스 테스트"""

    def test_init(self, temp_sources_yml):
        """초기화"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        assert curator.sm is sm
        assert "min_quality_score" in curator.rules

    def test_get_default_rules(self, temp_sources_yml):
        """기본 규칙"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        rules = curator.rules

        assert rules["min_relevance_score"] == 0.6
        assert rules["min_quality_score"] == 0.5
        assert rules["max_inactive_days"] == 30

    def test_apply_rules_trusted(self, temp_sources_yml):
        """신뢰 소스 판정"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # 고품질 + 많은 수집
        source = SourceMeta(
            id="trusted",
            type="rss",
            url="https://trusted.com",
            category="test",
            quality_score=0.95,
            collected_count=100,
        )

        action = curator.apply_rules(source)
        assert action == "trusted"

    def test_apply_rules_disable(self, temp_sources_yml):
        """비활성화 판정"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # 저품질
        source = SourceMeta(
            id="low",
            type="rss",
            url="https://low.com",
            category="test",
            quality_score=0.3,
        )

        action = curator.apply_rules(source)
        assert action == "disable"

    def test_apply_rules_review(self, temp_sources_yml):
        """검토 필요 판정"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # 중간 품질 (min_relevance_score < 0.6)
        source = SourceMeta(
            id="review",
            type="rss",
            url="https://review.com",
            category="test",
            quality_score=0.55,
        )

        action = curator.apply_rules(source)
        assert action == "review"

    def test_apply_rules_none(self, temp_sources_yml):
        """정상 소스 (조치 없음)"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # 양호한 품질
        source = SourceMeta(
            id="good",
            type="rss",
            url="https://good.com",
            category="test",
            quality_score=0.75,
            collected_count=10,
        )

        action = curator.apply_rules(source)
        assert action is None

    def test_evaluate_all(self, temp_sources_yml):
        """전체 평가"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        report = curator.evaluate_all()

        assert report.total_sources == 5
        assert report.pending_sources == 1
        # high_quality는 trusted_threshold를 만족하므로 trusted
        assert report.trusted_sources >= 1
        # low_quality는 min_quality_score 미만이므로 disable 대상
        assert len(report.low_quality_sources) >= 1
        # inactive_source는 30일 이상 비활성
        assert len(report.inactive_sources) >= 1

    def test_get_status(self, temp_sources_yml):
        """상태 요약"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        status = curator.get_status()

        assert status["total"] == 5
        assert status["active"] == 4  # pending 제외
        assert status["pending"] == 1

    def test_cleanup_dry_run(self, temp_sources_yml):
        """정리 (dry-run)"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        disabled = curator.cleanup(dry_run=True)

        # low_quality가 비활성화 대상
        assert "low_quality" in disabled

        # 실제로 비활성화되지 않음
        sm.load()
        source = sm.get_by_id("low_quality")
        assert source.enabled is True  # 여전히 활성

    def test_cleanup_actual(self, temp_sources_yml):
        """정리 (실제)"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        disabled = curator.cleanup(dry_run=False)

        # 실제로 비활성화됨
        sm.load()
        source = sm.get_by_id("low_quality")
        assert source.enabled is False

    def test_approve(self, temp_sources_yml):
        """승인"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # pending 소스 승인
        result = curator.approve("pending_source")
        assert result is True

        source = sm.get_by_id("pending_source")
        assert source.status == "active"
        assert source.enabled is True

    def test_reject(self, temp_sources_yml):
        """거부"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        result = curator.reject("medium_quality")
        assert result is True

        source = sm.get_by_id("medium_quality")
        assert source.status == "rejected"
        assert source.enabled is False

    def test_report(self, temp_sources_yml):
        """리포트 생성"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        report_text = curator.report()

        assert "# Source Quality Report" in report_text
        assert "high_quality" in report_text

    def test_signal_noise_ratio_rule(self, temp_sources_yml):
        """신호/잡음 비율 규칙"""
        sm = SourceManager(temp_sources_yml)
        curator = SourceCurator(source_manager=sm)

        # 낮은 신호/잡음 비율
        source = SourceMeta(
            id="noisy",
            type="rss",
            url="https://noisy.com",
            category="test",
            signal_noise_ratio=0.1,  # min_signal_noise_ratio (0.2) 미만
        )

        action = curator.apply_rules(source)
        assert action == "disable"
