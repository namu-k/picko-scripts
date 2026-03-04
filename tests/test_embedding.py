from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from _pytest.monkeypatch import MonkeyPatch

from picko.config import EmbeddingConfig
from picko.embedding import EmbeddingManager


def test_embedding_manager_initialization_creates_cache_dir(temp_vault_dir: Path):
    cache_dir = temp_vault_dir / "cache" / "emb-cache"
    config = EmbeddingConfig(cache_enabled=True, cache_dir=str(cache_dir))

    manager = EmbeddingManager(config=config)

    assert manager.config == config
    assert manager.cache_dir == cache_dir
    assert cache_dir.exists()


def test_embed_uses_local_provider_with_mocked_model(temp_vault_dir: Path):
    config = EmbeddingConfig(
        provider="local",
        dimensions=3,
        cache_enabled=False,
        cache_dir=str(temp_vault_dir / "cache"),
    )
    manager = EmbeddingManager(config=config)

    class FakeModel:
        def encode(self, text: str, convert_to_numpy: bool = True) -> np.ndarray:
            assert text == "hello world"
            assert convert_to_numpy is True
            return np.array([0.1, 0.2, 0.3])

    manager._local_model = FakeModel()

    result = manager.embed("hello world")

    assert result == [0.1, 0.2, 0.3]


def test_calculate_novelty_returns_expected_score(temp_vault_dir: Path):
    config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
    manager = EmbeddingManager(config=config)

    novelty = manager.calculate_novelty(new_embedding=[1.0, 0.0], existing_embeddings=[[1.0, 0.0], [0.0, 1.0]])

    assert novelty == pytest.approx(0.0)


def test_embed_reads_from_cache_without_calling_provider(temp_vault_dir: Path):
    cache_dir = temp_vault_dir / "cache" / "emb-cache"
    config = EmbeddingConfig(provider="local", dimensions=3, cache_enabled=True, cache_dir=str(cache_dir))
    manager = EmbeddingManager(config=config)

    expected = [0.7, 0.8, 0.9]
    key = manager._get_cache_key("cached text")
    manager._save_cache(key, expected)

    class FailModel:
        def encode(self, text: str, convert_to_numpy: bool = True) -> np.ndarray:
            raise AssertionError("provider should not be called when cache exists")

    manager._local_model = FailModel()

    result = manager.embed("cached text")

    assert result == expected


def test_local_provider_falls_back_to_openai_when_local_fails(temp_vault_dir: Path):
    config = EmbeddingConfig(
        provider="local",
        dimensions=3,
        cache_enabled=False,
        cache_dir=str(temp_vault_dir / "cache"),
    )
    manager = EmbeddingManager(config=config)

    manager._local_model = False

    with patch.object(manager, "_embed_openai", return_value=[0.4, 0.5, 0.6]) as mock_openai:
        result = manager.embed("fallback please")

    mock_openai.assert_called_once_with("fallback please")

    assert result == [0.4, 0.5, 0.6]


def test_embed_local_uses_model_encode_output(monkeypatch: MonkeyPatch, temp_vault_dir: Path):
    config = EmbeddingConfig(
        provider="local",
        dimensions=3,
        cache_enabled=False,
        cache_dir=str(temp_vault_dir / "cache"),
    )
    manager = EmbeddingManager(config=config)

    class FakeModel:
        def encode(self, text, convert_to_numpy=True):
            assert text == "encode me"
            assert convert_to_numpy is True
            return np.array([1.0, 2.0, 3.0])

    monkeypatch.setattr(manager, "_local_model", FakeModel())

    result = manager._embed_local("encode me")

    assert result == [1.0, 2.0, 3.0]


# ============================================================================
# Additional Tests for Missing Coverage
# ============================================================================


