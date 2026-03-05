# tests/test_account_inferrer.py
"""Tests for AccountInferrer and AccountSeed"""

from picko.account_inferrer import AccountSeed


class TestAccountSeed:
    """Test AccountSeed dataclass"""

    def test_account_seed_minimal(self):
        """Test AccountSeed with minimal required fields"""
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
        """Test AccountSeed with optional fields"""
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
