"""Tests for account migration script."""

from pathlib import Path
from typing import Any

import yaml

from scripts.migrate_accounts import migrate_account


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def test_migrate_account_creates_directory(tmp_path: Path):
    """Migration should create account directory."""
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    legacy = {
        "account_id": "test_account",
        "name": "Test Account",
        "description": "Test description",
    }
    with open(accounts_dir / "test_account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(legacy, f)

    migrate_account("test_account", tmp_path)

    assert (accounts_dir / "test_account").is_dir()


def test_migrate_account_creates_three_files(tmp_path: Path):
    """Migration should create account.yml/scoring.yml/style.yml."""
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    with open(accounts_dir / "test_account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account"}, f)

    migrate_account("test_account", tmp_path)

    out = accounts_dir / "test_account"
    assert (out / "account.yml").exists()
    assert (out / "scoring.yml").exists()
    assert (out / "style.yml").exists()


def test_migrate_account_splits_content_correctly(tmp_path: Path):
    """Migration should split legacy fields into the right files."""
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    legacy_data = {
        "account_id": "test_account",
        "name": "Test Account",
        "description": "Test description",
        "one_liner": "Test one liner",
        "target_audience": ["developers"],
        "value_proposition": "Test value",
        "channels": {"twitter": {"enabled": True, "tone": "friendly"}},
        "interests": {"primary": ["AI"], "secondary": ["tech"]},
        "keywords": {
            "high_relevance": ["AI"],
            "medium_relevance": [],
            "low_relevance": [],
        },
        "trusted_sources": ["TechCrunch"],
        "visual_settings": {"default_layout_preset": "minimal_dark"},
        "style_name": "test_style",
    }
    with open(accounts_dir / "test_account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(legacy_data, f)

    migrate_account("test_account", tmp_path)

    out = accounts_dir / "test_account"
    account = _load_yaml(out / "account.yml")
    scoring = _load_yaml(out / "scoring.yml")
    style = _load_yaml(out / "style.yml")

    assert account["account_id"] == "test_account"
    assert account["name"] == "Test Account"
    assert "twitter" in account["channels"]
    assert "interests" not in account

    assert scoring["interests"]["primary"] == ["AI"]
    assert scoring["trusted_sources"] == ["TechCrunch"]

    assert style["visual_settings"]["default_layout_preset"] == "minimal_dark"


def test_migrate_account_creates_backup(tmp_path: Path):
    """Migration should create .yml.bak backup file."""
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    src = accounts_dir / "test_account.yml"
    with open(src, "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account"}, f)

    migrate_account("test_account", tmp_path)

    assert src.with_suffix(".yml.bak").exists()