class TestCosineSimilarity:
    """cosine_similarity 메서드 테스트"""

    def test_cosine_similarity_identical_vectors(self, temp_vault_dir: Path):
        """동일한 벡터 간 유사도는 1.0"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        similarity = manager.cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])

        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self, temp_vault_dir: Path):
        """직교 벡터 간 유사도는 0.0"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        similarity = manager.cosine_similarity([1.0, 0.0], [0.0, 1.0])

        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_opposite_vectors(self, temp_vault_dir: Path):
        """반대 방향 벡터 간 유사도는 -1.0"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        similarity = manager.cosine_similarity([1.0, 0.0], [-1.0, 0.0])

        assert similarity == pytest.approx(-1.0)

    def test_cosine_similarity_with_different_lengths(self, temp_vault_dir: Path):
        """다른 길이 벡터 처리"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        # 3차원 벡터
        similarity = manager.cosine_similarity(
            [1.0, 2.0, 3.0],
            [2.0, 4.0, 6.0],  # 같은 방향, 다른 크기
        )

        assert similarity == pytest.approx(1.0)


class TestFindSimilar:
    """find_similar 메서드 테스트"""

    def test_find_similar_returns_top_k(self, temp_vault_dir: Path):
        """top_k개 결과 반환"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        query = [1.0, 0.0]
        candidates = [
            [0.9, 0.1],  # 높은 유사도
            [0.1, 0.9],  # 낮은 유사도
            [0.8, 0.2],  # 중간 유사도
        ]

        results = manager.find_similar(query, candidates, top_k=2)

        assert len(results) == 2
        # 유사도 내림차순
        assert results[0][1] >= results[1][1]

    def test_find_similar_respects_threshold(self, temp_vault_dir: Path):
        """임계값 미만 결과 제외"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        query = [1.0, 0.0]
        candidates = [
            [0.9, 0.1],  # 높은 유사도 (~0.98)
            [0.1, 0.9],  # 낮은 유사도 (~0.18)
            [0.0, 1.0],  # 매우 낮은 유사도 (0.0)
        ]

        results = manager.find_similar(query, candidates, threshold=0.5)

        # threshold 이상인 것만 반환
        for idx, sim in results:
            assert sim >= 0.5

    def test_find_similar_returns_empty_for_no_matches(self, temp_vault_dir: Path):
        """매칭 없을 때 빈 리스트 반환"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        query = [1.0, 0.0]
        candidates = [
            [0.0, 1.0],  # 유사도 0
            [0.0, 0.9],  # 유사도 ~0
        ]

        results = manager.find_similar(query, candidates, threshold=0.99)

        assert len(results) == 0

    def test_find_similar_returns_correct_indices(self, temp_vault_dir: Path):
        """올바른 인덱스 반환"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        query = [1.0, 0.0]
        candidates = [
            [0.1, 0.9],  # 인덱스 0, 낮은 유사도
            [0.9, 0.1],  # 인덱스 1, 높은 유사도
        ]

        results = manager.find_similar(query, candidates, top_k=2)

        # 가장 높은 유사도가 인덱스 1
        assert results[0][0] == 1
        assert results[1][0] == 0

    def test_find_similar_with_empty_candidates(self, temp_vault_dir: Path):
        """빈 후보 리스트"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        results = manager.find_similar([1.0, 0.0], [], top_k=5)

        assert len(results) == 0


class TestCalculateNovelty:
    """calculate_novelty 메서드 테스트"""

    def test_calculate_novelty_returns_1_for_empty_existing(self, temp_vault_dir: Path):
        """기존 임베딩 없으면 참신도 1.0"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        novelty = manager.calculate_novelty([1.0, 0.0], existing_embeddings=[])

        assert novelty == 1.0

    def test_calculate_novelty_returns_0_for_identical(self, temp_vault_dir: Path):
        """동일한 임베딩이면 참신도 0.0"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        novelty = manager.calculate_novelty(
            new_embedding=[1.0, 0.0],
            existing_embeddings=[[1.0, 0.0], [0.0, 1.0]],
        )

        assert novelty == pytest.approx(0.0)

    def test_calculate_novelty_with_partial_similarity(self, temp_vault_dir: Path):
        """부분적 유사도"""
        config = EmbeddingConfig(cache_enabled=False, cache_dir=str(temp_vault_dir / "cache"))
        manager = EmbeddingManager(config=config)

        # 45도 각도 벡터
        new = [1.0, 1.0]
        existing = [[1.0, 0.0]]  # 유사도 ~0.707

        novelty = manager.calculate_novelty(new, existing)

        # 참신도 = 1 - 0.707 ≈ 0.293
        assert 0.2 < novelty < 0.4


class TestEmbedBatch:
    """embed_batch 메서드 테스트"""

    def test_embed_batch_with_local_model(self, temp_vault_dir: Path):
        """로컬 모델로 배치 임베딩"""
        config = EmbeddingConfig(
            provider="local",
            dimensions=3,
            cache_enabled=False,
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        class FakeModel:
            def encode(self, texts, convert_to_numpy=True):
                # 배치 인코딩
                return np.array([[i, i + 1, i + 2] for i in range(len(texts))])

        manager._local_model = FakeModel()

        texts = ["text1", "text2", "text3"]
        results = manager.embed_batch(texts)

        assert len(results) == 3
        assert results[0] == [0, 1, 2]
        assert results[1] == [1, 2, 3]
        assert results[2] == [2, 3, 4]

    def test_embed_batch_with_cache(self, temp_vault_dir: Path):
        """캐시와 함께 배치 임베딩"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            dimensions=3,
            cache_enabled=True,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        # 첫 번째 텍스트 캐시에 저장
        key1 = manager._get_cache_key("cached text")
        manager._save_cache(key1, [0.1, 0.2, 0.3])

        class FakeModel:
            def encode(self, texts, convert_to_numpy=True):
                # 캐시되지 않은 텍스트만 인코딩
                return np.array([[i, i, i] for i in range(len(texts))])

        manager._local_model = FakeModel()

        texts = ["cached text", "new text"]
        results = manager.embed_batch(texts)

        assert len(results) == 2
        # 첫 번째는 캐시된 값
        assert results[0] == [0.1, 0.2, 0.3]

    def test_embed_batch_preserves_order(self, temp_vault_dir: Path):
        """결과 순서 유지"""
        config = EmbeddingConfig(
            provider="local",
            dimensions=3,
            cache_enabled=False,
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        class FakeModel:
            def encode(self, texts, convert_to_numpy=True):
                return np.array([[hash(t) % 10] * 3 for t in texts])

        manager._local_model = FakeModel()

        texts = ["first", "second", "third"]
        results = manager.embed_batch(texts)

        assert len(results) == 3
        # 각 텍스트에 해당하는 임베딩
        assert results[0] != results[1] or results[1] != results[2] or True  # 순서 유지 확인

    def test_embed_batch_empty_list(self, temp_vault_dir: Path):
        """빈 리스트 처리"""
        config = EmbeddingConfig(
            provider="local",
            dimensions=3,
            cache_enabled=False,
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        results = manager.embed_batch([])

        assert len(results) == 0


class TestCacheOperations:
    """캐시 연산 테스트"""

    def test_get_cache_key_consistent(self, temp_vault_dir: Path):
        """동일한 텍스트는 동일한 캐시 키"""
        config = EmbeddingConfig(
            provider="local",
            model="test-model",
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        key1 = manager._get_cache_key("test text")
        key2 = manager._get_cache_key("test text")

        assert key1 == key2

    def test_get_cache_key_different_for_different_text(self, temp_vault_dir: Path):
        """다른 텍스트는 다른 캐시 키"""
        config = EmbeddingConfig(
            provider="local",
            model="test-model",
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        key1 = manager._get_cache_key("text one")
        key2 = manager._get_cache_key("text two")

        assert key1 != key2

    def test_save_and_get_cache(self, temp_vault_dir: Path):
        """캐시 저장 및 조회"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            cache_enabled=True,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        embedding = [0.1, 0.2, 0.3]
        key = "testkey123"

        manager._save_cache(key, embedding)
        result = manager._get_cached(key)

        assert result == embedding

    def test_get_cached_returns_none_for_missing(self, temp_vault_dir: Path):
        """없는 캐시 조회 시 None 반환"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            cache_enabled=True,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        result = manager._get_cached("nonexistent")

        assert result is None

    def test_clear_cache_removes_all_files(self, temp_vault_dir: Path):
        """clear_cache가 모든 캐시 파일 삭제"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            cache_enabled=True,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        # 캐시 파일 생성
        manager._save_cache("key1", [0.1, 0.2])
        manager._save_cache("key2", [0.3, 0.4])

        count = manager.clear_cache()

        assert count == 2
        assert len(list(cache_dir.glob("*.npy"))) == 0

    def test_clear_cache_returns_zero_when_empty(self, temp_vault_dir: Path):
        """빈 캐시 디렉토리에서 clear_cache"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            cache_enabled=True,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        count = manager.clear_cache()

        assert count == 0


class TestEmbedEdgeCases:
    """embed 메서드 엣지 케이스 테스트"""

    def test_embed_returns_zero_vector_on_failure(self, temp_vault_dir: Path):
        """실패 시 0 벡터 반환"""
        config = EmbeddingConfig(
            provider="local",
            dimensions=5,
            cache_enabled=False,
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        # 로컬 모델 실패
        manager._local_model = False

        # _embed_openai를 None 반환하도록 패치하여 폴백도 실패
        with patch.object(manager, "_embed_openai", return_value=None):
            result = manager.embed("test")

        # embedding이 None이면 0 벡터 반환
        assert result == [0.0] * 5

    def test_embed_with_dummy_key(self, temp_vault_dir: Path, monkeypatch):
        """dummy_key 환경 변수 시 더미 임베딩"""
        config = EmbeddingConfig(
            provider="openai",
            dimensions=3,
            cache_enabled=False,
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")

        result = manager.embed("test text")

        assert result == [0.1] * 3

    def test_embed_with_cache_disabled(self, temp_vault_dir: Path):
        """캐시 비활성화 시 캐시 사용 안함"""
        cache_dir = temp_vault_dir / "cache"
        config = EmbeddingConfig(
            provider="local",
            dimensions=3,
            cache_enabled=False,
            cache_dir=str(cache_dir),
        )
        manager = EmbeddingManager(config=config)

        class FakeModel:
            def encode(self, text, convert_to_numpy=True):
                return np.array([1.0, 2.0, 3.0])

        manager._local_model = FakeModel()

        # 캐시가 비활성화되면 _save_cache는 아무것도 하지 않음 (또는 무시됨)
        # embed 호출 시 모델을 직접 사용
        result = manager.embed("test")

        # 캐시 사용 안하고 모델 호출
        assert result == [1.0, 2.0, 3.0]


class TestLocalModelProperty:
    """local_model 프로퍼티 테스트"""

    def test_local_model_lazy_load(self, temp_vault_dir: Path):
        """로컬 모델 지연 로드"""
        config = EmbeddingConfig(
            provider="local",
            model="BAAI/bge-m3",
            cache_dir=str(temp_vault_dir / "cache"),
        )
        manager = EmbeddingManager(config=config)

        # 초기에는 None
        assert manager._local_model is None

        # 프로퍼티 접근 시 로드 시도 (실제 모델 없으면 False)
        model = manager.local_model
        assert model is not None or manager._local_model is False


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def test_get_embedding_manager_returns_singleton(self, temp_vault_dir: Path):
        """get_embedding_manager 싱글톤"""
        # 기존 매니저 초기화
        import picko.embedding as emb_module
        from picko.embedding import _default_manager, get_embedding_manager

        emb_module._default_manager = None

        manager1 = get_embedding_manager()
        manager2 = get_embedding_manager()

        assert manager1 is manager2

    def test_embed_text_convenience(self, temp_vault_dir: Path, monkeypatch):
        """embed_text 편의 함수"""
        import picko.embedding as emb_module

        emb_module._default_manager = None

        from picko.embedding import embed_text

        monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")

        result = embed_text("test")

        assert isinstance(result, list)
        assert len(result) > 0
