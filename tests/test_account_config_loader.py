from pathlib import Path

import pytest
import yaml

from picko.account_config_loader import _validate_includes, deep_merge, load_account_config


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def test_loader_loads_directory_account_with_includes(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    account_dir = accounts_root / "acme"

    _write_yaml(
        account_dir / "_index.yml",
        {
            "account_id": "acme",
            "name": "acme",
            "description": "acme desc",
            "style_name": "acme_style",
            "includes": ["scoring", "style"],
        },
    )
    _write_yaml(account_dir / "scoring.yml", {"weights": {"novelty": 0.7}, "tags": ["alpha"]})
    _write_yaml(account_dir / "style.yml", {"visual_settings": {"theme": "light"}})

    got = load_account_config(accounts_root, "acme")

    assert got["name"] == "acme"
    assert got["weights"] == {"novelty": 0.7}
    assert got["tags"] == ["alpha"]
    assert got["visual_settings"] == {"theme": "light"}
    assert got["includes"] == ["scoring", "style"]


def test_loader_conflict_directory_wins_over_legacy(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"

    _write_yaml(accounts_root / "acme.yml", {"source": "legacy"})
    _write_yaml(
        accounts_root / "acme" / "_index.yml",
        {
            "account_id": "acme",
            "name": "directory",
            "description": "desc",
            "style_name": "style",
        },
    )

    got = load_account_config(accounts_root, "acme")

    assert got["name"] == "directory"


def test_deep_merge_dicts() -> None:
    base = {"a": {"x": 1, "y": 2}, "b": 10}
    override = {"a": {"y": 99, "z": 3}}

    got = deep_merge(base, override)

    assert got == {"a": {"x": 1, "y": 99, "z": 3}, "b": 10}


def test_deep_merge_lists_replace() -> None:
    base = {"items": [1, 2], "keep": "ok"}
    override = {"items": [3]}

    got = deep_merge(base, override)

    assert got == {"items": [3], "keep": "ok"}


def test_deep_merge_scalars_replace() -> None:
    base = {"threshold": 1, "keep": "ok"}
    override = {"threshold": 2}

    got = deep_merge(base, override)

    assert got == {"threshold": 2, "keep": "ok"}


def test_loader_returns_empty_for_not_found(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"

    got = load_account_config(accounts_root, "missing")

    assert got == {}


def test_loader_raises_valueerror_for_missing_slice(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    _write_yaml(
        accounts_root / "acme" / "_index.yml",
        {
            "account_id": "acme",
            "name": "acme",
            "description": "desc",
            "style_name": "style",
            "includes": ["scoring"],
        },
    )

    with pytest.raises(ValueError, match="Missing slice file"):
        _ = load_account_config(accounts_root, "acme")


def test_loader_raises_valueerror_for_invalid_includes_shape(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    _write_yaml(
        accounts_root / "acme" / "_index.yml",
        {
            "account_id": "acme",
            "name": "acme",
            "description": "desc",
            "style_name": "style",
            "includes": "scoring",
        },
    )

    with pytest.raises(ValueError, match="includes"):
        _ = load_account_config(accounts_root, "acme")


def test_loader_raises_valueerror_for_missing_required_index_keys(
    tmp_path: Path,
) -> None:
    accounts_root = tmp_path / "accounts"
    _write_yaml(accounts_root / "acme" / "_index.yml", {"account_id": "acme"})

    with pytest.raises(ValueError, match="Missing required keys in _index.yml"):
        _ = load_account_config(accounts_root, "acme")


def test_loader_raises_valueerror_when_directory_missing_index(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    (accounts_root / "acme").mkdir(parents=True)

    with pytest.raises(ValueError, match="Missing account.yml"):
        _ = load_account_config(accounts_root, "acme")


def test_loader_loads_legacy_directory_without_index(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    account_dir = accounts_root / "acme"

    _write_yaml(
        account_dir / "account.yml",
        {
            "account_id": "acme",
            "name": "legacy-dir",
            "description": "desc",
            "target_audience": ["founders"],
        },
    )
    _write_yaml(account_dir / "scoring.yml", {"interests": {"primary": ["ai"]}})
    _write_yaml(account_dir / "style.yml", {"visual_settings": {"theme": "dark"}})

    got = load_account_config(accounts_root, "acme")

    assert got["name"] == "legacy-dir"
    assert got["interests"]["primary"] == ["ai"]
    assert got["visual_settings"]["theme"] == "dark"


def test_validate_includes_rejects_parent_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid include"):
        _validate_includes(["../secret"], Path("accounts/acme/_index.yml"))


def test_validate_includes_rejects_absolute_or_prefixed_path() -> None:
    with pytest.raises(ValueError, match="Invalid include"):
        _validate_includes(["/etc/passwd"], Path("accounts/acme/_index.yml"))

    with pytest.raises(ValueError, match="Invalid include"):
        _validate_includes(["./scoring"], Path("accounts/acme/_index.yml"))


def test_validate_includes_rejects_special_characters() -> None:
    with pytest.raises(ValueError, match="Invalid include"):
        _validate_includes(["scoring$HOST"], Path("accounts/acme/_index.yml"))


def test_validate_includes_accepts_simple_safe_names() -> None:
    includes = _validate_includes(["scoring", "style", "channels_v2"], Path("accounts/acme/_index.yml"))
    assert includes == ["scoring", "style", "channels_v2"]


def test_missing_slice_error_lists_available_files(tmp_path: Path) -> None:
    accounts_root = tmp_path / "accounts"
    account_dir = accounts_root / "acme"

    _write_yaml(
        account_dir / "_index.yml",
        {
            "account_id": "acme",
            "name": "acme",
            "description": "desc",
            "includes": ["nonexistent"],
        },
    )
    _write_yaml(account_dir / "style.yml", {"visual_settings": {"theme": "dark"}})

    with pytest.raises(ValueError) as exc_info:
        _ = load_account_config(accounts_root, "acme")

    message = str(exc_info.value)
    assert "nonexistent" in message
    assert "Available" in message
    assert "style" in message
