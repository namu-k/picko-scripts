"""
설정 로더 모듈
config.yml 및 계정 프로필 로드
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .logger import get_logger

logger = get_logger("config")

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yml"

# .env 파일 로드 (프로젝트 루트의 .env)
# 로드된 환경변수는 LLMConfig/WriterLLMConfig/SummaryLLMConfig의 api_key_env
# (OPENAI_API_KEY, OPENROUTER_API_KEY 등)에서 API 키로 사용됩니다.
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class VaultConfig:
    """Vault 경로 설정"""

    root: str
    inbox: str = "Inbox/Inputs"
    digests: str = "Inbox/Inputs/_digests"
    explorations: str = "Inbox/Explorations"
    content: str = "Content"
    longform: str = "Content/Longform"
    packs: str = "Content/Packs"
    assets: str = "Assets"
    # 멀티미디어 프롬프트 및 결과물
    images_prompts: str = "Assets/Images/_prompts"
    images_output: str = "Assets/Images/_output"
    videos_prompts: str = "Assets/Videos/_prompts"
    videos_output: str = "Assets/Videos/_output"
    # 참고 자료
    references: str = "Assets/References"
    archive: str = "Archive"
    logs_publish: str = "Logs/Publish"

    def get_path(self, key: str) -> Path:
        """경로 키로 전체 경로 반환"""
        relative = getattr(self, key, None)
        if relative is None:
            raise ValueError(f"Unknown vault path key: {key}")
        return Path(self.root) / relative  # type: ignore[no-any-return]


@dataclass
class LLMConfig:
    """LLM 설정"""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4000
    api_key_env: str = "OPENAI_API_KEY"
    # Optional fallback attributes (for ollama/local LLMs)
    base_url: str = ""
    fallback_provider: str = ""
    fallback_model: str = ""
    fallback_api_key_env: str = ""

    @property
    def api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        key = os.environ.get(self.api_key_env)
        if not key:
            logger.warning(f"API key not found in environment: {self.api_key_env}")
        return key or ""


@dataclass
class SummaryLLMConfig:
    """요약/태깅용 LLM 설정 (로컬 우선)"""

    provider: str = "ollama"
    model: str = "deepseek-r1:7b"
    temperature: float = 0.3
    max_tokens: int = 1000
    base_url: str = "http://localhost:11434"
    api_key_env: str = ""

    # 폴백옵션 (로컬 실패 시 클라우드 사용)
    fallback_provider: str = "openai"
    fallback_model: str = "gpt-4o-mini"
    fallback_api_key_env: str = "OPENAI_API_KEY"


@dataclass
class WriterLLMConfig:
    """글쓰기용 LLM 설정 (클라우드)"""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.8
    max_tokens: int = 2000
    api_key_env: str = "OPENAI_API_KEY"

    @property
    def api_key(self) -> str:
        """환경변수에서 API 키 로드"""
        key = os.environ.get(self.api_key_env)
        if not key:
            logger.warning(f"API key not found in environment: {self.api_key_env}")
        return key or ""


@dataclass
class EmbeddingConfig:
    """임베딩 설정"""

    provider: str = "local"  # local | openai | ollama
    model: str = "BAAI/bge-m3"  # sentence-transformers 모델
    dimensions: int = 1024  # bge-m3: 1024, all-MiniLM-L6-v2: 384
    device: str = "cpu"  # cpu | cuda
    cache_enabled: bool = True
    cache_dir: str = "cache/embeddings"
    base_url: str = "http://localhost:11434"  # Ollama base URL

    # OpenAI 폴백 (로컬 실패 시)
    fallback_provider: str = "openai"
    fallback_model: str = "text-embedding-3-small"
    fallback_api_key_env: str = "OPENAI_API_KEY"
    fallback_device: str = "cpu"  # Fallback device for local processing


@dataclass
class ScoringConfig:
    """점수 계산 설정"""

    weights: dict[str, float] = field(default_factory=lambda: {"novelty": 0.3, "relevance": 0.4, "quality": 0.3})
    freshness_half_life_days: float = 7.0
    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "auto_approve": 0.85,
            "auto_reject": 0.3,
            "minimum_display": 0.4,
        }
    )


@dataclass
class LoggingConfig:
    """로깅 설정"""

    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
    dir: str = "logs"
    retention_days: int = 30


@dataclass
class ProcessingConfig:
    """처리 설정"""

    batch_size: int = 10
    max_retries: int = 3
    retry_delay_seconds: int = 5
    request_timeout_seconds: int = 30


@dataclass
class QualityConfig:
    """품질 검증 설정 (007-agentic)"""

    enabled: bool = True
    primary_model: str = "gpt-4o-mini"
    cross_check_model: str = "claude-3.5-sonnet"
    auto_approve_threshold: float = 0.85
    feedback_enabled: bool = True


@dataclass
class NotificationConfig:
    """알림 설정 (007-agentic)"""

    provider: str = "telegram"  # telegram | slack
    review_timeout_hours: int = 72


@dataclass
class GenerationConfig:
    """콘텐츠 생성 설정"""

    auto_validate: bool = True


@dataclass
class DeduplicationConfig:
    """중복 탐지 설정"""

    embedding_threshold: float = 0.92


@dataclass
class Config:
    """전체 설정"""

    vault: VaultConfig
    llm: LLMConfig
    summary_llm: SummaryLLMConfig
    writer_llm: WriterLLMConfig
    embedding: EmbeddingConfig
    scoring: ScoringConfig
    logging: LoggingConfig
    processing: ProcessingConfig
    quality: QualityConfig = field(default_factory=QualityConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    deduplication: DeduplicationConfig = field(default_factory=DeduplicationConfig)
    sources_file: str = "config/sources.yml"
    accounts_dir: str = "config/accounts"

    _sources: dict[str, Any] = field(default_factory=dict, repr=False)
    _accounts: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    @property
    def sources(self) -> dict[str, Any]:
        """소스 설정 로드 (lazy)"""
        if not self._sources:
            sources_path = Path(self.vault.root) / self.sources_file
            if sources_path.exists():
                with open(sources_path, "r", encoding="utf-8") as f:
                    self._sources = yaml.safe_load(f) or {}
                logger.debug(f"Loaded sources from {sources_path}")
        return self._sources

    def _load_account_dir(self, dir_path: Path) -> dict[str, Any]:
        """Load account profile from directory structure.

        Expected files:
        - account.yml (required)
        - scoring.yml (optional)
        - style.yml (optional)
        """
        account_path = dir_path / "account.yml"
        if not account_path.exists():
            logger.warning(f"account.yml not found in: {dir_path}")
            return {}

        with open(account_path, "r", encoding="utf-8") as f:
            loaded_account = yaml.safe_load(f) or {}
        if not isinstance(loaded_account, dict):
            logger.warning(f"account.yml is not a dict: {account_path}")
            return {}

        account: dict[str, Any] = dict(loaded_account)

        scoring_path = dir_path / "scoring.yml"
        if scoring_path.exists():
            with open(scoring_path, "r", encoding="utf-8") as f:
                loaded_scoring = yaml.safe_load(f) or {}
            if isinstance(loaded_scoring, dict):
                account["interests"] = loaded_scoring.get("interests", {})
                account["keywords"] = loaded_scoring.get("keywords", {})
                account["trusted_sources"] = loaded_scoring.get("trusted_sources", [])

        style_path = dir_path / "style.yml"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                loaded_style = yaml.safe_load(f) or {}
            if isinstance(loaded_style, dict):
                account["visual_settings"] = loaded_style.get("visual_settings", {})

        return account

    def get_account(self, account_id: str) -> dict[str, Any]:
        """계정 프로필 로드"""
        if account_id not in self._accounts:

            def _try_load(base: Path) -> dict[str, Any] | None:
                dir_path = base / self.accounts_dir / account_id
                if dir_path.is_dir():
                    loaded_dir = self._load_account_dir(dir_path)
                    if loaded_dir:
                        logger.debug(f"Loaded account directory: {account_id} from {dir_path}")
                        return loaded_dir

                account_path = base / self.accounts_dir / f"{account_id}.yml"
                if account_path.exists():
                    with open(account_path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f) or {}
                    if not isinstance(loaded, dict):
                        logger.warning(f"Account profile is not a dict: {account_id}, got {type(loaded)}")
                        return {}
                    logger.debug(f"Loaded account profile: {account_id} from {account_path}")
                    return loaded
                return None

            loaded_profile = _try_load(Path(self.vault.root))
            if loaded_profile is None:
                loaded_profile = _try_load(PROJECT_ROOT)

            if loaded_profile is None:
                logger.warning(f"Account profile not found: {account_id}")
                loaded_profile = {}

            self._accounts[account_id] = loaded_profile
        return self._accounts[account_id]


def load_config(config_path: str | Path | None = None) -> Config:
    """
    설정 파일 로드

    Args:
        config_path: 설정 파일 경로 (기본: config/config.yml)

    Returns:
        Config 인스턴스
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    logger.info(f"Loaded config from {config_path}")

    # vault root: 상대 경로면 프로젝트 루트 기준으로 해석 (CI/다중 환경 대응)
    vault_raw = dict(raw.get("vault", {}))
    root = vault_raw.get("root", "mock_vault")
    if not Path(root).is_absolute():
        vault_raw["root"] = str(PROJECT_ROOT / root)

    # 각 섹션별로 dataclass 생성
    return Config(
        vault=VaultConfig(**vault_raw),
        llm=LLMConfig(**raw.get("llm", {})),
        summary_llm=SummaryLLMConfig(**raw.get("summary_llm", {})),
        writer_llm=WriterLLMConfig(**raw.get("writer_llm", {})),
        embedding=EmbeddingConfig(**raw.get("embedding", {})),
        scoring=ScoringConfig(**raw.get("scoring", {})),
        logging=LoggingConfig(**raw.get("logging", {})),
        processing=ProcessingConfig(**raw.get("processing", {})),
        quality=QualityConfig(
            enabled=raw.get("quality", {}).get("enabled", True),
            primary_model=raw.get("quality", {}).get("primary", {}).get("model", "gpt-4o-mini"),
            cross_check_model=raw.get("quality", {}).get("cross_check", {}).get("model", "claude-3.5-sonnet"),
            auto_approve_threshold=raw.get("quality", {}).get("final", {}).get("auto_approve_threshold", 0.85),
            feedback_enabled=raw.get("quality", {}).get("feedback", {}).get("enabled", True),
        ),
        notification=NotificationConfig(
            provider=raw.get("notification", {}).get("provider", "telegram"),
            review_timeout_hours=raw.get("notification", {}).get("review_timeout_hours", 72),
        ),
        generation=GenerationConfig(
            auto_validate=raw.get("generation", {}).get("auto_validate", True),
        ),
        deduplication=DeduplicationConfig(
            embedding_threshold=raw.get("deduplication", {}).get("embedding_threshold", 0.92),
        ),
        sources_file=raw.get("sources_file", "config/sources.yml"),
        accounts_dir=raw.get("accounts_dir", "config/accounts"),
    )


# 싱글톤 설정 인스턴스
_config: Config | None = None


def get_config(config_path: str | Path | None = None) -> Config:
    """
    싱글톤 설정 인스턴스 반환

    Args:
        config_path: 설정 파일 경로 (최초 호출 시에만 사용)

    Returns:
        Config 인스턴스
    """
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reload_config(config_path: str | Path | None = None) -> Config:
    """
    설정 다시 로드

    Args:
        config_path: 설정 파일 경로

    Returns:
        새로 로드된 Config 인스턴스
    """
    global _config
    _config = load_config(config_path)
    return _config
