from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REQUIRED_INDEX_KEYS = ("account_id", "name", "description")
SAFE_INCLUDE_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge dicts; list/scalar replace."""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return loaded


def _validate_includes(includes: Any, index_path: Path) -> list[str]:
    if not isinstance(includes, list) or not all(isinstance(name, str) for name in includes):
        raise ValueError(f"'includes' must be a list of strings: {index_path}")

    for name in includes:
        if "/" in name or "\\" in name:
            raise ValueError(f"Invalid include '{name}': path separators are not allowed in includes ({index_path})")
        if name.startswith("."):
            raise ValueError(
                f"Invalid include '{name}': relative path prefixes are not allowed in includes ({index_path})"
            )
        if not SAFE_INCLUDE_NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid include '{name}': must start with a letter and use only "
                f"letters, numbers, _ or - ({index_path})"
            )

    return includes


def _validate_index_required_keys(cfg: dict[str, Any], index_path: Path) -> None:
    missing = [k for k in REQUIRED_INDEX_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing required keys in _index.yml ({', '.join(missing)}): {index_path}")


def _load_legacy_directory_account(account_dir: Path) -> dict[str, Any]:
    account_path = account_dir / "account.yml"
    if not account_path.exists():
        raise ValueError(
            f"Missing account.yml in legacy directory: {account_dir}. " f"Legacy layout requires account.yml."
        )

    cfg = _load_yaml_dict(account_path)
    for name in ("scoring", "style", "content", "channels", "identity", "weekly_slot"):
        slice_path = account_dir / f"{name}.yml"
        if slice_path.exists():
            cfg = deep_merge(cfg, _load_yaml_dict(slice_path))
    return cfg


def load_account_config(accounts_root: Path, account_id: str) -> dict[str, Any]:
    """Returns {} when not found, raises ValueError for invalid shapes."""
    account_dir = accounts_root / account_id
    index = account_dir / "_index.yml"
    if index.exists():
        cfg = _load_yaml_dict(index)
        _validate_index_required_keys(cfg, index)
        includes = _validate_includes(cfg.get("includes", []), index)
        for name in includes:
            slice_path = account_dir / f"{name}.yml"
            if not slice_path.exists():
                available = sorted(path.stem for path in account_dir.glob("*.yml") if path.name != "_index.yml")
                available_text = ", ".join(available) if available else "(none)"
                raise ValueError(
                    f"Missing slice file: {slice_path}. "
                    f"Requested include: {name}. Available: {available_text}. "
                    "Check _index.yml includes or create the missing slice file."
                )
            cfg = deep_merge(cfg, _load_yaml_dict(slice_path))
        return cfg

    if account_dir.exists() and account_dir.is_dir():
        return _load_legacy_directory_account(account_dir)

    legacy = accounts_root / f"{account_id}.yml"
    if legacy.exists():
        return _load_yaml_dict(legacy)
    return {}
