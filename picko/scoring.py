"""
점수 계산 모듈
novelty, relevance, quality, total 점수 계산
"""

from dataclasses import dataclass

from .account_context import AccountIdentity, get_identity
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

    def __init__(
        self,
        config: ScoringConfig | None = None,
        account_profile: dict | None = None,
        account_identity: AccountIdentity | None = None,
    ):
        if config is None:
            config = get_config().scoring

        self.config = config
        self.weights = config.weights
        self.thresholds = config.thresholds
        self.account_profile = account_profile or {}
        self.account_identity = account_identity
        self.embedding_manager = get_embedding_manager()

        logger.debug(f"ContentScorer initialized with weights: {self.weights}")

    def score(self, content: dict, existing_embeddings: list[list[float]] | None = None) -> ContentScore:
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

    def _calculate_novelty(self, content: dict, existing_embeddings: list[list[float]] | None = None) -> float:
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
        관련도 계산 (계정 프로필 및 AccountIdentity 기반)

        Args:
            content: 콘텐츠 (title, text, keywords 등)

        Returns:
            관련도 점수 (0~1)
        """
        # 텍스트 결합
        text = (
            content.get("title", "") + " " + content.get("text", "") + " " + " ".join(content.get("keywords", []))
        ).lower()

        score = 0.0
        matches = 0

        # 1) AccountIdentity의 타겟 오디언스 매칭 (우선순위 높음)
        if self.account_identity:
            # 타겟 오디언스와 관련된 키워드 추출
            target_score = self._match_target_audience(text, self.account_identity)
            if target_score > 0:
                score += target_score
                matches += 1
                logger.debug(f"Target audience match: {target_score:.2f}")

        # 2) 기존 account_profile 기반 매칭 (호환성 유지)
        if self.account_profile:
            score += self._match_account_profile(text, self.account_profile)
            matches += 1  # 프로필 매칭 시도 횟수 증가

        # 3) 필러(Pillar) 기반 매칭 (AccountIdentity에서)
        if self.account_identity and self.account_identity.pillars:
            pillar_score = self._match_pillars(text, self.account_identity.pillars)
            if pillar_score > 0:
                score += pillar_score * 0.5  # 필러는 가중치 낮게
                matches += 1

        # 정규화 (최대 5개 매칭 기준)
        if matches == 0:
            return 0.5  # 매칭 없으면 중립 점수

        normalized = min(score / 5.0, 1.0)
        return max(0.0, min(1.0, normalized))

    def _match_target_audience(self, text: str, identity: AccountIdentity) -> float:
        """
        타겟 오디언스와 콘텐츠 텍스트 매칭

        Args:
            text: 콘텐츠 텍스트 (소문자)
            identity: AccountIdentity 인스턴스

        Returns:
            매칭 점수 (0~2)
        """
        score = 0.0

        # 타겟 오디언스 목록에서 키워드 추출하여 매칭
        for target in identity.target_audience:
            target_lower = target.lower()
            # 정확히 일치하면 높은 가중치
            if target_lower in text:
                score += 1.0

        # one_liner에서 키워드 추출 (간단 분할)
        one_liner_words = identity.one_liner.lower().split()
        for word in one_liner_words:
            if len(word) > 3 and word in text:  # 3글자 이상 단어만
                score += 0.3

        return min(score, 2.0)  # 최대 2점

    def _match_pillars(self, text: str, pillars: list[str]) -> float:
        """
        필러와 콘텐츠 텍스트 매칭

        Args:
            text: 콘텐츠 텍스트 (소문자)
            pillars: 필러 목록 (예: ["P1: 리더십", "P2: 마케팅"])

        Returns:
            매칭 점수 (0~1)
        """
        score = 0.0
        for pillar in pillars:
            # P1, P2 등 접두사 제거 후 설명 부분 추출
            pillar_desc = pillar.split(":", 1)[1].strip() if ":" in pillar else pillar
            pillar_lower = pillar_desc.lower()
            # 키워드 단위로 분해
            pillar_words = pillar_lower.split()
            for word in pillar_words:
                if len(word) > 2 and word in text:
                    score += 0.2

        return min(score, 1.0)

    def _match_account_profile(self, text: str, profile: dict) -> float:
        """
        기존 account_profile 기반 매칭 (호환성 유지)

        Args:
            text: 콘텐츠 텍스트
            profile: 계정 프로필 딕셔너리

        Returns:
            매칭 점수
        """
        score = 0.0

        # 관심 주제 매칭
        interests = profile.get("interests", {})
        for interest in interests.get("primary", []):
            if interest.lower() in text:
                score += 1.0

        for interest in interests.get("secondary", []):
            if interest.lower() in text:
                score += 0.5

        # 키워드 매칭
        keywords = profile.get("keywords", {})
        for kw in keywords.get("high_relevance", []):
            if kw.lower() in text:
                score += 1.0

        for kw in keywords.get("medium_relevance", []):
            if kw.lower() in text:
                score += 0.5

        for kw in keywords.get("low_relevance", []):
            if kw.lower() in text:
                score += 0.2

        return score

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
        return score.total >= self.thresholds.get("auto_approve", 0.85)  # type: ignore[no-any-return]

    def should_auto_reject(self, score: ContentScore) -> bool:
        """자동 거부 여부"""
        return score.total <= self.thresholds.get("auto_reject", 0.3)  # type: ignore[no-any-return]

    def should_display(self, score: ContentScore) -> bool:
        """Digest에 표시 여부"""
        return score.total >= self.thresholds.get("minimum_display", 0.4)  # type: ignore[no-any-return]


# 편의 함수
def score_content(
    content: dict,
    account_id: str | None = None,
    existing_embeddings: list[list[float]] | None = None,
    account_identity: AccountIdentity | None = None,
) -> ContentScore:
    """
    콘텐츠 점수 계산 (편의 함수)

    Args:
        content: 콘텐츠 정보
        account_id: 계정 프로필 ID
        existing_embeddings: 기존 콘텐츠 임베딩들
        account_identity: AccountIdentity 인스턴스 (선택)

    Returns:
        ContentScore
    """
    config = get_config()
    account_profile = config.get_account(account_id) if account_id else {}

    # account_identity가 없으면 account_id로부터 로드 시도
    if account_identity is None and account_id:
        try:
            account_identity = get_identity(account_id)
            if account_identity:
                logger.debug(f"Loaded AccountIdentity for {account_id}")
        except Exception as e:
            logger.debug(f"Could not load AccountIdentity for {account_id}: {e}")

    scorer = ContentScorer(account_profile=account_profile, account_identity=account_identity)
    return scorer.score(content, existing_embeddings)
