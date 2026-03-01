"""
Unit tests for auto-approve/reject quality gates in scoring module
Phase 0.1 implementation tests
"""

from picko.scoring import ContentScore, ContentScorer


class TestAutoApproveRejectGates:
    """Auto-approve/reject thresholds tests"""

    def test_should_auto_approve_high_score(self):
        """높은 점수는 자동 승인되어야 함"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.9,
            relevance=0.9,
            quality=0.9,
            freshness=0.9,
            total=0.88,
        )
        assert scorer.should_auto_approve(score) is True

    def test_should_auto_approve_exactly_threshold(self):
        """정확히 임계값이면 자동 승인"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.85,
            relevance=0.85,
            quality=0.85,
            freshness=0.85,
            total=0.85,
        )
        assert scorer.should_auto_approve(score) is True

    def test_should_auto_approve_below_threshold(self):
        """임계값 미만이면 자동 승인 안됨"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.8,
            relevance=0.8,
            quality=0.8,
            freshness=0.8,
            total=0.84,
        )
        assert scorer.should_auto_approve(score) is False

    def test_should_auto_reject_low_score(self):
        """낮은 점수는 자동 거절되어야 함"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.2,
            relevance=0.2,
            quality=0.2,
            freshness=0.2,
            total=0.25,
        )
        assert scorer.should_auto_reject(score) is True

    def test_should_auto_reject_exactly_threshold(self):
        """정확히 거절 임계값이면 자동 거절"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.3,
            relevance=0.3,
            quality=0.3,
            freshness=0.3,
            total=0.3,
        )
        assert scorer.should_auto_reject(score) is True

    def test_should_auto_reject_above_threshold(self):
        """거절 임계값 초과면 자동 거절 안됨"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.4,
            relevance=0.4,
            quality=0.4,
            freshness=0.4,
            total=0.35,
        )
        assert scorer.should_auto_reject(score) is False

    def test_middle_score_neither_approve_nor_reject(self):
        """중간 점수는 승인도 거절도 안됨"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.5,
            relevance=0.5,
            quality=0.5,
            freshness=0.5,
            total=0.5,
        )
        assert scorer.should_auto_approve(score) is False
        assert scorer.should_auto_reject(score) is False

    def test_custom_thresholds(self):
        """커스텀 임계값 테스트"""
        # ContentScorer는 config를 통해 thresholds를 받음
        # 기본 thresholds 확인
        scorer = ContentScorer()
        assert scorer.thresholds.get("auto_approve") == 0.85
        assert scorer.thresholds.get("auto_reject") == 0.3
        """최소 표시 임계값 이상이면 표시"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.5,
            relevance=0.5,
            quality=0.5,
            freshness=0.5,
            total=0.45,
        )
        assert scorer.should_display(score) is True

    def test_should_display_below_minimum(self):
        """최소 표시 임계값 미만이면 표시 안됨"""
        scorer = ContentScorer()
        score = ContentScore(
            novelty=0.3,
            relevance=0.3,
            quality=0.3,
            freshness=0.3,
            total=0.35,
        )
        assert scorer.should_display(score) is False
