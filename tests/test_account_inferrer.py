"""Tests for AccountInferrer and AccountSeed."""

import json
from unittest.mock import MagicMock

import pytest
import yaml

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

    def test_infer_style_returns_valid_structure(self, mock_llm_client, sample_seed):
        """Test that infer_style returns valid style structure."""
        mock_llm_client.generate.return_value = json.dumps(
            {
                "tone": {
                    "primary": "professional, insightful",
                    "forbidden": "salesy, clickbait",
                    "cta_style": "soft, natural",
                },
                "sentence_style": "medium_balanced",
                "structure_patterns": ["hook -> insight -> takeaway"],
                "vocabulary": ["business_terms", "action_verbs"],
                "visual_settings": {
                    "default_layout_preset": "minimal_dark",
                    "channel_layouts": {},
                },
                "content_themes": ["startup stories", "growth tactics"],
            },
            ensure_ascii=False,
        )

        inferrer = AccountInferrer(mock_llm_client)
        result = inferrer.infer_style(sample_seed)

        assert "tone" in result
        assert "primary" in result["tone"]
        assert "sentence_style" in result
        assert "visual_settings" in result

    def test_infer_style_includes_reference_text(self, mock_llm_client):
        """Test that infer_style uses reference_text when provided."""
        seed = AccountSeed(
            account_id="test",
            name="Test",
            description="Test",
            target_audience=["devs"],
            channels=["twitter"],
            reference_text="This is existing content style to analyze.",
        )

        inferrer = AccountInferrer(mock_llm_client)
        inferrer.infer_style(seed)

        prompt = mock_llm_client.generate.call_args[1]["prompt"]
        assert "existing content style" in prompt.lower() or "reference" in prompt.lower()

    def test_generate_account_files_creates_directory_structure(self, mock_llm_client, sample_seed, tmp_path):
        """Test that generate_account_files creates proper directory structure."""
        inferrer = AccountInferrer(mock_llm_client)
        output_dir = tmp_path / "test_account"

        inferrer.generate_account_files(sample_seed, output_dir)

        assert output_dir.is_dir()
        assert (output_dir / "_index.yml").exists()
        assert (output_dir / "channels.yml").exists()
        assert (output_dir / "content.yml").exists()
        assert (output_dir / "identity.yml").exists()
        assert (output_dir / "scoring.yml").exists()
        assert not (output_dir / "style.yml").exists()

    def test_generate_account_files_identity_and_channels_content(self, mock_llm_client, sample_seed, tmp_path):
        inferrer = AccountInferrer(mock_llm_client)
        output_dir = tmp_path / "test_account"

        inferrer.generate_account_files(sample_seed, output_dir)

        with open(output_dir / "identity.yml", encoding="utf-8") as f:
            identity = yaml.safe_load(f)
        with open(output_dir / "channels.yml", encoding="utf-8") as f:
            channels = yaml.safe_load(f)
        with open(output_dir / "_index.yml", encoding="utf-8") as f:
            index = yaml.safe_load(f)

        assert identity["one_liner"] == ""
        assert identity["target_audience"] == ["startup founders", "tech enthusiasts"]
        assert "twitter" in channels
        assert "linkedin" in channels
        assert index["account_id"] == "test_account"
        assert "content" in index["includes"]

    def test_generate_account_files_does_not_overwrite_existing(self, mock_llm_client, sample_seed, tmp_path):
        """Test that existing files are not overwritten by default."""
        inferrer = AccountInferrer(mock_llm_client)
        output_dir = tmp_path / "test_account"
        output_dir.mkdir()

        existing_content = {
            "account_id": "existing",
            "name": "Existing",
            "description": "d",
            "style_name": "s",
        }
        with open(output_dir / "_index.yml", "w", encoding="utf-8") as f:
            yaml.safe_dump(existing_content, f)

        inferrer.generate_account_files(sample_seed, output_dir)

        with open(output_dir / "_index.yml", encoding="utf-8") as f:
            index = yaml.safe_load(f)

        assert index["account_id"] == "existing"
