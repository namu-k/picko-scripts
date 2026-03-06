"""Tests for account CLI commands."""

from unittest.mock import MagicMock, patch

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
