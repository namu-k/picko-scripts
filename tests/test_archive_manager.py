from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from scripts.archive_manager import ArchiveManager


def _build_config(tmp_path: Path):
    cfg = SimpleNamespace()
    cfg.vault = SimpleNamespace(inbox="Inbox/Inputs", archive="Archive")
    cfg.embedding = SimpleNamespace(cache_dir=str(tmp_path / "cache"))
    return cfg


def test_run_dry_run_archives_only_old_inbox_items(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    old_note = tmp_path / "old.md"
    new_note = tmp_path / "new.md"
    old_note.write_text("x", encoding="utf-8")
    new_note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [old_note, new_note]
    vault.read_frontmatter.side_effect = [
        {"status": "inbox", "collected_at": "2020-01-01T00:00:00"},
        {"status": "inbox", "collected_at": datetime.now().isoformat()},
    ]

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    result = manager.run(days=30, dry_run=True)

    assert result["scanned"] == 2
    assert result["archived"] == 1
    assert result["errors"] == []


def test_archive_note_updates_and_moves(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    archive_root = tmp_path / "Archive" / "Inputs"
    vault.get_path.return_value = archive_root

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    note = tmp_path / "item.md"
    note.write_text("x", encoding="utf-8")

    assert manager._archive_note(note, {"id": "id-1"}) is True
    vault.update_frontmatter.assert_called_once()
    vault.move_note.assert_called_once()


def test_clean_cache_removes_matching_files(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    cache_dir = Path(config.embedding.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    keep = cache_dir / "keep.json"
    remove = cache_dir / "abc123_embed.json"
    keep.write_text("1", encoding="utf-8")
    remove.write_text("1", encoding="utf-8")

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: MagicMock())

    manager = ArchiveManager()
    cleaned = manager._clean_cache("abc123")

    assert cleaned == 1
    assert keep.exists()
    assert not remove.exists()


def test_list_archivable_filters_by_status_and_age(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
    new_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    old_note = tmp_path / "old.md"
    new_note = tmp_path / "new.md"
    old_note.write_text("x", encoding="utf-8")
    new_note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [old_note, new_note]
    vault.read_frontmatter.side_effect = [
        {"status": "inbox", "id": "old", "title": "Old", "collected_at": old_date},
        {"status": "inbox", "id": "new", "title": "New", "collected_at": new_date},
    ]

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    items = manager.list_archivable(days=30)

    assert len(items) == 1
    assert items[0]["id"] == "old"


def test_run_non_dry_archives_old_items_and_cleans_cache(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    old_note = tmp_path / "old.md"
    old_note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [old_note]
    vault.read_frontmatter.return_value = {
        "status": "inbox",
        "collected_at": "2020-01-01T00:00:00",
        "id": "item-1",
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]
    manager._clean_cache = MagicMock(return_value=2)  # type: ignore[method-assign]

    result = manager.run(days=30, clean_cache=True, dry_run=False)

    assert result["archived"] == 1
    assert result["cache_cleaned"] == 2
    manager._archive_note.assert_called_once()
    manager._clean_cache.assert_called_once_with("item-1")


def test_run_skips_non_inbox_items(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "done.md"
    note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "status": "completed",
        "collected_at": "2020-01-01",
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]

    result = manager.run(days=30)

    assert result["scanned"] == 1
    assert result["archived"] == 0
    manager._archive_note.assert_not_called()


def test_run_recent_items_not_archived_by_cutoff(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "recent.md"
    note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "status": "inbox",
        "collected_at": datetime.now().isoformat(),
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]

    result = manager.run(days=30)

    assert result["archived"] == 0
    manager._archive_note.assert_not_called()


def test_run_uses_file_mtime_when_collected_at_missing(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "mtime_old.md"
    note.write_text("x", encoding="utf-8")
    old_ts = (datetime.now() - timedelta(days=45)).timestamp()
    note.touch()
    note.chmod(0o644)
    import os

    os.utime(note, (old_ts, old_ts))

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {"status": "inbox"}

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]

    result = manager.run(days=30)

    assert result["archived"] == 1
    manager._archive_note.assert_called_once()


def test_run_invalid_iso_date_falls_back_to_ymd_parse(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "old2.md"
    note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "status": "inbox",
        "collected_at": "2020-01-01 invalid",
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]

    result = manager.run(days=30)

    assert result["archived"] == 1


def test_run_dry_run_never_calls_archive_or_cache_cleanup(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "old3.md"
    note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "status": "inbox",
        "collected_at": "2020-01-01",
        "id": "x1",
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(return_value=True)  # type: ignore[method-assign]
    manager._clean_cache = MagicMock(return_value=1)  # type: ignore[method-assign]

    result = manager.run(days=30, clean_cache=True, dry_run=True)

    assert result["archived"] == 1
    assert result["cache_cleaned"] == 0
    manager._archive_note.assert_not_called()
    manager._clean_cache.assert_not_called()


def test_run_records_error_when_frontmatter_read_fails(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note = tmp_path / "bad.md"
    note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.side_effect = RuntimeError("read failed")

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    result = manager.run(days=30)

    assert result["archived"] == 0
    assert len(result["errors"]) == 1
    assert "read failed" in result["errors"][0]


def test_run_handles_list_notes_failure_gracefully(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.list_notes.side_effect = RuntimeError("list failed")

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    result = manager.run(days=30)

    assert result["scanned"] == 0
    assert result["archived"] == 0
    assert len(result["errors"]) == 1
    assert "list failed" in result["errors"][0]


def test_run_empty_input_has_zero_counts(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.list_notes.return_value = []

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    result = manager.run(days=30)

    assert result == {
        "threshold_days": 30,
        "scanned": 0,
        "archived": 0,
        "cache_cleaned": 0,
        "errors": [],
    }


def test_run_partial_failures_only_count_successful_archives(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note1 = tmp_path / "one.md"
    note2 = tmp_path / "two.md"
    note1.write_text("x", encoding="utf-8")
    note2.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note1, note2]
    vault.read_frontmatter.side_effect = [
        {"status": "inbox", "collected_at": "2020-01-01", "id": "a"},
        {"status": "inbox", "collected_at": "2020-01-01", "id": "b"},
    ]

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    manager._archive_note = MagicMock(side_effect=[True, False])  # type: ignore[method-assign]
    manager._clean_cache = MagicMock(return_value=1)  # type: ignore[method-assign]

    result = manager.run(days=30, clean_cache=True)

    assert result["archived"] == 1
    assert result["cache_cleaned"] == 1
    assert result["errors"] == []


def test_archive_note_updates_status_and_archived_timestamp(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    archive_root = tmp_path / "Archive" / "Inputs"
    vault.get_path.return_value = archive_root

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    note = tmp_path / "item2.md"
    note.write_text("x", encoding="utf-8")

    ok = manager._archive_note(note, {"id": "id-2"})

    assert ok is True
    args, _kwargs = vault.update_frontmatter.call_args
    assert args[0] == note
    assert args[1]["status"] == "archived"
    assert "archived_at" in args[1]


def test_archive_note_returns_false_when_update_frontmatter_fails(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.get_path.return_value = tmp_path / "Archive" / "Inputs"
    vault.update_frontmatter.side_effect = RuntimeError("write failed")

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    note = tmp_path / "item3.md"
    note.write_text("x", encoding="utf-8")

    assert manager._archive_note(note, {}) is False
    vault.move_note.assert_not_called()


def test_archive_note_returns_false_when_move_fails(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.get_path.return_value = tmp_path / "Archive" / "Inputs"
    vault.move_note.side_effect = RuntimeError("move failed")

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    note = tmp_path / "item4.md"
    note.write_text("x", encoding="utf-8")

    assert manager._archive_note(note, {}) is False


def test_clean_cache_returns_zero_for_missing_item_id(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: MagicMock())

    manager = ArchiveManager()

    assert manager._clean_cache("") == 0
    assert manager._clean_cache(cast(Any, None)) == 0


def test_clean_cache_handles_missing_cache_directory(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: MagicMock())

    manager = ArchiveManager()
    cleaned = manager._clean_cache("any-id")

    assert cleaned == 0


def test_clean_cache_continues_when_unlink_fails(tmp_path, monkeypatch):
    config = _build_config(tmp_path)

    bad_file = MagicMock()
    bad_file.unlink.side_effect = OSError("cannot delete")
    good_file = MagicMock()
    good_file.unlink.return_value = None

    fake_cache_dir = MagicMock()
    fake_cache_dir.exists.return_value = True
    fake_cache_dir.glob.return_value = [bad_file, good_file]

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: MagicMock())
    monkeypatch.setattr("scripts.archive_manager.Path", lambda _p: fake_cache_dir)

    manager = ArchiveManager()
    cleaned = manager._clean_cache("id-99")

    assert cleaned == 1


def test_list_archivable_returns_empty_for_empty_input(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.list_notes.return_value = []

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    items = manager.list_archivable(days=30)

    assert items == []


def test_list_archivable_continues_when_note_read_fails(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    note1 = tmp_path / "good.md"
    note2 = tmp_path / "bad.md"
    note1.write_text("x", encoding="utf-8")
    note2.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [note1, note2]
    vault.read_frontmatter.side_effect = [
        {"status": "inbox", "id": "ok", "title": "Good", "collected_at": "2020-01-01"},
        RuntimeError("broken note"),
    ]

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    items = manager.list_archivable(days=30)

    assert len(items) == 1
    assert items[0]["id"] == "ok"


def test_list_archivable_parses_iso_z_timestamps(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    old_note = tmp_path / "isoz.md"
    old_note.write_text("x", encoding="utf-8")

    vault = MagicMock()
    vault.list_notes.return_value = [old_note]
    vault.read_frontmatter.return_value = {
        "status": "inbox",
        "id": "isoz",
        "title": "ISO Z",
        "collected_at": "2020-01-01T00:00:00Z",
    }

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    items = manager.list_archivable(days=30)

    assert len(items) == 1
    assert items[0]["id"] == "isoz"


def test_main_list_mode_outputs_items_without_archiving(monkeypatch, capsys):
    class FakeManager:
        def __init__(self):
            self.run = MagicMock()

        def list_archivable(self, days):
            assert days == 30
            return [
                {
                    "title": "Old title",
                    "collected_at": "2020-01-01",
                    "id": "x",
                    "path": "p",
                }
            ]

    monkeypatch.setattr(
        "scripts.archive_manager.argparse.ArgumentParser.parse_args",
        lambda _self: SimpleNamespace(days=30, clean_cache=False, list=True, dry_run=False),
    )
    monkeypatch.setattr("scripts.archive_manager.ArchiveManager", FakeManager)

    from scripts.archive_manager import main

    main()
    out = capsys.readouterr().out

    assert "Archivable Items" in out
    assert "Total: 1 items" in out


def test_main_run_mode_prints_archive_results(monkeypatch, capsys):
    class FakeManager:
        def list_archivable(self, days):
            raise AssertionError("list mode should not run")

        def run(self, days, clean_cache, dry_run):
            assert days == 10
            assert clean_cache is True
            assert dry_run is True
            return {"scanned": 5, "archived": 2, "cache_cleaned": 1, "errors": []}

    monkeypatch.setattr(
        "scripts.archive_manager.argparse.ArgumentParser.parse_args",
        lambda _self: SimpleNamespace(days=10, clean_cache=True, list=False, dry_run=True),
    )
    monkeypatch.setattr("scripts.archive_manager.ArchiveManager", FakeManager)

    from scripts.archive_manager import main

    main()
    out = capsys.readouterr().out

    assert "Archive Results" in out
    assert "Scanned:" in out
    assert "Archived:" in out


def test_archive_note_frontmatter_does_not_use_legacy_writing_status_keys(tmp_path, monkeypatch):
    config = _build_config(tmp_path)
    vault = MagicMock()
    vault.get_path.return_value = tmp_path / "Archive" / "Inputs"

    monkeypatch.setattr("scripts.archive_manager.get_config", lambda: config)
    monkeypatch.setattr("scripts.archive_manager.VaultIO", lambda: vault)

    manager = ArchiveManager()
    note = tmp_path / "item5.md"
    note.write_text("x", encoding="utf-8")

    assert manager._archive_note(note, {}) is True
    args, _kwargs = vault.update_frontmatter.call_args
    assert "writing_status" not in args[1]
    assert "archive_date" not in args[1]
