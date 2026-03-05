"""Tests for AccountInferrer and AccountSeed."""

import json
from unittest.mock import MagicMock

import pytest

from picko.account_inferrer import AccountInferrer, AccountSeed


class TestAccountSeed:
    """Test AccountSeed dataclass."""

    def test_account_seed_minimal(self):
        """Test AccountSeed with minimal required fields."""
        seed = AccountSeed(
            account_id="test_account",
            name="Test Account",
            description="A test account for testing",
            target_audience=["developers", "engineers"],
            channels=["twitter", "linkedin"],
        )

        assert seed.account_id == "test_account"
        assert seed.name == "Test Account"
        assert seed.description == "A test account for testing"
        assert seed.target_audience == ["developers", "engineers"]
        assert seed.channels == ["twitter", "linkedin"]
        assert seed.tone_hints is None
        assert seed.reference_text is None
        assert seed.reference_url is None

    def test_account_seed_with_optional_fields(self):
        """Test AccountSeed with optional fields."""
        seed = AccountSeed(
            account_id="test_account",
            name="Test Account",
            description="A test account",
            target_audience=["developers"],
            channels=["twitter"],
            one_liner="AI-generated one-liner summary",
            tone_hints=["professional", "friendly"],
            reference_text="Some reference content",
            reference_url="https://example.com",
        )

        assert seed.one_liner == "AI-generated one-liner summary"
        assert seed.tone_hints == ["professional", "friendly"]
        assert seed.reference_text == "Some reference content"
        assert seed.reference_url == "https://example.com"


class TestAccountInferrer:
    """Test AccountInferrer class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.generate.return_value = json.dumps(
            {
                "interests": {
                    "primary": ["AI", "startups", "technology"],
                    "secondary": ["marketing", "growth"],
                },
                "keywords": {
                    "high_relevance": ["AI", "startup", "founder"],
                    "medium_relevance": ["growth", "marketing"],
                    "low_relevance": ["news", "trends"],
                },
                "trusted_sources": ["TechCrunch", "Y Combinator"],
            },
            ensure_ascii=False,
        )
        return client

    @pytest.fixture
    def sample_seed(self):
        """Create sample AccountSeed."""
        return AccountSeed(
            account_id="test_account",
            name="Test Account",
            description="AI insights for startup founders",
            target_audience=["startup founders", "tech enthusiasts"],
            channels=["twitter", "linkedin"],
        )

    def test_infer_scoring_returns_valid_structure(self, mock_llm_client, sample_seed):
        """Test that infer_scoring returns valid scoring structure."""
        inferrer = AccountInferrer(mock_llm_client)
        result = inferrer.infer_scoring(sample_seed)

        assert "interests" in result
        assert "primary" in result["interests"]
        assert "secondary" in result["interests"]
        assert "keywords" in result
        assert "high_relevance" in result["keywords"]
        assert "medium_relevance" in result["keywords"]
        assert "low_relevance" in result["keywords"]
        assert "trusted_sources" in result

    def test_infer_scoring_calls_llm_with_correct_prompt(self, mock_llm_client, sample_seed):
        """Test that infer_scoring calls LLM with proper context."""
        inferrer = AccountInferrer(mock_llm_client)
        inferrer.infer_scoring(sample_seed)

        assert mock_llm_client.generate.called
        call_args = mock_llm_client.generate.call_args

        prompt = call_args[1]["prompt"]
        assert "Test Account" in prompt
        assert "AI insights for startup founders" in prompt
        assert "startup founders" in prompt or "tech enthusiasts" in prompt
