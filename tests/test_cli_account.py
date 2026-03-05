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
