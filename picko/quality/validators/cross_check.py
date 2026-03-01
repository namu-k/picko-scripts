"""
Cross-Check Validator - Second pass LLM validation.

Uses a different LLM model than primary validation for independent verification.
Calculates agreement between primary and cross-check results.
"""

import json
from typing import Any

from picko.config import get_config
from picko.llm_client import LLMClient
from picko.logger import get_logger

logger = get_logger("quality.validators.cross_check")

CROSS_CHECK_PROMPT = """다음 콘텐츠에 대한 2차 검증을 수행해주세요.

제목: {title}
내용: {content}
1차 검증 결과: {primary_verdict} (신뢰도: {primary_confidence:.2f})

**중요**: 1차 검증 결과를 참고만 하고, 독립적으로 평가하세요.

JSON 형식으로만 응답하세요. 다른 설명 없이 JSON만 출력:
{{
  "verdict": "approved|rejected|needs_review",
  "confidence": 0.0-1.0,
  "reasoning": "판단 근거"
}}"""


def parse_json_response(response: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM response."""
    if not response:
        return _fallback_result("Empty response from LLM")

    try:
        result: dict[str, Any] = json.loads(response)
        return result
    except json.JSONDecodeError:
        pass

    try:
        # Remove markdown code blocks
        cleaned = response.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline >= 0:
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1

        if start >= 0 and end > start:
            result = json.loads(cleaned[start:end])
            return result
    except json.JSONDecodeError:
        pass

    return _fallback_result(f"Failed to parse response: {response[:100]}")


def _fallback_result(reason: str) -> dict[str, Any]:
    """Return fallback result when parsing fails."""
    return {
        "verdict": "needs_review",
        "confidence": 0.5,
        "reasoning": reason,
    }


class CrossCheckValidator:
    """
    Second-pass validator using a different LLM model.

    Provides independent verification of primary validation results.
    Typically uses Claude if primary used GPT, or vice versa.
    """

    # Default model mappings for cross-check
    PROVIDER_ALTERNATIVES = {
        "openai": ("anthropic", "claude-3-5-sonnet-20241022"),
        "openrouter": ("openai", "gpt-4o-mini"),
        "relay": ("openai", "gpt-4o-mini"),
        "anthropic": ("openai", "gpt-4o-mini"),
        "ollama": ("openai", "gpt-4o-mini"),  # Fallback to cloud for cross-check
    }

    def __init__(self, provider: str | None = None, model: str | None = None):
        """
        Initialize CrossCheckValidator.

        Args:
            provider: Optional provider override (auto-detected if not provided)
            model: Optional model override (auto-detected if not provided)
        """
        self.provider = provider
        self.model = model
        self._llm: LLMClient | None = None

    @property
    def llm(self) -> LLMClient:
        """Lazy-load LLM client with alternative model."""
        if self._llm is None:
            self._llm = self._create_cross_check_client()
        return self._llm

    def _create_cross_check_client(self) -> LLMClient:
        """Create LLM client with alternative model for cross-check."""
        config = get_config()

        # Determine alternative provider/model
        if self.provider and self.model:
            provider = self.provider
            model = self.model
        else:
            primary_provider = config.summary_llm.provider
            provider, model = self.PROVIDER_ALTERNATIVES.get(primary_provider, ("openai", "gpt-4o-mini"))

        # Build LLMConfig for the alternative provider
        from picko.config import LLMConfig

        # Determine API key env based on provider
        if provider == "anthropic":
            api_key_env = "ANTHROPIC_API_KEY"
        elif provider == "openrouter":
            api_key_env = "OPENROUTER_API_KEY"
        elif provider == "relay":
            api_key_env = "RELAY_API_KEY"
        else:
            api_key_env = "OPENAI_API_KEY"

        llm_config = LLMConfig(
            provider=provider,
            model=model,
            temperature=0.3,  # Lower temperature for more consistent evaluation
            max_tokens=500,
            api_key_env=api_key_env,
        )

        logger.info(f"Cross-check using {provider}/{model}")
        return LLMClient(config=llm_config)

    def validate(
        self,
        title: str,
        content: str,
        primary_verdict: str,
        primary_confidence: float,
    ) -> dict[str, Any]:
        """
        Perform cross-check validation.

        Args:
            title: Content title
            content: Full content text
            primary_verdict: Verdict from primary validation
            primary_confidence: Confidence from primary validation

        Returns:
            Dict with keys:
                - verdict: "approved", "rejected", or "needs_review"
                - confidence: float 0.0-1.0
                - reasoning: str explaining the verdict
                - agreement: bool indicating if verdicts match
        """
        # Truncate content
        max_content_length = 2000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "\n... (truncated)"

        prompt = CROSS_CHECK_PROMPT.format(
            title=title or "(No title)",
            content=truncated_content or "(No content)",
            primary_verdict=primary_verdict,
            primary_confidence=primary_confidence,
        )

        try:
            response = self.llm.generate(prompt, use_cache=False)
            result = parse_json_response(response)

            # Normalize result
            result = self._normalize_result(result)

            # Calculate agreement
            result["agreement"] = result["verdict"] == primary_verdict

            logger.info(
                f"Cross-check: verdict={result['verdict']}, "
                f"confidence={result['confidence']:.2f}, "
                f"agreement={result['agreement']}"
            )

            return result

        except Exception as e:
            logger.error(f"Cross-check validation failed: {e}")
            result = _fallback_result(f"Cross-check error: {str(e)}")
            result["agreement"] = False
            return result

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure result has all required fields with valid values."""
        # Normalize verdict
        verdict = result.get("verdict", "needs_review").lower()
        if verdict not in ("approved", "rejected", "needs_review"):
            verdict = "needs_review"
        result["verdict"] = verdict

        # Normalize confidence
        confidence = result.get("confidence", 0.5)
        if isinstance(confidence, (int, float)):
            result["confidence"] = max(0.0, min(1.0, float(confidence)))
        else:
            result["confidence"] = 0.5

        # Ensure reasoning
        if "reasoning" not in result or not isinstance(result["reasoning"], str):
            result["reasoning"] = "No reasoning provided"

        return result
