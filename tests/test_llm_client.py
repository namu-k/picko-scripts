"""
Unit tests for picko.llm_client module - OpenRouter provider
"""

from unittest.mock import MagicMock, patch

import pytest

from picko.config import LLMConfig
from picko.llm_client import AnthropicClient, LLMClient, OllamaClient, OpenAIClient, OpenRouterClient, RelayClient


class TestOpenRouterClient:
    """OpenRouterClient tests"""

    @pytest.fixture
    def openrouter_config(self):
        """OpenRouter용 LLMConfig"""
        return LLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            temperature=0.7,
            max_tokens=4000,
            api_key_env="OPENROUTER_API_KEY",
        )

    def test_init(self, openrouter_config):
        """OpenRouterClient 초기화"""
        client = OpenRouterClient(openrouter_config)
        assert client.config == openrouter_config
        assert client._client is None

    def test_generate(self, openrouter_config):
        """OpenRouterClient.generate() 텍스트 생성"""
        client = OpenRouterClient(openrouter_config)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text from OpenRouter"
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.generate("Test prompt", system_prompt="System prompt")

        assert result == "Generated text from OpenRouter"
        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "openai/gpt-4o-mini"
        assert len(call_kwargs.kwargs["messages"]) == 2
        assert call_kwargs.kwargs["messages"][0]["role"] == "system"
        assert call_kwargs.kwargs["messages"][1]["role"] == "user"

    def test_generate_no_system_prompt(self, openrouter_config):
        """OpenRouterClient.generate() 시스템 프롬프트 없이"""
        client = OpenRouterClient(openrouter_config)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.generate("Test prompt")

        assert result == "Response"
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert len(call_kwargs.kwargs["messages"]) == 1
        assert call_kwargs.kwargs["messages"][0]["role"] == "user"

    def test_generate_stream(self, openrouter_config):
        """OpenRouterClient.generate_stream() 스트리밍 생성"""
        client = OpenRouterClient(openrouter_config)

        # 스트리밍 청크 모킹
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None  # 빈 청크

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])
        client._client = mock_openai

        result = list(client.generate_stream("Test prompt"))

        assert result == ["Hello", " World"]
        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs["stream"] is True

    def test_client_lazy_init(self, openrouter_config, monkeypatch):
        """OpenRouterClient의 OpenAI 클라이언트 lazy 초기화"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        client = OpenRouterClient(openrouter_config)

        with patch("openai.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance

            result = client.client

            mock_openai_class.assert_called_once_with(
                api_key="test-key",
                base_url="https://openrouter.ai/api/v1",
            )
            assert result == mock_instance

            # 두 번째 호출 시 같은 인스턴스 반환
            result2 = client.client
            assert result2 == mock_instance
            assert mock_openai_class.call_count == 1


class TestRelayClient:
    """RelayClient tests"""

    @pytest.fixture
    def relay_config(self):
        """Relay용 LLMConfig"""
        return LLMConfig(
            provider="relay",
            model="openai/gpt-4o-mini",
            temperature=0.7,
            max_tokens=4000,
            api_key_env="RELAY_API_KEY",
        )

    def test_init(self, relay_config):
        """RelayClient 초기화"""
        client = RelayClient(relay_config)
        assert client.config == relay_config
        assert client._client is None

    def test_generate(self, relay_config):
        """RelayClient.generate() 텍스트 생성"""
        client = RelayClient(relay_config)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text from Relay"
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.generate("Test prompt", system_prompt="System prompt")

        assert result == "Generated text from Relay"
        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "openai/gpt-4o-mini"
        assert len(call_kwargs.kwargs["messages"]) == 2
        assert call_kwargs.kwargs["messages"][0]["role"] == "system"
        assert call_kwargs.kwargs["messages"][1]["role"] == "user"

    def test_generate_no_system_prompt(self, relay_config):
        """RelayClient.generate() 시스템 프롬프트 없이"""
        client = RelayClient(relay_config)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.generate("Test prompt")

        assert result == "Response"
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert len(call_kwargs.kwargs["messages"]) == 1
        assert call_kwargs.kwargs["messages"][0]["role"] == "user"

    def test_generate_stream(self, relay_config):
        """RelayClient.generate_stream() 스트리밍 생성"""
        client = RelayClient(relay_config)

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None  # 빈 청크

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])
        client._client = mock_openai

        result = list(client.generate_stream("Test prompt"))

        assert result == ["Hello", " World"]
        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs["stream"] is True

    def test_client_lazy_init(self, relay_config, monkeypatch):
        """RelayClient의 OpenAI 클라이언트 lazy 초기화 및 base_url 검증"""
        monkeypatch.setenv("RELAY_API_KEY", "test-key")
        client = RelayClient(relay_config)

        with patch("openai.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance

            result = client.client

            mock_openai_class.assert_called_once_with(
                api_key="test-key",
                base_url="https://www.relayservice.im/api/v1",
            )
            assert result == mock_instance

            # 두 번째 호출 시 같은 인스턴스 반환
            result2 = client.client
            assert result2 == mock_instance
            assert mock_openai_class.call_count == 1


class TestLLMClientOpenRouter:
    """LLMClient with OpenRouter provider tests"""

    def test_llm_client_init_openrouter(self, monkeypatch):
        """LLMClient provider=openrouter 초기화"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        config = LLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, OpenRouterClient)

    def test_llm_client_generate_openrouter(self, monkeypatch):
        """LLMClient.generate() OpenRouter 프로바이더 사용"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "dummy_key")
        config = LLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)

        # dummy_key이면 dummy response 반환
        result = client.generate("Test prompt")
        assert "DUMMY RESPONSE" in result


class TestGetSummaryClientOpenRouter:
    """get_summary_client() with OpenRouter provider tests"""

    def test_get_summary_client_openrouter(self, monkeypatch):
        """get_summary_client() OpenRouter 프로바이더"""
        import picko.llm_client

        # 싱글톤 리셋
        original = picko.llm_client._summary_client
        picko.llm_client._summary_client = None

        try:
            monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

            # mock config
            mock_summary_config = MagicMock()
            mock_summary_config.provider = "openrouter"
            mock_summary_config.model = "openai/gpt-4o-mini"
            mock_summary_config.temperature = 0.3
            mock_summary_config.max_tokens = 1000
            mock_summary_config.api_key_env = "OPENROUTER_API_KEY"
            mock_summary_config.base_url = ""
            mock_summary_config.fallback_provider = ""
            mock_summary_config.fallback_model = ""
            mock_summary_config.fallback_api_key_env = ""

            mock_config = MagicMock()
            mock_config.summary_llm = mock_summary_config

            # get_summary_client 내부에서 from .config import get_config를 호출하므로
            # picko.config.get_config도 패치해야 함
            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_summary_client()
                assert isinstance(client._client, OpenRouterClient)
                assert client.config.provider == "openrouter"
                assert client.config.api_key_env == "OPENROUTER_API_KEY"
        finally:
            picko.llm_client._summary_client = original

    def test_get_summary_client_openrouter_default_api_key_env(self, monkeypatch):
        """FR-003: provider=openrouter + api_key_env 미지정 시 기본값 OPENROUTER_API_KEY"""
        import picko.llm_client

        original = picko.llm_client._summary_client
        picko.llm_client._summary_client = None

        try:
            monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

            mock_summary_config = MagicMock()
            mock_summary_config.provider = "openrouter"
            mock_summary_config.model = "openai/gpt-4o-mini"
            mock_summary_config.temperature = 0.3
            mock_summary_config.max_tokens = 1000
            mock_summary_config.api_key_env = ""  # 미지정
            mock_summary_config.base_url = ""
            mock_summary_config.fallback_provider = ""
            mock_summary_config.fallback_model = ""
            mock_summary_config.fallback_api_key_env = ""

            mock_config = MagicMock()
            mock_config.summary_llm = mock_summary_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_summary_client()
                assert client.config.api_key_env == "OPENROUTER_API_KEY"
        finally:
            picko.llm_client._summary_client = original


class TestLLMClientRelay:
    """LLMClient with Relay provider tests"""

    def test_llm_client_init_relay(self, monkeypatch):
        """LLMClient provider=relay 초기화"""
        monkeypatch.setenv("RELAY_API_KEY", "test-key")
        config = LLMConfig(
            provider="relay",
            model="openai/gpt-4o-mini",
            api_key_env="RELAY_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, RelayClient)

    def test_llm_client_generate_relay(self, monkeypatch):
        """LLMClient.generate() Relay 프로바이더 사용"""
        monkeypatch.setenv("RELAY_API_KEY", "dummy_key")
        config = LLMConfig(
            provider="relay",
            model="openai/gpt-4o-mini",
            api_key_env="RELAY_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)

        # dummy_key이면 dummy response 반환
        result = client.generate("Test prompt")
        assert "DUMMY RESPONSE" in result


class TestGetSummaryClientRelay:
    """get_summary_client() with Relay provider tests"""

    def test_get_summary_client_relay(self, monkeypatch):
        """get_summary_client() Relay 프로바이더"""
        import picko.llm_client

        original = picko.llm_client._summary_client
        picko.llm_client._summary_client = None

        try:
            monkeypatch.setenv("RELAY_API_KEY", "test-key")

            mock_summary_config = MagicMock()
            mock_summary_config.provider = "relay"
            mock_summary_config.model = "openai/gpt-4o-mini"
            mock_summary_config.temperature = 0.3
            mock_summary_config.max_tokens = 1000
            mock_summary_config.api_key_env = "RELAY_API_KEY"
            mock_summary_config.base_url = ""
            mock_summary_config.fallback_provider = ""
            mock_summary_config.fallback_model = ""
            mock_summary_config.fallback_api_key_env = ""

            mock_config = MagicMock()
            mock_config.summary_llm = mock_summary_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_summary_client()
                assert isinstance(client._client, RelayClient)
                assert client.config.provider == "relay"
                assert client.config.api_key_env == "RELAY_API_KEY"
        finally:
            picko.llm_client._summary_client = original

    def test_get_summary_client_relay_default_api_key_env(self, monkeypatch):
        """provider=relay + api_key_env 미지정 시 기본값 RELAY_API_KEY"""
        import picko.llm_client

        original = picko.llm_client._summary_client
        picko.llm_client._summary_client = None

        try:
            monkeypatch.setenv("RELAY_API_KEY", "test-key")

            mock_summary_config = MagicMock()
            mock_summary_config.provider = "relay"
            mock_summary_config.model = "openai/gpt-4o-mini"
            mock_summary_config.temperature = 0.3
            mock_summary_config.max_tokens = 1000
            mock_summary_config.api_key_env = ""  # 미지정
            mock_summary_config.base_url = ""
            mock_summary_config.fallback_provider = ""
            mock_summary_config.fallback_model = ""
            mock_summary_config.fallback_api_key_env = ""

            mock_config = MagicMock()
            mock_config.summary_llm = mock_summary_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_summary_client()
                assert client.config.api_key_env == "RELAY_API_KEY"
        finally:
            picko.llm_client._summary_client = original


class TestGetSummaryClientNonOpenRouterFallback:
    """get_summary_client() non-OpenRouter provider api_key_env fallback tests"""

    def test_non_openrouter_empty_api_key_env_defaults_to_openai(self, monkeypatch):
        """provider != openrouter + api_key_env="" 시 기본값 OPENAI_API_KEY (FR-003 역방향 검증)"""
        import picko.llm_client

        original = picko.llm_client._summary_client
        picko.llm_client._summary_client = None

        try:
            monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

            mock_summary_config = MagicMock()
            mock_summary_config.provider = "openai"
            mock_summary_config.model = "gpt-4o-mini"
            mock_summary_config.temperature = 0.3
            mock_summary_config.max_tokens = 1000
            mock_summary_config.api_key_env = ""  # 미지정
            mock_summary_config.base_url = ""
            mock_summary_config.fallback_provider = ""
            mock_summary_config.fallback_model = ""
            mock_summary_config.fallback_api_key_env = ""

            mock_config = MagicMock()
            mock_config.summary_llm = mock_summary_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_summary_client()
                assert client.config.api_key_env == "OPENAI_API_KEY"
        finally:
            picko.llm_client._summary_client = original


class TestLLMClientProviderRouting:
    """LLMClient constructor routes to correct client class per provider"""

    def test_openai_provider_routes_to_openai_client(self, monkeypatch):
        """provider=openai → OpenAIClient"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        config = LLMConfig(provider="openai", model="gpt-4o-mini", api_key_env="OPENAI_API_KEY")
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, OpenAIClient)

    def test_anthropic_provider_routes_to_anthropic_client(self, monkeypatch):
        """provider=anthropic → AnthropicClient"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key_env="ANTHROPIC_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, AnthropicClient)

    def test_ollama_provider_routes_to_ollama_client(self):
        """provider=ollama → OllamaClient"""
        config = LLMConfig(provider="ollama", model="deepseek-r1:7b", api_key_env="")
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, OllamaClient)

    def test_openrouter_provider_routes_to_openrouter_client(self, monkeypatch):
        """provider=openrouter → OpenRouterClient (회귀 검증)"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        config = LLMConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key_env="OPENROUTER_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, OpenRouterClient)

    def test_relay_provider_routes_to_relay_client(self, monkeypatch):
        """provider=relay → RelayClient"""
        monkeypatch.setenv("RELAY_API_KEY", "test-key")
        config = LLMConfig(
            provider="relay",
            model="openai/gpt-4o-mini",
            api_key_env="RELAY_API_KEY",
        )
        client = LLMClient(config=config, cache_enabled=False)
        assert isinstance(client._client, RelayClient)

    def test_unknown_provider_raises(self):
        """알 수 없는 provider → ValueError"""
        config = LLMConfig(provider="unknown_llm", model="some-model")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMClient(config=config, cache_enabled=False)


