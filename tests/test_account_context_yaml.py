"""Tests for AccountContextLoader YAML identity loading."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import picko.account_context as account_context_module
from picko.account_context import AccountContextLoader, AccountIdentity


@pytest.fixture
def account_dir(tmp_path: Path) -> Path:
    """Create account directory with account.yml and style.yml."""
    acc_dir = tmp_path / "config" / "accounts" / "test_account"
    acc_dir.mkdir(parents=True)

    account_data = {
        "account_id": "test_account",
        "one_liner": "Test account one liner",
        "target_audience": ["developers", "founders"],
        "value_proposition": "Test value prop",
        "pillars": ["P1: Growth", "P2: Product"],
        "boundaries": ["No politics", "No spam"],
        "bio": "Test bio",
    }
    with open(acc_dir / "account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(account_data, f)

    style_data = {
        "tone": {
            "primary": "professional, friendly",
            "forbidden": "salesy",
            "cta_style": "soft",
        }
    }
    with open(acc_dir / "style.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(style_data, f)

    return acc_dir


def test_load_identity_from_yaml_returns_account_identity(account_dir: Path):
    """_load_identity_from_yaml should return AccountIdentity."""
    loader = AccountContextLoader(account_dir.parent.parent)
    identity = loader._load_identity_from_yaml(account_dir / "account.yml")

    assert isinstance(identity, AccountIdentity)
    assert identity.account_id == "test_account"
    assert identity.one_liner == "Test account one liner"
    assert identity.target_audience == ["developers", "founders"]


def test_load_identity_from_yaml_includes_tone_from_style(account_dir: Path):
    """tone_voice should be populated from style.yml."""
    loader = AccountContextLoader(account_dir.parent.parent)
    identity = loader._load_identity_from_yaml(account_dir / "account.yml")

    assert identity is not None
    assert identity.tone_voice["tone"] == "professional, friendly"
    assert identity.tone_voice["forbidden"] == "salesy"
    assert identity.tone_voice["cta_style"] == "soft"


def test_load_identity_uses_yaml_when_directory_exists(
    account_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """load_identity should prefer config/accounts/{id}/account.yml over legacy markdown."""
    monkeypatch.setattr(account_context_module, "PROJECT_ROOT", tmp_path)

    profile = {
        "account_id": "test_account",
        "one_liner": "Test account one liner",
        "target_audience": ["developers", "founders"],
        "value_proposition": "Test value prop",
        "pillars": ["P1: Growth", "P2: Product"],
        "boundaries": ["No politics", "No spam"],
        "bio": "Test bio",
    }

    mock_config = SimpleNamespace(
        accounts_dir="config/accounts",
        get_account=lambda account_id: profile if account_id == "test_account" else {},
    )
    monkeypatch.setattr(account_context_module, "get_config", lambda: mock_config)

    (tmp_path / "vault").mkdir(parents=True, exist_ok=True)
    loader = AccountContextLoader(tmp_path / "vault")

    identity = loader.load_identity("test_account")

    assert identity is not None
    assert identity.account_id == "test_account"
