from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from scripts.health_check import HealthChecker


def _build_config(tmp_path: Path):
    cfg = SimpleNamespace()
    cfg.vault = SimpleNamespace(
        root=str(tmp_path),
        inbox="Inbox/Inputs",
        digests="Inbox/Inputs/_digests",
        longform="Content/Longform",
        packs="Content/Packs",
        images_prompts="Assets/Images/_prompts",
    )
    cfg.llm = SimpleNamespace(api_key_env="OPENAI_API_KEY")
    cfg.sources = {"sources": [{"id": "s1", "url": "https://example.com/feed", "enabled": True}]}
    return cfg


def test_check_api_keys_pass_and_mask(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())
    monkeypatch.setenv("OPENAI_API_KEY", "sk-1234567890abcdef")

    checker = HealthChecker()
    checker.check_api_keys()

    result = checker.results[-1]
    assert result.name == "OpenAI API Key"
    assert result.passed is True
    assert "..." in result.details


def test_check_sources_collects_failed_status(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())

    class _Resp:
        def __init__(self, code):
            self.status_code = code

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def head(self, *args, **kwargs):
            return _Resp(500)

    monkeypatch.setattr("scripts.health_check.httpx.Client", lambda timeout: _Client())

    checker = HealthChecker()
    checker.check_sources()
    result = checker.results[-1]
    assert result.name == "RSS Sources"
    assert result.passed is False
    assert "0/1" in result.message


def test_check_directories_reports_missing(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    (tmp_path / "Inbox").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())

    checker = HealthChecker()
    checker.check_directories()
    result = checker.results[-1]

    assert result.name == "Directories"
    assert result.passed is False
    assert "missing" in result.message


def test_run_all_returns_five_checks(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    for rel in [
        "Inbox/Inputs",
        "Inbox/Inputs/_digests",
        "Content/Longform",
        "Content/Packs",
        "Assets/Images/_prompts",
    ]:
        (tmp_path / rel).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class _Resp:
        status_code = 200

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def head(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("scripts.health_check.httpx.Client", lambda timeout: _Client())
    monkeypatch.setattr("shutil.disk_usage", lambda path: (10, 5, 5 * 1024**3))

    checker = HealthChecker()
    results = checker.run_all()

    assert len(results) == 5
    assert {r.name for r in results} == {
        "Vault Access",
        "OpenAI API Key",
        "RSS Sources",
        "Directories",
        "Disk Space",
    }


def test_check_api_keys_missing_reports_failure(tmp_path, monkeypatch):
    """Covers line 99: else branch when API key env var is not set."""
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    checker = HealthChecker()
    checker.check_api_keys()

    result = checker.results[-1]
    assert result.name == "OpenAI API Key"
    assert result.passed is False
    assert "Not set" in result.message


def test_check_sources_handles_request_exception(tmp_path, monkeypatch):
    """Covers lines 132-133: exception handler in check_sources HTTP loop."""
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.health_check.get_config", lambda: config)
    monkeypatch.setattr("scripts.health_check.VaultIO", lambda: MagicMock())

    class _ClientRaising:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def head(self, *args, **kwargs):
            raise RuntimeError("connection refused")

    monkeypatch.setattr("scripts.health_check.httpx.Client", lambda timeout: _ClientRaising())

    checker = HealthChecker()
    checker.check_sources()

    result = checker.results[-1]
    assert result.name == "RSS Sources"
    assert result.passed is False
    # Error message from the exception should appear in details
    assert "connection refused" in result.details