class TestGetWriterClient:
    """get_writer_client() 함수 테스트 (FR-003)"""

    def test_get_writer_client_openrouter_default_api_key_env(self, monkeypatch):
        """FR-003: writer_llm provider=openrouter + api_key_env 미지정 시 기본값 OPENROUTER_API_KEY"""
        import picko.llm_client

        original = picko.llm_client._writer_client
        picko.llm_client._writer_client = None

        try:
            monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

            mock_writer_config = MagicMock()
            mock_writer_config.provider = "openrouter"
            mock_writer_config.model = "openai/gpt-4o-mini"
            mock_writer_config.temperature = 0.8
            mock_writer_config.max_tokens = 2000
            mock_writer_config.api_key_env = ""  # 미지정

            mock_config = MagicMock()
            mock_config.writer_llm = mock_writer_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_writer_client()
                assert client.config.api_key_env == "OPENROUTER_API_KEY"
        finally:
            picko.llm_client._writer_client = original

    def test_get_writer_client_relay_default_api_key_env(self, monkeypatch):
        """FR-003: writer_llm provider=relay + api_key_env 미지정 시 기본값 RELAY_API_KEY"""
        import picko.llm_client

        original = picko.llm_client._writer_client
        picko.llm_client._writer_client = None

        try:
            monkeypatch.setenv("RELAY_API_KEY", "test-key")

            mock_writer_config = MagicMock()
            mock_writer_config.provider = "relay"
            mock_writer_config.model = "openai/gpt-4o-mini"
            mock_writer_config.temperature = 0.8
            mock_writer_config.max_tokens = 2000
            mock_writer_config.api_key_env = ""  # 미지정

            mock_config = MagicMock()
            mock_config.writer_llm = mock_writer_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_writer_client()
                assert client.config.api_key_env == "RELAY_API_KEY"
        finally:
            picko.llm_client._writer_client = original

    def test_get_writer_client_openai_default_api_key_env(self, monkeypatch):
        """FR-003: writer_llm provider=openai + api_key_env 미지정 시 기본값 OPENAI_API_KEY"""
        import picko.llm_client

        original = picko.llm_client._writer_client
        picko.llm_client._writer_client = None

        try:
            monkeypatch.setenv("OPENAI_API_KEY", "test-key")

            mock_writer_config = MagicMock()
            mock_writer_config.provider = "openai"
            mock_writer_config.model = "gpt-4o-mini"
            mock_writer_config.temperature = 0.8
            mock_writer_config.max_tokens = 2000
            mock_writer_config.api_key_env = ""  # 미지정

            mock_config = MagicMock()
            mock_config.writer_llm = mock_writer_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_writer_client()
                assert client.config.api_key_env == "OPENAI_API_KEY"
        finally:
            picko.llm_client._writer_client = original

    def test_get_writer_client_explicit_api_key_env(self, monkeypatch):
        """FR-003: writer_llm api_key_env 명시 시 명시된 값 사용"""
        import picko.llm_client

        original = picko.llm_client._writer_client
        picko.llm_client._writer_client = None

        try:
            monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

            mock_writer_config = MagicMock()
            mock_writer_config.provider = "openrouter"
            mock_writer_config.model = "openai/gpt-4o-mini"
            mock_writer_config.temperature = 0.8
            mock_writer_config.max_tokens = 2000
            mock_writer_config.api_key_env = "CUSTOM_API_KEY"  # 명시적 지정

            mock_config = MagicMock()
            mock_config.writer_llm = mock_writer_config

            with (
                patch("picko.config.get_config", return_value=mock_config),
                patch("picko.llm_client.get_config", return_value=mock_config),
            ):
                client = picko.llm_client.get_writer_client()
                assert client.config.api_key_env == "CUSTOM_API_KEY"
        finally:
            picko.llm_client._writer_client = original
