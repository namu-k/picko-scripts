"""
Unit tests for HumanConfirmationGate
Phase 1.2 implementation tests
"""

from picko.discovery.gates import (
    AUTO_APPROVE_THRESHOLD,
    AUTO_REJECT_THRESHOLD,
    SOCIAL_PLATFORMS,
    GateDecision,
    HumanConfirmationGate,
    PlatformType,
)


class TestHumanConfirmationGate:
    """HumanConfirmationGate tests"""

    def test_init_default(self):
        """기본 초기화"""
        gate = HumanConfirmationGate()
        assert len(gate.trusted_domains) > 0
        assert gate.auto_approve_threshold == AUTO_APPROVE_THRESHOLD

    def test_init_custom_domains(self):
        """커스텀 도메인 설정"""
        gate = HumanConfirmationGate(trusted_domains={"custom.com"})
        assert "custom.com" in gate.trusted_domains

    def test_social_platforms_always_require_review(self):
        """소셜 플랫폼은 항상 사람 검토"""
        gate = HumanConfirmationGate()

        for platform in [
            "threads",
            "reddit",
            "mastodon",
            "instagram",
            "facebook",
            "linkedin",
        ]:
            assert gate.requires_review(platform) is True

    def test_social_platform_types(self):
        """PlatformType으로 소셜 플랫폼 검토"""
        gate = HumanConfirmationGate()

        for platform_type in SOCIAL_PLATFORMS:
            assert gate.requires_review(platform_type) is True

    def test_trusted_domain_high_score_auto_approve(self):
        """신뢰 도메인 + 높은 점수 = 자동 승인"""
        gate = HumanConfirmationGate()

        # techcrunch.com은 신뢰 도메인
        requires_review = gate.requires_review(
            platform="rss",
            domain="techcrunch.com",
            relevance_score=0.92,
        )

        assert requires_review is False

    def test_trusted_domain_low_score_requires_review(self):
        """신뢰 도메인도 낮은 점수면 검토"""
        gate = HumanConfirmationGate()

        requires_review = gate.requires_review(
            platform="rss",
            domain="techcrunch.com",
            relevance_score=0.7,
        )

        assert requires_review is True

    def test_unknown_domain_requires_review(self):
        """알 수 없는 도메인은 검토"""
        gate = HumanConfirmationGate()

        requires_review = gate.requires_review(
            platform="rss",
            domain="unknown-blog.com",
            relevance_score=0.92,
        )

        assert requires_review is True

    def test_low_score_auto_reject(self):
        """매우 낮은 점수는 자동 거절 (검토 없음)"""
        gate = HumanConfirmationGate()

        decision = gate.evaluate(
            platform="rss",
            domain="example.com",
            relevance_score=0.2,
        )

        assert decision.requires_review is False
        assert "too low" in decision.reason.lower()

    def test_is_social_platform(self):
        """소셜 플랫폼 여부 확인"""
        gate = HumanConfirmationGate()

        assert gate.is_social_platform("threads") is True
        assert gate.is_social_platform("reddit") is True
        assert gate.is_social_platform("rss") is False
        assert gate.is_social_platform("web") is False

    def test_is_trusted_domain(self):
        """신뢰 도메인 여부 확인"""
        gate = HumanConfirmationGate()

        assert gate.is_trusted_domain("techcrunch.com") is True
        assert gate.is_trusted_domain("unknown.com") is False

    def test_subdomain_trusted(self):
        """서브도메인도 신뢰"""
        gate = HumanConfirmationGate()

        # openai.com이 신뢰 도메인이면 blog.openai.com도 신뢰
        assert gate.is_trusted_domain("openai.com") is True
        assert gate.is_trusted_domain("blog.openai.com") is True

    def test_add_trusted_domain(self):
        """신뢰 도메인 추가"""
        gate = HumanConfirmationGate(trusted_domains=set())

        gate.add_trusted_domain("new-trusted.com")

        assert gate.is_trusted_domain("new-trusted.com") is True

    def test_remove_trusted_domain(self):
        """신뢰 도메인 제거"""
        gate = HumanConfirmationGate(trusted_domains={"test.com"})

        result = gate.remove_trusted_domain("test.com")

        assert result is True
        assert gate.is_trusted_domain("test.com") is False

    def test_remove_nonexistent_domain(self):
        """존재하지 않는 도메인 제거"""
        gate = HumanConfirmationGate(trusted_domains=set())

        result = gate.remove_trusted_domain("nonexistent.com")

        assert result is False

    def test_evaluate_returns_gate_decision(self):
        """evaluate()는 GateDecision 반환"""
        gate = HumanConfirmationGate()

        decision = gate.evaluate(
            platform="threads",
            domain=None,
            relevance_score=0.8,
        )

        assert isinstance(decision, GateDecision)
        assert decision.requires_review is True
        assert decision.reason != ""

    def test_evaluate_auto_approve_eligible(self):
        """자동 승인 자격 확인"""
        gate = HumanConfirmationGate()

        # 신뢰 도메인 + 높은 점수
        decision = gate.evaluate(
            platform="rss",
            domain="techcrunch.com",
            relevance_score=0.95,
        )

        assert decision.auto_approve_eligible is True

    def test_normalize_platform_string(self):
        """플랫폼 문자열 정규화"""
        gate = HumanConfirmationGate()

        # 소문자 변환
        assert gate._normalize_platform("THREADS") == PlatformType.THREADS
        assert gate._normalize_platform(" Reddit ") == PlatformType.REDDIT

    def test_normalize_platform_unknown(self):
        """알 수 없는 플랫폼은 WEB으로 처리"""
        gate = HumanConfirmationGate()

        result = gate._normalize_platform("unknown_platform")
        assert result == PlatformType.WEB


class TestPlatformType:
    """PlatformType enum tests"""

    def test_social_platforms_count(self):
        """소셜 플랫폼 개수 확인"""
        assert len(SOCIAL_PLATFORMS) >= 6  # threads, reddit, mastodon, instagram, facebook, linkedin

    def test_platform_type_values(self):
        """플랫폼 타입 값 확인"""
        assert PlatformType.THREADS.value == "threads"
        assert PlatformType.REDDIT.value == "reddit"
        assert PlatformType.MASTODON.value == "mastodon"


class TestGateDecision:
    """GateDecision dataclass tests"""

    def test_create_decision(self):
        """결과 생성"""
        decision = GateDecision(
            requires_review=True,
            reason="Test reason",
        )

        assert decision.requires_review is True
        assert decision.auto_approve_eligible is False

    def test_create_with_auto_approve(self):
        """자동 승인 자격 포함"""
        decision = GateDecision(
            requires_review=False,
            reason="Auto-approve eligible",
            auto_approve_eligible=True,
        )

        assert decision.auto_approve_eligible is True


class TestThresholds:
    """임계값 테스트"""

    def test_auto_approve_threshold(self):
        """자동 승인 임계값"""
        assert AUTO_APPROVE_THRESHOLD == 0.9

    def test_auto_reject_threshold(self):
        """자동 거절 임계값"""
        assert AUTO_REJECT_THRESHOLD == 0.3

    def test_custom_thresholds(self):
        """커스텀 임계값"""
        gate = HumanConfirmationGate(
            auto_approve_threshold=0.85,
            auto_reject_threshold=0.2,
        )

        assert gate.auto_approve_threshold == 0.85
        assert gate.auto_reject_threshold == 0.2
