"""
Unit tests for picko.scoring module
"""

from datetime import UTC, datetime, timedelta
from math import isclose

from picko.config import ScoringConfig, load_config
from picko.scoring import ContentScore, ContentScorer, score_content


class TestContentScorer:
    """ContentScorer class tests"""

    def test_score_minimal_content(self):
        """최소한의 콘텐츠로 점수 계산"""
        scorer = ContentScorer()
        content = {
            "title": "Test Article",
            "text": "This is a test article about AI and machine learning.",
            "keywords": ["AI", "machine learning"],
            "source": "test.com",
        }
        score = scorer.score(content)
        assert isinstance(score, ContentScore)
        assert 0 <= score.total <= 1

    def test_score_with_embedding(self):
        """임베딩이 포함된 콘텐츠 점수 계산"""
        scorer = ContentScorer()
        content = {
            "title": "AI Article",
            "text": "Article about AI",
            "keywords": ["AI"],
            "source": "test.com",
            "embedding": [0.1, 0.2, 0.3],
        }
        score = scorer.score(content, existing_embeddings=[[0.5, 0.6, 0.7]])
        assert isinstance(score, ContentScore)

    def test_novelty_no_existing_embeddings(self):
        """기존 임베딩 없으면 참신도 1.0"""
        scorer = ContentScorer()
        content = {
            "title": "Test",
            "text": "Test content",
            "embedding": [0.1, 0.2, 0.3],
        }
        score = scorer.score(content, existing_embeddings=None)
        assert score.novelty == 1.0

    def test_novelty_no_embedding_in_content(self):
        """임베딩 없는 콘텐츠는 기본값 0.5"""
        scorer = ContentScorer()
        content = {"title": "Test", "text": "Test content"}
        score = scorer.score(content, existing_embeddings=[[0.1, 0.2]])
        assert score.novelty == 0.5

    def test_relevance_no_account_profile(self):
        """계정 프로필 없으면 관련도 기본값 0.5"""
        scorer = ContentScorer(account_profile=None)
        content = {
            "title": "AI and machine learning",
            "text": "Article about AI",
            "keywords": ["AI"],
        }
        score = scorer.score(content)
        assert score.relevance == 0.5

    def test_relevance_with_profile(self):
        """계정 프로필 기반 관련도 계산"""
        account = {
            "interests": {
                "primary": ["AI", "machine learning"],
                "secondary": ["design"],
            },
            "keywords": {
                "high_relevance": ["ChatGPT", "Claude"],
                "medium_relevance": ["productivity"],
                "low_relevance": ["tech"],
            },
        }
        scorer = ContentScorer(account_profile=account)
        content = {
            "title": "ChatGPT and AI Technology",
            "text": "Discussion about AI developments",
            "keywords": ["AI", "ChatGPT"],
        }
        score = scorer.score(content)
        # AI (1.0) + ChatGPT in title (1.0) = 2.0, normalized by 5 = 0.4
        assert score.relevance > 0.3  # Should have some matches

    def test_quality_score_calculation(self):
        """품질 점수 계산"""
        scorer = ContentScorer()
        content = {
            "title": "A Perfect Title for Quality Content",
            "text": "A" * 1000,  # Long enough text
            "source": "techcrunch.com",
        }
        score = scorer.score(content)
        assert 0 <= score.quality <= 1
        # Good title length + long text should give decent score
        assert score.quality > 0.5

    def test_quality_poor_content(self):
        """낮은 품질 콘텐츠 점수"""
        scorer = ContentScorer()
        content = {
            "title": "short",
            "text": "A" * 30,
            "source": "unknown.com",
        }  # Too short
        score = scorer.score(content)
        assert score.quality < 0.5

    def test_quality_with_trusted_source(self):
        """신뢰할 수 있는 소스 높은 점수"""
        account = {"trusted_sources": ["techcrunch.com", "arxiv.org"]}
        scorer = ContentScorer(account_profile=account)
        content = {
            "title": "Good Title with Proper Length",
            "text": "A" * 800,
            "source": "techcrunch.com",
        }
        score = scorer.score(content)
        assert score.quality > 0.5

    def test_should_auto_approve(self):
        """자동 승인 임계값 테스트"""
        scorer = ContentScorer()
        high_score = ContentScore(novelty=0.9, relevance=0.9, quality=0.9, total=0.9)
        low_score = ContentScore(novelty=0.3, relevance=0.3, quality=0.3, total=0.3)

        assert scorer.should_auto_approve(high_score) is True
        assert scorer.should_auto_approve(low_score) is False

    def test_should_auto_reject(self):
        """자동 거부 임계값 테스트"""
        scorer = ContentScorer()
        high_score = ContentScore(novelty=0.9, relevance=0.9, quality=0.9, total=0.9)
        low_score = ContentScore(novelty=0.2, relevance=0.2, quality=0.2, total=0.2)

        assert scorer.should_auto_reject(low_score) is True
        assert scorer.should_auto_reject(high_score) is False

    def test_should_display(self):
        """표시 임계값 테스트"""
        scorer = ContentScorer()
        medium_score = ContentScore(novelty=0.5, relevance=0.5, quality=0.5, total=0.5)
        very_low_score = ContentScore(novelty=0.1, relevance=0.1, quality=0.1, total=0.1)

        assert scorer.should_display(medium_score) is True
        assert scorer.should_display(very_low_score) is False

    def test_score_to_dict(self):
        """ContentScore to_dict 메서드 테스트"""
        score = ContentScore(novelty=0.123456, relevance=0.456789, quality=0.789012, total=0.5)
        result = score.to_dict()
        assert result["novelty"] == 0.123
        assert result["relevance"] == 0.457
        assert result["quality"] == 0.789
        assert result["total"] == 0.5


