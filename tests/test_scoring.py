"""
Unit tests for picko.scoring module
"""

import pytest

from picko.scoring import (
    calculate_novelty,
    calculate_relevance,
    calculate_quality,
    calculate_score,
)


class TestCalculateNovelty:
    """calculate_novelty tests"""

    def test_novelty_no_existing(self):
        """기존 콘텐츠 없으면 참신도 1.0"""
        score = calculate_novelty("test content", [])
        assert score == 1.0

    def test_novelty_identical_content(self):
        """동일한 콘텐츠면 참신도 0.0"""
        existing = ["test content"]
        score = calculate_novelty("test content", existing)
        assert score == 0.0

    def test_novelty_different_content(self):
        """완전 다른 콘텐츠면 참신도 높음"""
        existing = ["completely different content"]
        score = calculate_novelty("test content", existing)
        assert score > 0.5


class TestCalculateRelevance:
    """calculate_relevance tests"""

    def test_relevance_no_interests(self):
        """관심 주제 없으면 기본 relevance"""
        account = {"interests": {"primary": [], "secondary": []}}
        score = calculate_relevance(
            "AI and machine learning",
            ["AI", "tech"],
            account
        )
        assert 0 <= score <= 1

    def test_relevance_primary_interest(self):
        """주요 관심사와 일치"""
        account = {
            "interests": {
                "primary": ["AI/머신러닝", "스타트업"],
                "secondary": ["디자인"]
            },
            "keywords": {
                "high_relevance": ["ChatGPT", "Claude"],
                "medium_relevance": ["생산성"],
                "low_relevance": ["테크"]
            }
        }
        score = calculate_relevance(
            "ChatGPT와 AI 기술의 발전",
            ["AI", "ChatGPT"],
            account
        )
        assert score > 0.5

    def test_relevance_secondary_interest(self):
        """2차 관심사와 일치"""
        account = {
            "interests": {
                "primary": ["AI/머신러닝"],
                "secondary": ["디자인", "마케팅"]
            },
            "keywords": {
                "high_relevance": ["ChatGPT"],
                "medium_relevance": ["디자인"],
                "low_relevance": ["테크"]
            }
        }
        score = calculate_relevance(
            "디자인 트렌드 2024",
            ["디자인"],
            account
        )
        # 2차 관심사이므로 주요 관심사보다 낮음
        assert score > 0


class TestCalculateQuality:
    """calculate_quality tests"""

    def test_quality_perfect(self):
        """완벽한 품질 점수"""
        score = calculate_quality(
            "A Perfect Title for Quality Content",
            2000,  # 본문 길이
            "techcrunch.com",  # 신뢰할 수 있는 소스
            ["AI", "tech"]  # 태그 있음
        )
        assert score > 0.5

    def test_quality_poor(self):
        """낮은 품질 점수"""
        score = calculate_quality(
            "short",  # 너무 짧은 제목
            50,  # 너무 짧은 본문
            "unknown.com",  # 알 수 없는 소스
            []  # 태그 없음
        )
        assert score < 0.5

    def test_quality_no_trusted_source(self):
        """신뢰 소스 설정 없을 때"""
        score = calculate_quality(
            "Good Title",
            1000,
            "techcrunch.com",
            ["tech"],
            trusted_sources=[]
        )
        assert 0 <= score <= 1


class TestCalculateScore:
    """calculate_score tests"""

    def test_calculate_score_weights(self):
        """가중치가 적용된 종합 점수"""
        result = calculate_score(
            novelty=0.8,
            relevance=0.7,
            quality=0.6,
            weights={"novelty": 0.3, "relevance": 0.4, "quality": 0.3}
        )
        # 0.8 * 0.3 + 0.7 * 0.4 + 0.6 * 0.3 = 0.69
        assert abs(result["total"] - 0.69) < 0.01
        assert result["novelty"] == 0.8
        assert result["relevance"] == 0.7
        assert result["quality"] == 0.6

    def test_calculate_score_custom_weights(self):
        """사용자 정의 가중치"""
        result = calculate_score(
            novelty=1.0,
            relevance=0.5,
            quality=0.5,
            weights={"novelty": 0.5, "relevance": 0.25, "quality": 0.25}
        )
        # 1.0 * 0.5 + 0.5 * 0.25 + 0.5 * 0.25 = 0.625
        assert abs(result["total"] - 0.625) < 0.01

    def test_calculate_score_thresholds(self):
        """임계값 적용"""
        result = calculate_score(
            novelty=0.9,
            relevance=0.9,
            quality=0.9,
            weights={"novelty": 0.3, "relevance": 0.4, "quality": 0.3},
            thresholds={"auto_approve": 0.85}
        )
        assert result["total"] > 0.85
        assert result.get("should_auto_approve") is True
