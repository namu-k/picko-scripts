from pathlib import Path

import pytest
import yaml

import picko.config as config_module
from picko.config import load_config


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
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
    accounts_dir = temp_repo / "config" / "accounts" / "test_account"
    accounts_dir.mkdir(parents=True)

    with open(accounts_dir / "_index.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {
                "account_id": "test_account",
                "name": "Test Account",
                "description": "Test description",
                "style_name": "test_style",
                "includes": ["scoring", "content"],
            },
            f,
            sort_keys=False,
        )

    with open(accounts_dir / "scoring.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {
                "interests": {"primary": ["AI"], "secondary": ["tech"]},
                "keywords": {
                    "high_relevance": ["AI"],
                    "medium_relevance": [],
                    "low_relevance": [],
                },
                "trusted_sources": ["TechCrunch"],
            },
            f,
            sort_keys=False,
        )

    with open(accounts_dir / "content.yml", "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"visual_settings": {"default_layout_preset": "minimal_dark"}},
            f,
            sort_keys=False,
        )

    return accounts_dir


def test_get_account_loads_from_directory(
    temp_repo: Path,
    account_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _ = account_dir
    cfg = load_config(temp_repo / "config" / "config.yml")
    monkeypatch.setattr(config_module, "PROJECT_ROOT", temp_repo)

    loaded = cfg.get_account("test_account")

    assert loaded["account_id"] == "test_account"
    assert loaded["interests"]["primary"] == ["AI"]
    assert loaded["visual_settings"]["default_layout_preset"] == "minimal_dark"


def test_get_account_loads_from_directory_with_project_root_fallback(
    temp_repo: Path,
    account_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _ = account_dir
    cfg = load_config(temp_repo / "config" / "config.yml")
    monkeypatch.setattr(config_module, "PROJECT_ROOT", temp_repo)

    loaded = cfg.get_account("test_account")

    assert loaded["account_id"] == "test_account"
    assert loaded["interests"]["primary"] == ["AI"]
    assert loaded["visual_settings"]["default_layout_preset"] == "minimal_dark"


def test_get_account_falls_back_to_single_file(temp_repo: Path, monkeypatch: pytest.MonkeyPatch):
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
