from types import SimpleNamespace
from unittest.mock import MagicMock

from scripts.publish_log import PublishLogManager


def _build_config():
    cfg = SimpleNamespace()
    cfg.vault = SimpleNamespace(root=".")
    return cfg


def test_create_success_writes_log(monkeypatch):
    vault = MagicMock()
    vault.read_note.return_value = (
        {"id": "input_1", "title": "Hello", "type": "longform"},
        "body",
    )
    renderer = MagicMock()
    renderer.render_string.return_value = "rendered"

    monkeypatch.setattr("scripts.publish_log.get_config", _build_config)
    monkeypatch.setattr("scripts.publish_log.VaultIO", lambda: vault)
    monkeypatch.setattr("scripts.publish_log.get_renderer", lambda: renderer)

    manager = PublishLogManager()
    result = manager.create("Content/Longform/x.md", platform="twitter")

    assert result["success"] is True
    assert result["log_path"].startswith("Logs/Publish/pub_input_1_")
    vault.write_note.assert_called_once()


def test_create_error_returns_message(monkeypatch):
    vault = MagicMock()
    vault.read_note.side_effect = RuntimeError("boom")

    monkeypatch.setattr("scripts.publish_log.get_config", _build_config)
    monkeypatch.setattr("scripts.publish_log.VaultIO", lambda: vault)
    monkeypatch.setattr("scripts.publish_log.get_renderer", lambda: MagicMock())

    manager = PublishLogManager()
    result = manager.create("bad.md")

    assert result["success"] is False
    assert "boom" in result["error"]


def test_update_status_validates_and_sets_published_at(monkeypatch):
    vault = MagicMock()
    monkeypatch.setattr("scripts.publish_log.get_config", _build_config)
    monkeypatch.setattr("scripts.publish_log.VaultIO", lambda: vault)
    monkeypatch.setattr("scripts.publish_log.get_renderer", lambda: MagicMock())

    manager = PublishLogManager()

    assert manager.update_status("Logs/Publish/log.md", "invalid") is False
    assert manager.update_status("Logs/Publish/log.md", "published") is True

    args, _ = vault.update_frontmatter.call_args
    assert args[0] == "Logs/Publish/log.md"
    assert args[1]["status"] == "published"
    assert "published_at" in args[1]


def test_list_logs_filters_status(monkeypatch, tmp_path):
    note1 = tmp_path / "a.md"
    note2 = tmp_path / "b.md"

    vault = MagicMock()
    vault.list_notes.return_value = [note1, note2]
    vault.read_frontmatter.side_effect = [
        {
            "id": "1",
            "content_id": "c1",
            "platform": "twitter",
            "status": "draft",
            "scheduled_at": None,
        },
        {
            "id": "2",
            "content_id": "c2",
            "platform": "linkedin",
            "status": "published",
            "scheduled_at": None,
        },
    ]

    monkeypatch.setattr("scripts.publish_log.get_config", _build_config)
    monkeypatch.setattr("scripts.publish_log.VaultIO", lambda: vault)
    monkeypatch.setattr("scripts.publish_log.get_renderer", lambda: MagicMock())

    manager = PublishLogManager()
    published = manager.list_logs(status="published")

    assert len(published) == 1
    assert published[0]["id"] == "2"
