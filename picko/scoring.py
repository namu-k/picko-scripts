"""
점수 계산 모듈
novelty, relevance, quality, total 점수 계산
"""

from dataclasses import dataclass

from .config import ScoringConfig, get_config
from .embedding import get_embedding_manager
from .logger import get_logger

logger = get_logger("scoring")


@dataclass
class ContentScore:
    """콘텐츠 점수"""

    novelty: float = 0.0
    relevance: float = 0.0
    quality: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict:
        return {
            "novelty": round(self.novelty, 3),
            "relevance": round(self.relevance, 3),
            "quality": round(self.quality, 3),
            "total": round(self.total, 3),
        }


class ContentScorer:
    """콘텐츠 점수 계산기"""

    def __init__(self, config: ScoringConfig = None, account_profile: dict = None):
        if config is None:
            config = get_config().scoring

        self.config = config
        self.weights = config.weights
        self.thresholds = config.thresholds
        self.account_profile = account_profile or {}
        self.embedding_manager = get_embedding_manager()

        logger.debug(f"ContentScorer initialized with weights: {self.weights}")

    def score(self, content: dict, existing_embeddings: list[list[float]] = None) -> ContentScore:
        """
        콘텐츠 점수 계산

        Args:
            content: 콘텐츠 정보 (title, text, embedding, source 등)
            existing_embeddings: 기존 콘텐츠 임베딩들 (novelty 계산용)

        Returns:
            ContentScore 인스턴스
        """
        novelty = self._calculate_novelty(content, existing_embeddings)
        relevance = self._calculate_relevance(content)
        quality = self._calculate_quality(content)

        total = (
            novelty * self.weights.get("novelty", 0.3)
            + relevance * self.weights.get("relevance", 0.4)
            + quality * self.weights.get("quality", 0.3)
        )

        score = ContentScore(novelty=novelty, relevance=relevance, quality=quality, total=total)

        logger.debug(f"Scored content: {score.to_dict()}")
        return score

    def _calculate_novelty(self, content: dict, existing_embeddings: list[list[float]] = None) -> float:
        """
        참신도 계산 (기존 콘텐츠와의 유사도 기반)

        Args:
            content: 콘텐츠 (embedding 키 필요)
            existing_embeddings: 기존 콘텐츠 임베딩들

        Returns:
            참신도 점수 (0~1)
        """
        if existing_embeddings is None or not existing_embeddings:
            return 1.0  # 기존 콘텐츠 없으면 완전 참신

        embedding = content.get("embedding")
        if embedding is None:
            logger.warning("No embedding in content, defaulting novelty to 0.5")
            return 0.5

        return self.embedding_manager.calculate_novelty(embedding, existing_embeddings)

    def _calculate_relevance(self, content: dict) -> float:
        """
        관련도 계산 (계정 프로필 기반)

        Args:
            content: 콘텐츠 (title, text, keywords 등)

        Returns:
            관련도 점수 (0~1)
        """
        if not self.account_profile:
            return 0.5  # 프로필 없으면 중립

        # 텍스트 결합
        text = (
            content.get("title", "") + " " + content.get("text", "") + " " + " ".join(content.get("keywords", []))
        ).lower()

        score = 0.0
        matches = 0

        # 관심 주제 매칭
        interests = self.account_profile.get("interests", {})

        # 주 관심사 (가중치 1.0)
        for interest in interests.get("primary", []):
            if interest.lower() in text:
                score += 1.0
                matches += 1

        # 부 관심사 (가중치 0.5)
        for interest in interests.get("secondary", []):
            if interest.lower() in text:
                score += 0.5
                matches += 1

        # 키워드 매칭
        keywords = self.account_profile.get("keywords", {})

        for kw in keywords.get("high_relevance", []):
            if kw.lower() in text:
                score += 1.0
                matches += 1

        for kw in keywords.get("medium_relevance", []):
            if kw.lower() in text:
                score += 0.5
                matches += 1

        for kw in keywords.get("low_relevance", []):
            if kw.lower() in text:
                score += 0.2
                matches += 1

        # 정규화 (최대 5개 매칭 기준)
        if matches == 0:
            return 0.3  # 매칭 없으면 낮은 점수

        normalized = min(score / 5.0, 1.0)
        return normalized

    def _calculate_quality(self, content: dict) -> float:
        """
        품질 점수 계산 (휴리스틱 기반)

        Args:
            content: 콘텐츠

        Returns:
            품질 점수 (0~1)
        """
        score = 0.5  # 기본 점수

        # 제목 길이 (10~60자가 적당)
        title = content.get("title", "")
        title_len = len(title)
        if 10 <= title_len <= 60:
            score += 0.1
        elif title_len > 100 or title_len < 5:
            score -= 0.1

        # 본문 길이 (200자 이상이면 실질적 콘텐츠)
        text = content.get("text", "")
        text_len = len(text)
        if text_len >= 500:
            score += 0.2
        elif text_len >= 200:
            score += 0.1
        elif text_len < 50:
            score -= 0.2

        # 소스 신뢰도 (설정에서 정의 가능)
        source = content.get("source", "")
        trusted_sources = self.account_profile.get("trusted_sources", [])
        if source in trusted_sources:
            score += 0.1

        # 발행일 (최근일수록 높은 점수)
        # publish_date = content.get("publish_date")
        # if publish_date: 날짜 계산 로직...

        return max(0.0, min(1.0, score))

    def should_auto_approve(self, score: ContentScore) -> bool:
        """자동 승인 여부"""
        return score.total >= self.thresholds.get("auto_approve", 0.85)

    def should_auto_reject(self, score: ContentScore) -> bool:
        """자동 거부 여부"""
        return score.total <= self.thresholds.get("auto_reject", 0.3)

    def should_display(self, score: ContentScore) -> bool:
        """Digest에 표시 여부"""
        return score.total >= self.thresholds.get("minimum_display", 0.4)


# 편의 함수
def score_content(content: dict, account_id: str = None, existing_embeddings: list[list[float]] = None) -> ContentScore:
    """
    콘텐츠 점수 계산 (편의 함수)

    Args:
        content: 콘텐츠 정보
        account_id: 계정 프로필 ID
        existing_embeddings: 기존 콘텐츠 임베딩들

    Returns:
        ContentScore
    """
    config = get_config()
    account_profile = config.get_account(account_id) if account_id else {}

    scorer = ContentScorer(account_profile=account_profile)
    return scorer.score(content, existing_embeddings)
