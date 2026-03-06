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


def test_migration_skips_existing_directory_without_force(tmp_path: Path):
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    src = accounts_dir / "test_account.yml"
    with open(src, "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "Legacy Name"}, f)

    out_dir = accounts_dir / "test_account"
    out_dir.mkdir(parents=True)
    with open(out_dir / "account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "MODIFIED NAME"}, f)

    migrate_account("test_account", tmp_path)

    with open(out_dir / "account.yml", "r", encoding="utf-8") as f:
        persisted = yaml.safe_load(f)

    assert persisted["name"] == "MODIFIED NAME"
    assert src.exists()
    assert not src.with_suffix(".yml.bak").exists()


def test_migration_force_overwrites_existing_directory(tmp_path: Path):
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    src = accounts_dir / "test_account.yml"
    with open(src, "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "Legacy Name"}, f)

    out_dir = accounts_dir / "test_account"
    out_dir.mkdir(parents=True)
    with open(out_dir / "account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "MODIFIED NAME"}, f)

    migrate_account("test_account", tmp_path, force=True)

    with open(out_dir / "account.yml", "r", encoding="utf-8") as f:
        persisted = yaml.safe_load(f)

    assert persisted["name"] == "Legacy Name"
    assert src.with_suffix(".yml.bak").exists()


def test_migration_preserves_existing_backup_with_timestamp(tmp_path: Path):
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    src = accounts_dir / "test_account.yml"
    with open(src, "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "Legacy Name"}, f)

    backup = src.with_suffix(".yml.bak")
    backup.write_text("existing backup", encoding="utf-8")

    migrate_account("test_account", tmp_path, force=True)

    assert backup.exists()
    backups = sorted(accounts_dir.glob("test_account.yml.bak.*"))
    assert backups


def test_migration_warns_when_directory_exists_without_force(tmp_path: Path, capsys):
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    src = accounts_dir / "test_account.yml"
    with open(src, "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "Legacy Name"}, f)

    out_dir = accounts_dir / "test_account"
    out_dir.mkdir(parents=True)
    with open(out_dir / "account.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"account_id": "test_account", "name": "MODIFIED NAME"}, f)

    migrate_account("test_account", tmp_path)
    captured = capsys.readouterr()

    assert "already exists" in captured.out
    assert "use --force" in captured.out
