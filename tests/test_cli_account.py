"""Tests for account CLI commands."""

from unittest.mock import MagicMock, patch

import yaml

import picko.__main__ as cli


def test_account_init_creates_directory_structure(tmp_path):
    """`picko account init` should create target account directory."""
    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch(
            "picko.__main__.prompt",
            side_effect=[
                "new_account",
                "New Account",
                "Test description",
                "developers, founders",
                "Optional one-liner",
            ],
        ):
            with patch("picko.__main__.multiselect", return_value=["twitter", "linkedin"]):
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                        instance = mock_inferrer.return_value
                        cli.cmd_account_init(dry_run=False)

    account_dir = tmp_path / "config" / "accounts" / "new_account"
    assert account_dir.is_dir()
    assert instance.generate_account_files.called


def test_account_regen_style_writes_content_slice(tmp_path):
    account_dir = tmp_path / "config" / "accounts" / "new_account"
    account_dir.mkdir(parents=True)

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                mock_get_config.return_value.get_account.return_value = {
                    "account_id": "new_account",
                    "name": "New Account",
                    "description": "Test description",
                    "target_audience": ["developers"],
                    "channels": {"twitter": {"enabled": True}},
                }
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    instance = mock_inferrer.return_value
                    instance.infer_style.return_value = {
                        "tone": {
                            "primary": "friendly",
                            "forbidden": "salesy",
                            "cta_style": "soft",
                        },
                        "sentence_style": "medium_balanced",
                        "structure_patterns": ["hook -> insight"],
                        "vocabulary": ["plain"],
                        "visual_settings": {
                            "default_layout_preset": "minimal_light",
                            "channel_layouts": {},
                        },
                        "content_themes": ["dev updates"],
                    }
                    instance._build_content_yml.return_value = {
                        "visual_settings": {"default_layout_preset": "minimal_light"},
                        "content_themes": ["dev updates"],
                    }

                    cli.cmd_account_regen("style", "new_account")

    expected_path = account_dir / "content.yml"
    instance._write_yaml.assert_called_once_with(
        expected_path,
        {
            "visual_settings": {"default_layout_preset": "minimal_light"},
            "content_themes": ["dev updates"],
        },
    )


