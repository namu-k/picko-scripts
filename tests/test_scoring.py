"""
Unit tests for picko.scoring module
"""

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
        content = {"title": "Test", "text": "Test content", "embedding": [0.1, 0.2, 0.3]}
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
        content = {"title": "AI and machine learning", "text": "Article about AI", "keywords": ["AI"]}
        score = scorer.score(content)
        assert score.relevance == 0.5

    def test_relevance_with_profile(self):
        """계정 프로필 기반 관련도 계산"""
        account = {
            "interests": {"primary": ["AI", "machine learning"], "secondary": ["design"]},
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
        content = {"title": "short", "text": "A" * 30, "source": "unknown.com"}  # Too short
        score = scorer.score(content)
        assert score.quality < 0.5

    def test_quality_with_trusted_source(self):
        """신뢰할 수 있는 소스 높은 점수"""
        account = {"trusted_sources": ["techcrunch.com", "arxiv.org"]}
        scorer = ContentScorer(account_profile=account)
        content = {"title": "Good Title with Proper Length", "text": "A" * 800, "source": "techcrunch.com"}
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
        content = {"title": "AI Technology", "text": "About AI", "keywords": ["AI"], "source": "test.com"}
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
        content = {"title": "A Good Title", "text": "A" * 600, "embedding": [0.1, 0.2], "source": "test.com"}

        score = scorer.score(content, existing_embeddings=None)
        # With default weights (0.3, 0.4, 0.3), should be close to expected
        assert 0 <= score.total <= 1
