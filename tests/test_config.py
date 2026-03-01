"""
Unit tests for picko.config module
"""

import os
from pathlib import Path

import pytest

from picko.config import (
    DeduplicationConfig,
    EmbeddingConfig,
    GenerationConfig,
    LLMConfig,
    NotificationConfig,
    QualityConfig,
    ScoringConfig,
    SummaryLLMConfig,
    VaultConfig,
    WriterLLMConfig,
    get_config,
    load_config,
)


class TestVaultConfig:
    """VaultConfig tests"""

    def test_vault_config_creation(self):
        """VaultConfig dataclass 생성"""
        config = VaultConfig(root="C:/test/vault")
        assert config.root == "C:/test/vault"
        assert config.inbox == "Inbox/Inputs"
        assert config.digests == "Inbox/Inputs/_digests"

    def test_get_path(self):
        """get_path 메서드 테스트"""
        config = VaultConfig(root="C:/test/vault", inbox="Inbox")
        path = config.get_path("inbox")
        # Use os.path.normpath to handle Windows path separators
        assert os.path.normpath(str(path)) == os.path.normpath("C:/test/vault/Inbox")

    def test_get_path_invalid_key(self):
        """잘못된 key로 get_path 호출 시 예외"""
        config = VaultConfig(root="C:/test/vault")
        with pytest.raises(ValueError, match="Unknown vault path key"):
            config.get_path("invalid_key")


class TestLLMConfig:
    """LLMConfig tests"""

    def test_llm_config_defaults(self):
        """LLMConfig 기본값"""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7

    def test_api_key_property(self, monkeypatch):
        """API key 환경변수 로드"""
        config = LLMConfig(api_key_env="TEST_API_KEY")
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key-123")
        assert config.api_key == "sk-test-key-123"

    def test_api_key_missing(self, monkeypatch):
        """API key 없을 때 빈 문자열 반환"""
        config = LLMConfig(api_key_env="NONEXISTENT_KEY")
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        assert config.api_key == ""


class TestSummaryLLMConfig:
    """SummaryLLMConfig tests"""

    def test_summary_llm_config_defaults(self):
        """SummaryLLMConfig 기본값"""
        config = SummaryLLMConfig()
        assert config.provider == "ollama"
        assert config.model == "deepseek-r1:7b"
        assert config.fallback_provider == "openai"


class TestWriterLLMConfig:
    """WriterLLMConfig tests"""

    def test_writer_llm_config_defaults(self):
        """WriterLLMConfig 기본값"""
        config = WriterLLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"


class TestEmbeddingConfig:
    """EmbeddingConfig tests"""

    def test_embedding_config_defaults(self):
        """EmbeddingConfig 기본값"""
        config = EmbeddingConfig()
        assert config.provider == "local"
        assert config.model == "BAAI/bge-m3"
        assert config.dimensions == 1024
        assert config.cache_enabled is True


class TestScoringConfig:
    """ScoringConfig tests"""

    def test_scoring_config_defaults(self):
        """ScoringConfig 기본값"""
        config = ScoringConfig()
        assert config.weights["novelty"] == 0.3
        assert config.weights["relevance"] == 0.4
        assert config.weights["quality"] == 0.3
        assert config.thresholds["auto_approve"] == 0.85


class TestAgenticConfig:
    """Quality/Notification config tests"""

    def test_quality_config_defaults(self):
        config = QualityConfig()
        assert config.enabled is True
        assert config.primary_model == "gpt-4o-mini"
        assert config.cross_check_model == "claude-3.5-sonnet"
        assert config.auto_approve_threshold == 0.85
        assert config.feedback_enabled is True

    def test_notification_config_defaults(self):
        config = NotificationConfig()
        assert config.provider == "telegram"
        assert config.review_timeout_hours == 72

    def test_generation_config_defaults(self):
        config = GenerationConfig()
        assert config.auto_validate is True

    def test_deduplication_config_defaults(self):
        config = DeduplicationConfig()
        assert config.embedding_threshold == 0.92


