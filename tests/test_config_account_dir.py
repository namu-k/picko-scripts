"""Tests for account directory loading in Config."""

from pathlib import Path

import pytest
import yaml

import picko.config as config_module
from picko.config import load_config


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create temporary repo-style layout with config.yml."""
    repo = tmp_path / "repo"
    config_dir = repo / "config"
    config_dir.mkdir(parents=True)

    config_data = {
        "vault": {"root": str(repo / "vault")},
        "accounts_dir": "config/accounts",
    }
    with open(config_dir / "config.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)

    (repo / "vault").mkdir(parents=True)
    return repo


@pytest.fixture
def account_dir(temp_repo: Path) -> Path:
    """Create directory-based account profile."""
    accounts_dir = temp_repo / "config" / "accounts" / "test_account"
    accounts_dir.mkdir(parents=True)

    account_data = {
        "account_id": "test_account",
        "name": "Test Account",
        "description": "Test description",
        "target_audience": ["developers"],
        "channels": {"twitter": {"enabled": True}},
    }
    with open(accounts_dir / "account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(account_data, f)

    scoring_data = {
        "interests": {"primary": ["AI"], "secondary": ["tech"]},
        "keywords": {
            "high_relevance": ["AI"],
            "medium_relevance": [],
            "low_relevance": [],
        },
        "trusted_sources": ["TechCrunch"],
    }
    with open(accounts_dir / "scoring.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(scoring_data, f)

    style_data = {
        "tone": {"primary": "professional"},
        "visual_settings": {"default_layout_preset": "minimal_dark"},
    }
    with open(accounts_dir / "style.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(style_data, f)

    return accounts_dir


def test_load_account_dir_merges_all_files(temp_repo: Path, account_dir: Path):
    """_load_account_dir should merge account/scoring/style into one dict."""
    cfg = load_config(temp_repo / "config" / "config.yml")
    merged = cfg._load_account_dir(account_dir)

    assert merged["account_id"] == "test_account"
    assert merged["name"] == "Test Account"
    assert merged["interests"]["primary"] == ["AI"]
    assert merged["keywords"]["high_relevance"] == ["AI"]
    assert merged["trusted_sources"] == ["TechCrunch"]
    assert merged["visual_settings"]["default_layout_preset"] == "minimal_dark"


def test_get_account_loads_from_directory_with_project_root_fallback(
    temp_repo: Path,
    account_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """get_account should load directory profile from PROJECT_ROOT fallback path."""
    cfg = load_config(temp_repo / "config" / "config.yml")
    monkeypatch.setattr(config_module, "PROJECT_ROOT", temp_repo)

    loaded = cfg.get_account("test_account")

    assert loaded["account_id"] == "test_account"
    assert loaded["interests"]["primary"] == ["AI"]
    assert loaded["visual_settings"]["default_layout_preset"] == "minimal_dark"


def test_get_account_falls_back_to_single_file(temp_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """get_account should preserve legacy single-file compatibility."""
    accounts_dir = temp_repo / "config" / "accounts"
    accounts_dir.mkdir(parents=True, exist_ok=True)

    legacy_data = {
        "account_id": "legacy_account",
        "name": "Legacy",
        "interests": {"primary": ["old"]},
    }
    with open(accounts_dir / "legacy_account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(legacy_data, f)

    cfg = load_config(temp_repo / "config" / "config.yml")
    monkeypatch.setattr(config_module, "PROJECT_ROOT", temp_repo)

    loaded = cfg.get_account("legacy_account")

    assert loaded["account_id"] == "legacy_account"
    assert loaded["name"] == "Legacy"
