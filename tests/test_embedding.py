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
