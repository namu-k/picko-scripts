"""
LLM API 클라이언트 모듈
OpenAI/Anthropic API 추상화 및 재시도 로직
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator

from .config import LLMConfig, get_config
from .logger import get_logger

logger = get_logger("llm_client")


class BaseLLMClient(ABC):
    """LLM 클라이언트 기본 클래스"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.config.api_key)
        return self._client

    def generate(
        self, prompt: str, system_prompt: str = None, temperature: float = None, max_tokens: int = None, **kwargs
    ) -> str:
        """
        텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수

        Returns:
            생성된 텍스트
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            **kwargs,
        )

        return response.choices[0].message.content

    def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.config.model, messages=messages, temperature=self.config.temperature, stream=True, **kwargs
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API 클라이언트"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.config.api_key)
        return self._client

    def generate(
        self, prompt: str, system_prompt: str = None, temperature: float = None, max_tokens: int = None, **kwargs
    ) -> str:
        """텍스트 생성"""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens or self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature or self.config.temperature,
            **kwargs,
        )

        return response.content[0].text

    def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성"""
        with self.client.messages.stream(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            for text in stream.text_stream:
                yield text


class OllamaClient(BaseLLMClient):
    """Ollama 로컬 LLM 클라이언트"""

    def __init__(self, config):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=getattr(self.config, "base_url", "http://localhost:11434"))
        return self._client

    def generate(
        self, prompt: str, system_prompt: str = None, temperature: float = None, max_tokens: int = None, **kwargs
    ) -> str:
        """텍스트 생성"""
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        response = self.client.generate(
            model=self.config.model,
            prompt=prompt,
            system=system_prompt or "",
            options=options if options else None,
            **kwargs,
        )

        return response.get("response", "")

    def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성"""
        for chunk in self.client.generate(
            model=self.config.model, prompt=prompt, system=system_prompt or "", stream=True, **kwargs
        ):
            if "response" in chunk:
                yield chunk["response"]


class LLMClient:
    """
    LLM 클라이언트 래퍼
    - 자동 재시도
    - 응답 캐싱
    - 프로바이더 추상화
    """

    def __init__(self, config: LLMConfig = None, cache_enabled: bool = True, cache_dir: str | Path = None):
        if config is None:
            config = get_config().llm

        self.config = config
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(cache_dir or "cache/responses")

        # 프로바이더별 클라이언트 초기화
        if config.provider == "openai":
            self._client = OpenAIClient(config)
        elif config.provider == "anthropic":
            self._client = AnthropicClient(config)
        elif config.provider == "ollama":
            self._client = OllamaClient(config)
        else:
            raise ValueError(f"Unknown LLM provider: {config.provider}")

        logger.debug(f"LLMClient initialized: {config.provider}/{config.model}")

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        use_cache: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ) -> str:
        """
        텍스트 생성 (캐싱 + 재시도)

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            use_cache: 캐시 사용 여부
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)

        Returns:
            생성된 텍스트
        """
        # 캐시 확인
        if self.cache_enabled and use_cache:
            cache_key = self._get_cache_key(prompt, system_prompt)
            cached = self._get_cached(cache_key)
            if cached:
                logger.debug("Using cached response")
                return cached

        # 재시도 로직
        last_error = None
        for attempt in range(max_retries):
            try:
                # Dummy response for testing
                if self.config.api_key == "dummy_key":
                    if "요약" in prompt or "summarize" in prompt.lower():
                        return "DUMMY SUMMARY: This is a placeholder summary for testing purposes."
                    if "핵심 포인트" in prompt:
                        return "1. DUMMY POINT 1\n2. DUMMY POINT 2\n3. DUMMY POINT 3"
                    if "태그" in prompt or "tags" in prompt.lower():
                        return "dummy, test, ai"
                    return "DUMMY RESPONSE: Test response."

                result = self._client.generate(prompt, system_prompt=system_prompt, **kwargs)

                # 캐시 저장
                if self.cache_enabled and use_cache:
                    self._save_cache(cache_key, result)

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2**attempt))  # Exponential backoff

        raise last_error

    def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성 (캐싱 없음)"""
        return self._client.generate_stream(prompt, system_prompt=system_prompt, **kwargs)

    # ─────────────────────────────────────────────────────────────
    # 고수준 메서드
    # ─────────────────────────────────────────────────────────────

    def summarize(self, text: str, max_length: int = 200) -> str:
        """텍스트 요약"""
        prompt = f"""다음 텍스트를 {max_length}자 이내로 핵심만 요약해주세요:

{text}

요약:"""
        return self.generate(prompt)

    def extract_keywords(self, text: str, max_keywords: int = 5) -> list[str]:
        """키워드 추출"""
        prompt = f"""다음 텍스트에서 핵심 키워드를 {max_keywords}개 추출해주세요.
쉼표로 구분하여 키워드만 출력하세요.

텍스트:
{text}

키워드:"""
        result = self.generate(prompt)
        return [k.strip() for k in result.split(",")]

    def generate_tags(self, text: str, existing_tags: list[str] = None) -> list[str]:
        """태그 생성"""
        tags_hint = ""
        if existing_tags:
            tags_hint = f"\n사용 가능한 기존 태그: {', '.join(existing_tags)}"

        prompt = f"""다음 콘텐츠에 적합한 태그를 3-5개 생성해주세요.
태그는 소문자 영어 또는 한글로, 띄어쓰기 없이 작성하세요.{tags_hint}

콘텐츠:
{text}

태그 (쉼표로 구분):"""
        result = self.generate(prompt)
        return [t.strip().lower().replace(" ", "_") for t in result.split(",")]

    # ─────────────────────────────────────────────────────────────
    # 캐싱 로직
    # ─────────────────────────────────────────────────────────────

    def _get_cache_key(self, prompt: str, system_prompt: str = None) -> str:
        """캐시 키 생성"""
        content = f"{self.config.model}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> str | None:
        """캐시 조회"""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("response")
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, response: str) -> None:
        """캐시 저장"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{key}.json"

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "key": key,
                    "response": response,
                    "model": self.config.model,
                    "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )


# 편의 함수
_default_client: LLMClient | None = None
_summary_client: LLMClient | None = None
_writer_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """기본 LLM 클라이언트 반환"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def get_summary_client() -> LLMClient:
    """요약/태깅용 LLM 클라이언트 반환 (로컬 우선)"""
    global _summary_client
    if _summary_client is None:
        from .config import get_config

        config = get_config().summary_llm

        # SummaryLLMConfig를 LLMConfig 형태로 변환
        llm_config = LLMConfig(
            provider=config.provider, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens
        )

        # Ollama의 경우 base_url 속성 추가
        if config.provider == "ollama":
            llm_config.base_url = config.base_url
            llm_config.fallback_provider = config.fallback_provider
            llm_config.fallback_model = config.fallback_model
            llm_config.fallback_api_key_env = config.fallback_api_key_env

        _summary_client = LLMClient(config=llm_config)
    return _summary_client


def get_writer_client() -> LLMClient:
    """글쓰기용 LLM 클라이언트 반환 (클라우드)"""
    global _writer_client
    if _writer_client is None:
        from .config import get_config

        config = get_config().writer_llm

        # WriterLLMConfig를 LLMConfig 형태로 변환
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key_env=config.api_key_env,
        )

        _writer_client = LLMClient(config=llm_config)
    return _writer_client
