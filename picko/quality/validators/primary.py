"""
Primary Validator - First pass LLM-based content validation.

Evaluates content on:
- Factual accuracy
- Source credibility
- Bias detection
- Value provision
"""

import json
from typing import Any

from picko.llm_client import LLMClient, get_summary_client
from picko.logger import get_logger

logger = get_logger("quality.validators.primary")

PRIMARY_VALIDATION_PROMPT = """다음 콘텐츠를 평가해주세요.

제목: {title}
내용: {content}

평가 기준:
1. 사실 정확성 (0-10): 내용이 사실에 기반하는가?
2. 출처 신뢰성 (0-10): 출처가 신뢰할 수 있는가?
3. 편향 여부 (0-10, 높을수록 편향 없음): 내용이 공정하고 균형 잡혀 있는가?
4. 가치 제공 (0-10): 독자에게 유용한 정보를 제공하는가?

JSON 형식으로만 응답하세요. 다른 설명 없이 JSON만 출력:
{{
  "verdict": "approved|rejected|needs_review",
  "confidence": 0.0-1.0,
  "scores": {{
    "factual": 0-10,
    "source_credibility": 0-10,
    "bias": 0-10,
    "value": 0-10
  }},
  "reasoning": "판단 근거 한 문장",
  "flags": ["문제가 있는 부분들"]
}}"""


def parse_json_response(response: str) -> dict[str, Any]:
    """
    Extract and parse JSON from LLM response.

    Handles various response formats including:
    - Pure JSON
    - JSON embedded in markdown code blocks
    - JSON with surrounding text
    """
    if not response:
        return _fallback_result("Empty response from LLM")

    try:
        # Try direct parse first
        result: dict[str, Any] = json.loads(response)
        return result
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from response
    try:
        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove opening ```json or ```
            first_newline = cleaned.find("\n")
            if first_newline >= 0:
                cleaned = cleaned[first_newline + 1 :]
            # Remove closing ```
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

        # Find JSON object boundaries
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1

        if start >= 0 and end > start:
            json_str = cleaned[start:end]
            result = json.loads(json_str)
            return result
    except json.JSONDecodeError:
        pass

    return _fallback_result(f"Failed to parse LLM response: {response[:100]}")


def _fallback_result(reason: str) -> dict[str, Any]:
    """Return fallback result when parsing fails."""
    return {
        "verdict": "needs_review",
        "confidence": 0.5,
        "scores": {
            "factual": 5,
            "source_credibility": 5,
            "bias": 5,
            "value": 5,
        },
        "reasoning": reason,
        "flags": ["parse_error"],
    }


class PrimaryValidator:
    """
    First-pass content validator using LLM.

    Evaluates content quality across multiple dimensions and returns
    a structured verdict with confidence score.
    """

    def __init__(self, model: str | None = None):
        """
        Initialize PrimaryValidator.

        Args:
            model: Optional model override (uses summary_llm by default)
        """
        self.model = model
        self._llm: LLMClient | None = None

    @property
    def llm(self) -> LLMClient:
        """Lazy-load LLM client."""
        if self._llm is None:
            self._llm = get_summary_client()
        return self._llm

    def validate(self, title: str, content: str) -> dict[str, Any]:
        """
        Validate content and return verdict.

        Args:
            title: Content title
            content: Full content text (will be truncated if too long)

        Returns:
            Dict with keys:
                - verdict: "approved", "rejected", or "needs_review"
                - confidence: float 0.0-1.0
                - scores: dict with factual, source_credibility, bias, value (0-10)
                - reasoning: str explaining the verdict
                - flags: list of problematic aspects
        """
        # Truncate content to avoid token limits
        max_content_length = 3000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "\n... (truncated)"

        prompt = PRIMARY_VALIDATION_PROMPT.format(
            title=title or "(No title)",
            content=truncated_content or "(No content)",
        )

        try:
            response = self.llm.generate(prompt, use_cache=False)
            result = parse_json_response(response)

            # Validate and normalize result
            result = self._normalize_result(result)

            logger.info(f"Primary validation: verdict={result['verdict']}, " f"confidence={result['confidence']:.2f}")

            return result

        except Exception as e:
            logger.error(f"Primary validation failed: {e}")
            return _fallback_result(f"Validation error: {str(e)}")

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure result has all required fields with valid values."""
        # Normalize verdict
        verdict = result.get("verdict", "needs_review").lower()
        if verdict not in ("approved", "rejected", "needs_review"):
            verdict = "needs_review"
        result["verdict"] = verdict

        # Normalize confidence to 0.0-1.0
        confidence = result.get("confidence", 0.5)
        if isinstance(confidence, (int, float)):
            result["confidence"] = max(0.0, min(1.0, float(confidence)))
        else:
            result["confidence"] = 0.5

        # Normalize scores
        default_scores = {
            "factual": 5,
            "source_credibility": 5,
            "bias": 5,
            "value": 5,
        }
        scores = result.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}
        result["scores"] = {k: max(0, min(10, int(scores.get(k, v)))) for k, v in default_scores.items()}

        # Ensure reasoning and flags
        if "reasoning" not in result or not isinstance(result["reasoning"], str):
            result["reasoning"] = "No reasoning provided"
        if "flags" not in result or not isinstance(result["flags"], list):
            result["flags"] = []

        return result
