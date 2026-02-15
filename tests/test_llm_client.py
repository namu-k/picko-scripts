"""
Unit tests for picko.llm_client module - OpenRouter provider
"""

from unittest.mock import MagicMock, patch

import pytest

from picko.config import LLMConfig
from picko.llm_client import LLMClient, OpenRouterClient


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