class TestOpenRouterConfig:
    """OpenRouter config tests"""

    def test_llm_config_openrouter(self):
        """LLMConfig with openrouter provider"""
        config = LLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        assert config.provider == "openrouter"
        assert config.model == "openai/gpt-4o-mini"
        assert config.api_key_env == "OPENROUTER_API_KEY"

    def test_writer_llm_config_openrouter(self):
        """WriterLLMConfig with openrouter provider"""
        config = WriterLLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        assert config.provider == "openrouter"
        assert config.model == "openai/gpt-4o-mini"

    def test_summary_llm_config_api_key_env(self):
        """SummaryLLMConfig api_key_env 필드"""
        config = SummaryLLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        assert config.provider == "openrouter"
        assert config.api_key_env == "OPENROUTER_API_KEY"

    def test_summary_llm_config_api_key_env_default(self):
        """SummaryLLMConfig api_key_env 기본값 빈 문자열"""
        config = SummaryLLMConfig()
        assert config.api_key_env == ""


class TestLoadConfig:
    """load_config function tests"""

    @pytest.fixture
    def mock_config_file(self, tmp_path):
        """임시 config.yml 파일"""
        config_content = """
vault:
  root: "C:/test/vault"
  inbox: "Inbox/Inputs"

llm:
  provider: "openai"
  model: "gpt-4o-mini"
  temperature: 0.7
  api_key_env: "OPENAI_API_KEY"

summary_llm:
  provider: "ollama"
  model: "deepseek-r1:7b"

writer_llm:
  provider: "openai"
  model: "gpt-4o-mini"

embedding:
  provider: "local"
  model: "BAAI/bge-m3"
  dimensions: 1024

scoring:
  weights:
    novelty: 0.3
    relevance: 0.4
    quality: 0.3
  thresholds:
    auto_approve: 0.85

logging:
  level: "INFO"
  format: "{time} | {level} | {message}"
  dir: "logs"

processing:
  batch_size: 10
  max_retries: 3

quality:
  enabled: true
  primary:
    model: "gpt-4o-mini"
  cross_check:
    model: "claude-3-5-sonnet-20241022"
  final:
    auto_approve_threshold: 0.85
  feedback:
    enabled: true

notification:
  provider: "telegram"
  review_timeout_hours: 72

generation:
  auto_validate: true

deduplication:
  embedding_threshold: 0.92
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)
        return config_file

    def test_load_config_success(self, mock_config_file):
        """config.yml 로드 성공"""
        config = load_config(mock_config_file)
        assert config.vault.root == "C:/test/vault"
        assert config.llm.provider == "openai"
        assert config.scoring.weights["novelty"] == 0.3
        assert config.quality.enabled is True
        assert config.quality.primary_model == "gpt-4o-mini"
        assert config.quality.cross_check_model == "claude-3-5-sonnet-20241022"
        assert config.quality.auto_approve_threshold == 0.85
        assert config.quality.feedback_enabled is True
        assert config.notification.provider == "telegram"
        assert config.notification.review_timeout_hours == 72
        assert config.generation.auto_validate is True
        assert config.deduplication.embedding_threshold == 0.92

    def test_load_config_file_not_found(self):
        """존재하지 않는 config.yml"""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yml")

    def test_load_config_openrouter_writer(self, tmp_path):
        """OpenRouter writer_llm config 로드"""
        config_content = """
vault:
  root: "C:/test/vault"
llm:
  provider: "openai"
  model: "gpt-4o-mini"
summary_llm:
  provider: "openrouter"
  model: "openai/gpt-4o-mini"
  api_key_env: "OPENROUTER_API_KEY"
writer_llm:
  provider: "openrouter"
  model: "openai/gpt-4o-mini"
  api_key_env: "OPENROUTER_API_KEY"
embedding:
  provider: "local"
  model: "BAAI/bge-m3"
scoring:
  weights:
    novelty: 0.3
    relevance: 0.4
    quality: 0.3
logging:
  level: "INFO"
processing:
  batch_size: 10
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        config = load_config(config_file)
        assert config.writer_llm.provider == "openrouter"
        assert config.writer_llm.model == "openai/gpt-4o-mini"
        assert config.writer_llm.api_key_env == "OPENROUTER_API_KEY"
        assert config.summary_llm.provider == "openrouter"
        assert config.summary_llm.api_key_env == "OPENROUTER_API_KEY"


class TestGetConfig:
    """get_config function tests"""

    def test_get_config_singleton(self, monkeypatch):
        """get_config 싱글톤 패턴"""
        # 모듈의 _config를 None으로 리셋
        import picko.config

        original_config = picko.config._config
        picko.config._config = None

        try:
            # 테스트용 config 파일 경로 설정
            test_config_path = Path(__file__).parent.parent / "config" / "config.yml"

            if test_config_path.exists():
                config1 = get_config(test_config_path)
                config2 = get_config()
                assert config1 is config2
        finally:
            # 원래 상태 복원
            picko.config._config = original_config