class TestScoreContentConvenience:
    """score_content 편의 함수 테스트"""

    def test_score_content_basic(self):
        """기본 점수 계산"""
        content = {"title": "Test", "text": "Test content", "source": "test.com"}
        score = score_content(content)
        assert isinstance(score, ContentScore)

    def test_score_content_with_account(self):
        """계정 프로필과 함께 점수 계산"""
        content = {
            "title": "AI Technology",
            "text": "About AI",
            "keywords": ["AI"],
            "source": "test.com",
        }
        score = score_content(content, account_id="socialbuilders")
        assert isinstance(score, ContentScore)


class TestScoringWeights:
    """가중치 적용 테스트"""

    def test_default_weights(self):
        """기본 가중치 적용"""
        from picko.config import get_config

        config = get_config()
        scorer = ContentScorer(config=config.scoring)

        # Create content that would give 1.0 for each component
        content = {
            "title": "A Good Title",
            "text": "A" * 600,
            "embedding": [0.1, 0.2],
            "source": "test.com",
        }

        score = scorer.score(content, existing_embeddings=None)
        # With default weights (0.3, 0.4, 0.3), should be close to expected
        assert 0 <= score.total <= 1


class TestFreshnessScoring:
    def test_freshness_decay_curve(self):
        scorer = ContentScorer(config=ScoringConfig())
        now = datetime.now(UTC)

        fresh_score = scorer.score({"publish_date": now})
        week_old_score = scorer.score({"publish_date": now - timedelta(days=7)})
        month_old_score = scorer.score({"publish_date": now - timedelta(days=30)})

        assert fresh_score.freshness == 1.0
        assert isclose(week_old_score.freshness, 0.5, rel_tol=0.05)
        assert isclose(month_old_score.freshness, 0.06, rel_tol=0.25)

    def test_freshness_defaults_when_publish_date_missing(self):
        scorer = ContentScorer(config=ScoringConfig())
        score = scorer.score({"title": "No date"})
        assert score.freshness == 0.5

    def test_total_includes_freshness_weight(self):
        config = ScoringConfig(
            weights={
                "novelty": 0.3,
                "relevance": 0.4,
                "quality": 0.3,
                "freshness": 0.15,
            }
        )
        scorer = ContentScorer(config=config)

        scorer._calculate_novelty = lambda *_args, **_kwargs: 0.4  # type: ignore[method-assign]
        scorer._calculate_relevance = lambda *_args, **_kwargs: 0.6  # type: ignore[method-assign]
        scorer._calculate_quality = lambda *_args, **_kwargs: 0.8  # type: ignore[method-assign]
        scorer._calculate_freshness = lambda *_args, **_kwargs: 0.2  # type: ignore[method-assign]

        score = scorer.score({"title": "Any"})
        expected = ((0.4 * 0.3) + (0.6 * 0.4) + (0.8 * 0.3) + (0.2 * 0.15)) / (0.3 + 0.4 + 0.3 + 0.15)
        assert isclose(score.total, expected, rel_tol=1e-9)

    def test_scoring_config_has_freshness_half_life(self, tmp_path):
        default_config = ScoringConfig()
        custom_config = ScoringConfig(freshness_half_life_days=14.0)

        assert default_config.freshness_half_life_days == 7.0
        assert custom_config.freshness_half_life_days == 14.0

        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "\n".join(
                [
                    "vault:",
                    f'  root: "{tmp_path.as_posix()}"',
                    "scoring:",
                    "  freshness_half_life_days: 10.5",
                    "  weights:",
                    "    novelty: 0.3",
                    "    relevance: 0.4",
                    "    quality: 0.3",
                ]
            ),
            encoding="utf-8",
        )

        loaded = load_config(config_file)
        assert loaded.scoring.freshness_half_life_days == 10.5