def test_account_regen_scoring_preserves_existing_file_on_empty_result(tmp_path):
    account_dir = tmp_path / "config" / "accounts" / "new_account"
    account_dir.mkdir(parents=True)

    scoring_path = account_dir / "scoring.yml"
    original_scoring = {
        "interests": {"primary": ["AI", "ML"], "secondary": ["infra"]},
        "keywords": {
            "high_relevance": ["ai"],
            "medium_relevance": ["ml"],
            "low_relevance": ["sports"],
        },
        "trusted_sources": ["TechCrunch"],
    }
    with open(scoring_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(original_scoring, f)

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                mock_get_config.return_value.get_account.return_value = {
                    "account_id": "new_account",
                    "name": "New Account",
                    "description": "Test description",
                    "target_audience": ["developers"],
                    "channels": {"twitter": {"enabled": True}},
                }
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    instance = mock_inferrer.return_value
                    instance.infer_scoring.return_value = {
                        "interests": {"primary": [], "secondary": []},
                        "keywords": {
                            "high_relevance": [],
                            "medium_relevance": [],
                            "low_relevance": [],
                        },
                        "trusted_sources": [],
                    }

                    cli.cmd_account_regen("scoring", "new_account")

    with open(scoring_path, "r", encoding="utf-8") as f:
        reloaded = yaml.safe_load(f)

    assert reloaded == original_scoring
    instance._write_yaml.assert_not_called()


def test_account_regen_scoring_warns_on_empty_result(tmp_path, capsys):
    account_dir = tmp_path / "config" / "accounts" / "new_account"
    account_dir.mkdir(parents=True)

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                mock_get_config.return_value.get_account.return_value = {
                    "account_id": "new_account",
                    "name": "New Account",
                    "description": "Test description",
                    "target_audience": ["developers"],
                    "channels": {"twitter": {"enabled": True}},
                }
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    instance = mock_inferrer.return_value
                    instance.infer_scoring.return_value = {
                        "interests": {"primary": [], "secondary": []},
                        "keywords": {
                            "high_relevance": [],
                            "medium_relevance": [],
                            "low_relevance": [],
                        },
                        "trusted_sources": [],
                    }

                    cli.cmd_account_regen("scoring", "new_account")

    captured = capsys.readouterr()
    assert "Skipped scoring.yml update due to empty inference result" in captured.out
    instance._write_yaml.assert_not_called()


def test_account_init_rejects_path_traversal_id(capsys):
    with patch("picko.__main__.prompt", side_effect=["../secret"]):
        cli.cmd_account_init(dry_run=True)

    captured = capsys.readouterr()
    assert "Invalid account ID" in captured.out


def test_account_init_rejects_special_chars_id(capsys):
    with patch("picko.__main__.prompt", side_effect=["test$account!"]):
        cli.cmd_account_init(dry_run=True)

    captured = capsys.readouterr()
    assert "Invalid account ID" in captured.out


def test_account_init_rejects_leading_digit_id(capsys):
    with patch("picko.__main__.prompt", side_effect=["123account"]):
        cli.cmd_account_init(dry_run=True)

    captured = capsys.readouterr()
    assert "Invalid account ID" in captured.out


def test_account_init_accepts_valid_account_id(capsys):
    with patch(
        "picko.__main__.prompt",
        side_effect=[
            "my_account_123",
            "New Account",
            "Test description",
            "developers, founders",
            "Optional one-liner",
        ],
    ):
        with patch("picko.__main__.multiselect", return_value=["twitter"]):
            cli.cmd_account_init(dry_run=True)

    captured = capsys.readouterr()
    assert "[DRY RUN] Would create" in captured.out


def test_account_regen_handles_list_channels(tmp_path):
    account_dir = tmp_path / "config" / "accounts" / "new_account"
    account_dir.mkdir(parents=True)

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                mock_get_config.return_value.get_account.return_value = {
                    "account_id": "new_account",
                    "name": "New Account",
                    "description": "Test description",
                    "target_audience": ["developers"],
                    "channels": ["twitter", "linkedin"],
                }
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    instance = mock_inferrer.return_value
                    instance.infer_scoring.return_value = {
                        "interests": {"primary": ["ai"], "secondary": []},
                        "keywords": {
                            "high_relevance": ["ai"],
                            "medium_relevance": [],
                            "low_relevance": [],
                        },
                        "trusted_sources": [],
                    }

                    cli.cmd_account_regen("scoring", "new_account")

    called_seed = instance.infer_scoring.call_args[0][0]
    assert called_seed.channels == ["twitter", "linkedin"]


def test_account_regen_handles_dict_channels(tmp_path):
    account_dir = tmp_path / "config" / "accounts" / "new_account"
    account_dir.mkdir(parents=True)

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            with patch("picko.llm_client.get_writer_client", return_value=MagicMock()):
                mock_get_config.return_value.get_account.return_value = {
                    "account_id": "new_account",
                    "name": "New Account",
                    "description": "Test description",
                    "target_audience": ["developers"],
                    "channels": {
                        "twitter": {"enabled": True},
                        "linkedin": {"enabled": False},
                    },
                }
                with patch("picko.account_inferrer.AccountInferrer") as mock_inferrer:
                    instance = mock_inferrer.return_value
                    instance.infer_scoring.return_value = {
                        "interests": {"primary": ["ai"], "secondary": []},
                        "keywords": {
                            "high_relevance": ["ai"],
                            "medium_relevance": [],
                            "low_relevance": [],
                        },
                        "trusted_sources": [],
                    }

                    cli.cmd_account_regen("scoring", "new_account")

    called_seed = instance.infer_scoring.call_args[0][0]
    assert called_seed.channels == ["twitter", "linkedin"]


def test_account_list_deduplicates_directory_and_legacy_entries(tmp_path, capsys):
    accounts_dir = tmp_path / "config" / "accounts"
    accounts_dir.mkdir(parents=True)

    dir_account = accounts_dir / "test_account"
    dir_account.mkdir(parents=True)

    legacy_file = accounts_dir / "test_account.yml"
    with open(legacy_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {
                "account_id": "test_account",
                "name": "Legacy Name",
                "description": "desc",
            },
            f,
            sort_keys=False,
        )

    with patch.object(cli, "PROJECT_ROOT", tmp_path):
        with patch("picko.__main__.get_config") as mock_get_config:
            mock_get_config.return_value.get_account.return_value = {"name": "Dir Name"}
            cli.cmd_account_list()

    captured = capsys.readouterr()
    assert captured.out.count("test_account") == 1
