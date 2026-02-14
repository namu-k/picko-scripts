"""
임베딩 생성 및 관리 모듈
"""

import hashlib
import os
from pathlib import Path

import numpy as np

from .config import EmbeddingConfig, get_config
from .logger import get_logger

logger = get_logger("embedding")


class EmbeddingManager:
    """임베딩 생성 및 캐시 관리"""

    def __init__(self, config: EmbeddingConfig | None = None):
        if config is None:
            config = get_config().embedding

        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self._client = None
        self._local_model = None

        if config.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"EmbeddingManager initialized: {config.provider}/{config.model}")

    @property
    def client(self):
        """OpenAI 클라이언트 (lazy 로드)"""
        if self._client is None:
            from openai import OpenAI

            api_key = os.environ.get(self.config.fallback_api_key_env, "")
            self._client = OpenAI(api_key=api_key)
        return self._client

    @property
    def local_model(self):
        """로컬 임베딩 모델 (lazy 로드)"""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                device = self.config.device if hasattr(self.config, "device") else "cpu"
                self._local_model = SentenceTransformer(self.config.model, device=device)
                logger.info(f"Loaded local embedding model: {self.config.model}")
            except Exception as e:
                logger.warning(f"Failed to load local model {self.config.model}: {e}")
                self._local_model = False  # 실패 표시
        return self._local_model if self._local_model is not False else None

    def embed(self, text: str, use_cache: bool = True) -> list[float]:
        """
        텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트
            use_cache: 캐시 사용 여부

        Returns:
            임베딩 벡터
        """
        # 캐시 확인
        if self.config.cache_enabled and use_cache:
            cache_key = self._get_cache_key(text)
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug("Using cached embedding")
                return cached

        # Dummy embedding for testing
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key == "dummy_key":
            return [0.1] * self.config.dimensions

        # 프로바이더별 임베딩 생성
        embedding = None

        # 1. 로컬 모델 시도 (sentence-transformers)
        if self.config.provider == "local":
            embedding = self._embed_local(text)
            if embedding is None and hasattr(self.config, "fallback_provider"):
                # 폴백: OpenAI
                logger.info("Local model failed, falling back to OpenAI")
                embedding = self._embed_openai(text)

        # 2. Ollama
        elif self.config.provider == "ollama":
            embedding = self._embed_ollama(text)

        # 3. OpenAI (default)
        else:
            embedding = self._embed_openai(text)

        # 실패 시 빈 벡터 반환
        if embedding is None:
            logger.warning("Failed to generate embedding, returning zero vector")
            return [0.0] * self.config.dimensions

        # 캐시 저장
        if self.config.cache_enabled and use_cache:
            cache_key = self._get_cache_key(text)
            self._save_cache(cache_key, embedding)

        return embedding

    def _embed_local(self, text: str) -> list[float] | None:
        """로컬 sentence-transformers 임베딩 생성"""
        try:
            model = self.local_model
            if model is None:
                return None

            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Local embedding failed: {e}")
            return None

    def _embed_openai(self, text: str) -> list[float]:
        """OpenAI 임베딩 생성"""
        response = self.client.embeddings.create(
            model=getattr(self.config, "fallback_model", "text-embedding-3-small"), input=text
        )
        return response.data[0].embedding

    def _embed_ollama(self, text: str) -> list[float]:
        """Ollama 임베딩 생성"""
        import ollama

        base_url = getattr(self.config, "base_url", "http://localhost:11434")
        client = ollama.Client(host=base_url)
        response = client.embeddings(model=self.config.model, prompt=text)
        return response["embedding"]

    def embed_batch(self, texts: list[str], use_cache: bool = True) -> list[list[float]]:
        """
        배치 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 리스트
            use_cache: 캐시 사용 여부

        Returns:
            임베딩 벡터 리스트
        """
        results = []
        uncached_indices = []
        uncached_texts = []

        # 캐시된 것 먼저 처리
        if self.config.cache_enabled and use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                cached = self._get_cached(cache_key)
                if cached is not None:
                    results.append((i, cached))
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # 캐시 미스분 처리
        if uncached_texts:
            # 로컬 모델 사용 (배치 처리 효율적)
            if self.config.provider == "local":
                model = self.local_model
                if model is not None:
                    try:
                        embeddings = model.encode(uncached_texts, convert_to_numpy=True)
                        for j, emb in enumerate(embeddings):
                            idx = uncached_indices[j]
                            results.append((idx, emb.tolist()))

                            # 캐시 저장
                            if self.config.cache_enabled and use_cache:
                                cache_key = self._get_cache_key(uncached_texts[j])
                                self._save_cache(cache_key, emb.tolist())
                    except Exception as e:
                        logger.warning(f"Batch local embedding failed: {e}")
                        # 개별 처리로 폴백
                        for j, text in enumerate(uncached_texts):
                            emb = self.embed(text, use_cache=False)
                            idx = uncached_indices[j]
                            results.append((idx, emb))

            # Ollama (개별 처리)
            elif self.config.provider == "ollama":
                for j, text in enumerate(uncached_texts):
                    emb = self._embed_ollama(text)
                    idx = uncached_indices[j]
                    results.append((idx, emb))

                    # 캐시 저장
                    if self.config.cache_enabled and use_cache:
                        cache_key = self._get_cache_key(text)
                        self._save_cache(cache_key, emb)

            # OpenAI (배치 API 지원)
            else:
                response = self.client.embeddings.create(
                    model=getattr(self.config, "fallback_model", "text-embedding-3-small"), input=uncached_texts
                )

                for j, data in enumerate(response.data):
                    idx = uncached_indices[j]
                    embedding = data.embedding
                    results.append((idx, embedding))

                    # 캐시 저장
                    if self.config.cache_enabled and use_cache:
                        cache_key = self._get_cache_key(uncached_texts[j])
                        self._save_cache(cache_key, embedding)

        # 인덱스 순서대로 정렬
        results.sort(key=lambda x: x[0])
        return [emb for _, emb in results]

    # ─────────────────────────────────────────────────────────────
    # 유사도 계산
    # ─────────────────────────────────────────────────────────────

    def cosine_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        두 임베딩 간 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩
            embedding2: 두 번째 임베딩

        Returns:
            유사도 (0~1)
        """
        a = np.array(embedding1)
        b = np.array(embedding2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def find_similar(
        self,
        query_embedding: list[float],
        candidate_embeddings: list[list[float]],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[int, float]]:
        """
        유사한 임베딩 검색

        Args:
            query_embedding: 쿼리 임베딩
            candidate_embeddings: 후보 임베딩 리스트
            top_k: 반환할 최대 개수
            threshold: 최소 유사도

        Returns:
            (인덱스, 유사도) 튜플 리스트 (유사도 내림차순)
        """
        similarities = []
        for i, emb in enumerate(candidate_embeddings):
            sim = self.cosine_similarity(query_embedding, emb)
            if sim >= threshold:
                similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def calculate_novelty(self, new_embedding: list[float], existing_embeddings: list[list[float]]) -> float:
        """
        새 콘텐츠의 참신도 계산 (기존 콘텐츠와의 최대 유사도 기반)

        Args:
            new_embedding: 새 콘텐츠 임베딩
            existing_embeddings: 기존 콘텐츠 임베딩들

        Returns:
            참신도 점수 (0~1, 높을수록 참신)
        """
        if not existing_embeddings:
            return 1.0  # 기존 콘텐츠 없으면 완전 참신

        # 가장 유사한 기존 콘텐츠와의 유사도
        max_similarity = 0.0
        for emb in existing_embeddings:
            sim = self.cosine_similarity(new_embedding, emb)
            max_similarity = max(max_similarity, sim)

        # 참신도 = 1 - 최대유사도
        return 1.0 - max_similarity

    # ─────────────────────────────────────────────────────────────
    # 캐싱 로직
    # ─────────────────────────────────────────────────────────────

    def _get_cache_key(self, text: str) -> str:
        """캐시 키 생성"""
        content = f"{self.config.model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> list[float] | None:
        """캐시 조회"""
        cache_file = self.cache_dir / f"{key}.npy"
        if cache_file.exists():
            try:
                return np.load(cache_file).tolist()
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, embedding: list[float]) -> None:
        """캐시 저장"""
        cache_file = self.cache_dir / f"{key}.npy"
        np.save(cache_file, np.array(embedding))

    def clear_cache(self) -> int:
        """캐시 전체 삭제"""
        if not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.npy"):
            cache_file.unlink()
            count += 1

        logger.info(f"Cleared {count} cached embeddings")
        return count


# 편의 함수
_default_manager: EmbeddingManager | None = None


def get_embedding_manager() -> EmbeddingManager:
    """기본 EmbeddingManager 반환"""
    global _default_manager
    if _default_manager is None:
        _default_manager = EmbeddingManager()
    return _default_manager


def embed_text(text: str) -> list[float]:
    """텍스트 임베딩 (편의 함수)"""
    return get_embedding_manager().embed(text)
