"""Migrate account profiles from single-file to directory structure."""

import argparse
from pathlib import Path
from typing import Any

import yaml

from picko.logger import get_logger

logger = get_logger("migrate_accounts")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write YAML file with migration metadata header."""
    header = "# Migrated from single-file structure\n# See .yml.bak for original\n\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_reference_style(style_name: str, config_dir: Path) -> dict[str, Any] | None:
    """Load optional reference style profile by style name."""
    profile_path = config_dir / "reference_styles" / style_name / "profile.yml"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if isinstance(loaded, dict):
            return loaded
    return None


def migrate_account(account_id: str, project_root: Path | None = None) -> None:
    """Migrate one account file into directory format.

    Args:
        account_id: account ID (source: config/accounts/{account_id}.yml)
        project_root: repository root containing config/
    """
    if project_root is None:
        project_root = PROJECT_ROOT

    config_dir = project_root / "config"
    accounts_dir = config_dir / "accounts"
    src = accounts_dir / f"{account_id}.yml"
    if not src.exists():
        logger.error(f"Account file not found: {src}")
        return

    with open(src, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if not isinstance(loaded, dict):
        logger.error(f"Account file is not a dict: {src}")
        return

    logger.info(f"Migrating account: {account_id}")

    out_dir = accounts_dir / account_id
    out_dir.mkdir(parents=True, exist_ok=True)

    account = {
        "account_id": loaded.get("account_id", account_id),
        "name": loaded.get("name", ""),
        "description": loaded.get("description", ""),
        "one_liner": loaded.get("one_liner", ""),
        "target_audience": loaded.get("target_audience", []),
        "value_proposition": loaded.get("value_proposition", ""),
        "pillars": loaded.get("pillars", []),
        "boundaries": loaded.get("boundaries", []),
        "bio": loaded.get("bio", ""),
        "channels": loaded.get("channels", {}),
    }
    write_yaml(out_dir / "account.yml", account)

    scoring = {
        "interests": loaded.get("interests", {"primary": [], "secondary": []}),
        "keywords": loaded.get(
            "keywords",
            {"high_relevance": [], "medium_relevance": [], "low_relevance": []},
        ),
        "trusted_sources": loaded.get("trusted_sources", []),
    }
    write_yaml(out_dir / "scoring.yml", scoring)

    style: dict[str, Any] = {
        "visual_settings": loaded.get("visual_settings", {}),
    }
    style_name = loaded.get("style_name")
    if isinstance(style_name, str) and style_name:
        ref_profile = load_reference_style(style_name, config_dir)
        if ref_profile:
            characteristics = ref_profile.get("characteristics", {})
            if isinstance(characteristics, dict):
                tone_value = characteristics.get("tone", [])
                forbidden_value = characteristics.get("forbidden", [])
                if isinstance(tone_value, list):
                    tone_primary = ", ".join(tone_value)
                else:
                    tone_primary = str(tone_value)
                if isinstance(forbidden_value, list):
                    forbidden_primary = ", ".join(forbidden_value)
                else:
                    forbidden_primary = str(forbidden_value)

                style["tone"] = {
                    "primary": tone_primary,
                    "forbidden": forbidden_primary,
                    "cta_style": str(characteristics.get("cta_style", "")),
                }
                style["sentence_style"] = str(characteristics.get("sentence_style", ""))
                vocab = characteristics.get("vocabulary", [])
                style["vocabulary"] = vocab if isinstance(vocab, list) else []
    write_yaml(out_dir / "style.yml", style)

    backup_path = src.with_suffix(".yml.bak")
    src.rename(backup_path)

    logger.info(f"Migration complete: {account_id}")
    logger.info(f"Backup: {backup_path}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Migrate accounts to directory structure")
    parser.add_argument("accounts", nargs="*", help="Account IDs to migrate")
    parser.add_argument("--all", action="store_true", help="Migrate all single-file accounts")
    parser.add_argument("--dry-run", action="store_true", help="Show migration targets only")
    args = parser.parse_args()

    accounts_dir = PROJECT_ROOT / "config" / "accounts"
    if args.all:
        accounts = [f.stem for f in accounts_dir.glob("*.yml") if not f.name.endswith(".bak")]
    else:
        accounts = args.accounts

    if not accounts:
        print("No accounts to migrate. Use --all or provide account IDs.")
        return

    print(f"Accounts to migrate: {accounts}")
    if args.dry_run:
        print("DRY RUN - no changes made")
        return

    for account_id in accounts:
        migrate_account(account_id)

    print(f"Migrated {len(accounts)} account(s)")


if __name__ == "__main__":
    main()
