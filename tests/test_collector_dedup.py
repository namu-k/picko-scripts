"""
Unit tests for duplicate detection in daily_collector
Phase 0.2 implementation tests
"""

from unittest.mock import MagicMock, patch

import pytest

from picko.scoring import ContentScore


class TestDuplicateDetection:
    """Embedding-based duplicate detection tests"""

    @pytest.fixture
    def mock_collector(self, temp_vault_dir, mock_config):
        """DailyCollector mock with duplicate detection"""
        from scripts.daily_collector import DailyCollector

        with patch("scripts.daily_collector.get_config", return_value=mock_config):
            with patch("scripts.daily_collector.get_embedding_manager") as mock_emb:
                with patch("scripts.daily_collector.get_summary_client"):
                    with patch("scripts.daily_collector.ContentScorer"):
                        mock_emb.return_value = MagicMock()
                        mock_emb.return_value.cosine_similarity = lambda a, b: sum(x * y for x, y in zip(a, b)) / (
                            sum(x**2 for x in a) ** 0.5 * sum(y**2 for y in b) ** 0.5
                        )
                        collector = DailyCollector(dry_run=True)
                        return collector

    def test_check_duplicate_no_existing(self, mock_collector):
        """기존 임베딩 없으면 중복 없음"""
        mock_collector._existing_embeddings_with_ids = []
        new_embedding = [0.1, 0.2, 0.3]

        duplicate_of, max_sim = mock_collector._check_duplicate(new_embedding)

        assert duplicate_of is None
        assert max_sim == 0.0

    def test_check_duplicate_low_similarity(self, mock_collector):
        """유사도 낮으면 중복 아님"""
        mock_collector._existing_embeddings_with_ids = [
            ("input_abc123", [0.9, 0.8, 0.7]),
        ]
        new_embedding = [0.1, 0.2, 0.3]

        duplicate_of, max_sim = mock_collector._check_duplicate(new_embedding)

        # 유사도가 낮아야 함 (cosine similarity)
        assert max_sim < 0.92
        assert duplicate_of is not None  # 가장 유사한 것 반환하지만 임계값 미만

    def test_check_duplicate_high_similarity(self, mock_collector):
        """유사도 높으면 중복 감지"""
        # 동일한 임베딩
        mock_collector._existing_embeddings_with_ids = [
            ("input_existing", [0.5, 0.5, 0.5]),
        ]
        new_embedding = [0.5, 0.5, 0.5]  # 동일

        duplicate_of, max_sim = mock_collector._check_duplicate(new_embedding)

        assert max_sim >= 0.99  # 거의 1.0
        assert duplicate_of == "input_existing"

    def test_check_duplicate_multiple_existing(self, mock_collector):
        """여러 기존 임베딩 중 가장 유사한 것 찾기"""
        mock_collector._existing_embeddings_with_ids = [
            ("input_a", [0.1, 0.2, 0.3]),
            ("input_b", [0.9, 0.8, 0.7]),
            ("input_c", [0.5, 0.5, 0.5]),
        ]
        new_embedding = [0.52, 0.48, 0.51]  # input_c와 가장 유사

        duplicate_of, max_sim = mock_collector._check_duplicate(new_embedding)

        assert duplicate_of == "input_c"

    def test_extract_text_for_embedding(self, mock_collector):
        """임베딩용 텍스트 추출"""
        meta = {
            "title": "Test Title",
            "summary": "This is a summary.",
        }

        text = mock_collector._extract_text_for_embedding(meta)

        assert "Test Title" in text
        assert "This is a summary." in text

    def test_extract_text_for_embedding_missing_fields(self, mock_collector):
        """필드 누락시 빈 텍스트"""
        meta: dict[str, str] = {}

        text = mock_collector._extract_text_for_embedding(meta)

        assert text == ""

    def test_score_items_with_duplicate_detection(self, mock_collector):
        """중복 아이템은 status=duplicate로 설정"""
        mock_collector._existing_embeddings_with_ids = [
            ("input_existing", [0.5, 0.5, 0.5]),
        ]
        mock_collector.scorer = MagicMock()
        mock_collector.scorer.score.return_value = ContentScore(
            novelty=0.8, relevance=0.8, quality=0.8, freshness=0.8, total=0.8
        )
        mock_collector.scorer.should_auto_approve.return_value = False
        mock_collector.scorer.should_auto_reject.return_value = False

        items = [
            {
                "url_hash": "abc123",
                "title": "Test",
                "embedding": [0.5, 0.5, 0.5],  # 중복
            },
            {
                "url_hash": "def456",
                "title": "Unique",
                "embedding": [1.0, 0.0, 0.0],  # 완전히 다른 방향 (직교)
            },
        ]

        mock_collector._score(items)

        # 첫 번째는 중복, 두 번째는 정상
        assert items[0].get("status") == "duplicate"
        assert items[1].get("status") != "duplicate"


class TestCosineSimilarity:
    """Cosine similarity calculation tests"""

    def test_identical_vectors(self):
        """동일 벡터는 유사도 1.0"""
        from picko.embedding import EmbeddingManager

        manager = EmbeddingManager.__new__(EmbeddingManager)
        manager.config = MagicMock()
        manager.config.dimensions = 3

        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]

        sim = manager.cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """직교 벡터는 유사도 0.0"""
        from picko.embedding import EmbeddingManager

        manager = EmbeddingManager.__new__(EmbeddingManager)
        manager.config = MagicMock()
        manager.config.dimensions = 3

        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]

        sim = manager.cosine_similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_opposite_vectors(self):
        """반대 벡터는 유사도 -1.0"""
        from picko.embedding import EmbeddingManager

        manager = EmbeddingManager.__new__(EmbeddingManager)
        manager.config = MagicMock()
        manager.config.dimensions = 3

        v1 = [1.0, 0.0, 0.0]
        v2 = [-1.0, 0.0, 0.0]

        sim = manager.cosine_similarity(v1, v2)
        assert abs(sim - (-1.0)) < 0.001
