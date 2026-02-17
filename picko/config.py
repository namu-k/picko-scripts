"""
설정 로더 모듈
config.yml 및 계정 프로필 로드
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

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
    images_prompts: str = "Assets/Images/_prompts"
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

    weights: dict = field(default_factory=lambda: {"novelty": 0.3, "relevance": 0.4, "quality": 0.3})
    thresholds: dict = field(
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
    sources_file: str = "config/sources.yml"
    accounts_dir: str = "config/accounts"

    _sources: dict = field(default_factory=dict, repr=False)
    _accounts: dict = field(default_factory=dict, repr=False)

    @property
    def sources(self) -> dict:
        """소스 설정 로드 (lazy)"""
        if not self._sources:
            sources_path = Path(self.vault.root) / self.sources_file
            if sources_path.exists():
                with open(sources_path, "r", encoding="utf-8") as f:
                    self._sources = yaml.safe_load(f) or {}
                logger.debug(f"Loaded sources from {sources_path}")
        return self._sources

    def get_account(self, account_id: str) -> dict:
        """계정 프로필 로드"""
        if account_id not in self._accounts:
            # 1. vault 루트 기준 경로 시도
            account_path = Path(self.vault.root) / self.accounts_dir / f"{account_id}.yml"

            # 2. vault 경로에 없으면 프로젝트 루트 기준 경로 시도 (fallback)
            if not account_path.exists():
                account_path = PROJECT_ROOT / self.accounts_dir / f"{account_id}.yml"

            if account_path.exists():
                with open(account_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                # dict가 아닌 경우 빈 dict로 폴백
                if not isinstance(loaded, dict):
                    logger.warning(f"Account profile is not a dict: {account_id}, got {type(loaded)}")
                    loaded = {}
                self._accounts[account_id] = loaded
                logger.debug(f"Loaded account profile: {account_id} from {account_path}")
            else:
                logger.warning(f"Account profile not found: {account_id}")
                self._accounts[account_id] = {}
        return self._accounts[account_id]  # type: ignore[no-any-return]


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

    # 각 섹션별로 dataclass 생성
    return Config(
        vault=VaultConfig(**raw.get("vault", {})),
        llm=LLMConfig(**raw.get("llm", {})),
        summary_llm=SummaryLLMConfig(**raw.get("summary_llm", {})),
        writer_llm=WriterLLMConfig(**raw.get("writer_llm", {})),
        embedding=EmbeddingConfig(**raw.get("embedding", {})),
        scoring=ScoringConfig(**raw.get("scoring", {})),
        logging=LoggingConfig(**raw.get("logging", {})),
        processing=ProcessingConfig(**raw.get("processing", {})),
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