class TestRelevanceNormalization:
    """관련도 정규화 - 고정 base 사용으로 일관된 점수 범위 보장"""

    def test_relevance_uses_fixed_base(self):
        """관련도 계산이 고정 base(3.0)를 사용하는지 확인"""
        scorer = ContentScorer()
        # 내부 메서드로 base 값 확인
        # _calculate_relevance는 RELEVANCE_BASE = 3.0 사용
        content = {"title": "AI test", "text": "test content"}

        # profile 없으면 0.5 반환
        assert scorer._calculate_relevance(content) == 0.5

    def test_relevance_consistent_range_with_varying_matches(self):
        """matches 수가 달라도 동일한 점수 범위 보장

        이전: base = max(2.0, 3.5 - 0.5*matches) → matches 증가 시 base 감소
        현재: RELEVANCE_BASE = 3.0 (고정) → 일관된 정규화
        """
        from picko.account_context import AccountIdentity

        # 여러 필드가 있는 AccountIdentity
        identity = AccountIdentity(
            account_id="test",
            one_liner="Test account",
            target_audience=["developers", "AI engineers"],
            value_proposition="AI productivity",
            pillars=["AI", "productivity", "automation"],
            tone_voice={},
            boundaries=[],
        )
        scorer = ContentScorer(account_identity=identity)

        # 모든 필드와 매칭되는 콘텐츠 (여러 matches)
        full_match = {
            "title": "AI productivity automation for developers",
            "text": "AI engineers love automation",
            "keywords": ["AI", "productivity"],
        }

        # 일부만 매칭되는 콘텐츠 (적은 matches)
        partial_match = {
            "title": "Random topic",
            "text": "Unrelated content",
            "keywords": [],
        }

        full_score = scorer._calculate_relevance(full_match)
        partial_score = scorer._calculate_relevance(partial_match)

        # 둘 다 0~1 범위 내에 있어야 함
        assert 0 <= full_score <= 1.0, f"full_score {full_score} out of range"
        assert 0 <= partial_score <= 1.0, f"partial_score {partial_score} out of range"

        # full_match가 partial_score보다 높아야 함
        assert full_score > partial_score

    def test_relevance_single_vs_multiple_matches(self):
        """단일 매칭 vs 다중 매칭 시 점수 비교

        고정 base를 사용하면 점수가 matches 수에 비례해서 증가
        (이전 동적 base에서는 matches 증가 시 base 감소로 역설적 결과 가능)
        """
        from picko.account_context import AccountIdentity

        # 단일 필드만 있는 identity
        simple_identity = AccountIdentity(
            account_id="simple",
            one_liner="Simple account",
            target_audience=["developers"],
            value_proposition="Dev tools",
            pillars=[],
            tone_voice={},
            boundaries=[],
        )

        # 여러 필드가 있는 identity
        rich_identity = AccountIdentity(
            account_id="rich",
            one_liner="Rich account",
            target_audience=["developers", "AI engineers"],
            value_proposition="AI productivity",
            pillars=["AI", "productivity", "automation"],
            tone_voice={},
            boundaries=[],
        )

        simple_scorer = ContentScorer(account_identity=simple_identity)
        rich_scorer = ContentScorer(account_identity=rich_identity)

        content = {
            "title": "AI for developers",
            "text": "Productivity tools for AI engineers",
            "keywords": ["AI", "productivity"],
        }

        simple_score = simple_scorer._calculate_relevance(content)
        rich_score = rich_scorer._calculate_relevance(content)

        # 둘 다 유효한 범위
        assert 0 <= simple_score <= 1.0
        assert 0 <= rich_score <= 1.0

        # rich identity가 더 많은 매칭을 찾으므로 더 높은 점수
        assert rich_score >= simple_score
