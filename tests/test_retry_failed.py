import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.retry_failed import RetryManager, main


def _build_config(tmp_path: Path):
    cfg = SimpleNamespace()
    cfg.logging = SimpleNamespace(dir=str(tmp_path / "logs"))
    cfg.vault = SimpleNamespace(inbox="Inbox/Inputs")
    return cfg


def _build_manager(tmp_path, monkeypatch, max_attempts=3):
    config = _build_config(tmp_path)
    vault = MagicMock()
    llm = MagicMock()
    embedder = MagicMock()

    monkeypatch.setattr("scripts.retry_failed.get_config", lambda: config)
    monkeypatch.setattr("scripts.retry_failed.VaultIO", lambda: vault)
    monkeypatch.setattr("scripts.retry_failed.get_llm_client", lambda: llm)
    monkeypatch.setattr("scripts.retry_failed.get_embedding_manager", lambda: embedder)

    return RetryManager(max_attempts=max_attempts), vault, llm, embedder


def test_init_uses_provided_max_attempts(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch, max_attempts=5)

    assert manager.max_attempts == 5


def test_run_no_failed_items_returns_early(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    monkeypatch.setattr(manager, "_load_failed_items", lambda date, stage: [])
    save_mock = MagicMock()
    monkeypatch.setattr(manager, "_save_retry_log", save_mock)

    result = manager.run(date="2026-02-01")

    assert result["failed_found"] == 0
    assert result["retried"] == 0
    save_mock.assert_not_called()


def test_run_uses_current_date_when_not_provided(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    monkeypatch.setattr(manager, "_load_failed_items", lambda date, stage: [])

    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 2, 27, 9, 10, 11)

    monkeypatch.setattr("scripts.retry_failed.datetime", FakeDateTime)
    result = manager.run()

    assert result["date"] == "2026-02-27"


def test_run_skips_items_at_max_attempts_threshold(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    monkeypatch.setattr(
        manager,
        "_load_failed_items",
        lambda date, stage: [{"id": "x", "stage": "nlp", "retry_count": 3}],
    )

    result = manager.run(date="2026-02-01", dry_run=True)

    assert result["failed_found"] == 1
    assert result["retried"] == 0
    assert result["still_failed"] == 1


def test_run_counts_retry_success_failure_and_exceptions(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    items = [
        {"id": "ok", "stage": "nlp", "retry_count": 0},
        {"id": "no", "stage": "nlp", "retry_count": 0},
        {"id": "err", "stage": "nlp", "retry_count": 0},
    ]
    monkeypatch.setattr(manager, "_load_failed_items", lambda date, stage: items)

    def fake_retry(item, dry_run):
        if item["id"] == "ok":
            return True
        if item["id"] == "no":
            return False
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "_retry_item", fake_retry)

    result = manager.run(date="2026-02-01", dry_run=True)

    assert result["retried"] == 3
    assert result["succeeded"] == 1
    assert result["still_failed"] == 2
    assert result["errors"] == ["boom"]


def test_run_saves_retry_log_when_not_dry_run(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    monkeypatch.setattr(manager, "_load_failed_items", lambda date, stage: [{"id": "x", "stage": "nlp"}])
    monkeypatch.setattr(manager, "_retry_item", lambda item, dry_run: True)
    save_mock = MagicMock()
    monkeypatch.setattr(manager, "_save_retry_log", save_mock)

    manager.run(date="2026-02-01", dry_run=False)

    save_mock.assert_called_once()


def test_run_does_not_save_retry_log_when_dry_run(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    monkeypatch.setattr(manager, "_load_failed_items", lambda date, stage: [{"id": "x", "stage": "nlp"}])
    monkeypatch.setattr(manager, "_retry_item", lambda item, dry_run: True)
    save_mock = MagicMock()
    monkeypatch.setattr(manager, "_save_retry_log", save_mock)

    manager.run(date="2026-02-01", dry_run=True)

    save_mock.assert_not_called()


def test_run_captures_load_failed_items_exception(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    def raise_load(date, stage):
        raise RuntimeError("load failed")

    monkeypatch.setattr(manager, "_load_failed_items", raise_load)
    result = manager.run(date="2026-02-01")

    assert result["errors"] == ["load failed"]
    assert result["retried"] == 0


@pytest.mark.parametrize("stage", ["fetch", "nlp", "embed", "score", "export"])
def test_load_failed_items_from_inbox_filters_each_stage(tmp_path, monkeypatch, stage):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    note = tmp_path / "failed.md"
    note.write_text("x", encoding="utf-8")
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "id": "n1",
        "status": "failed",
        "failed_stage": stage,
        "error_message": "err",
        "retry_count": 1,
    }

    items = manager._load_failed_items("2026-02-01", stage=stage)

    assert len(items) == 1
    assert items[0]["id"] == "n1"
    assert items[0]["stage"] == stage


def test_load_failed_items_from_inbox_stage_mismatch_returns_empty(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    note = tmp_path / "failed.md"
    note.write_text("x", encoding="utf-8")
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "id": "n1",
        "status": "failed",
        "failed_stage": "nlp",
        "retry_count": 1,
    }

    items = manager._load_failed_items("2026-02-01", stage="embed")

    assert items == []


def test_load_failed_items_from_inbox_ignores_non_failed_status(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    note = tmp_path / "ok.md"
    note.write_text("x", encoding="utf-8")
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {"id": "n1", "status": "inbox"}

    assert manager._load_failed_items("2026-02-01") == []


def test_load_failed_items_from_inbox_ignores_frontmatter_read_errors(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    note = tmp_path / "bad.md"
    note.write_text("x", encoding="utf-8")
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.side_effect = RuntimeError("bad read")

    assert manager._load_failed_items("2026-02-01") == []


def test_load_failed_items_from_inbox_defaults_unknown_stage_and_retry_count(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    note = tmp_path / "failed.md"
    note.write_text("x", encoding="utf-8")
    vault.list_notes.return_value = [note]
    vault.read_frontmatter.return_value = {
        "id": "n1",
        "status": "failed",
    }

    items = manager._load_failed_items("2026-02-01")

    assert items[0]["stage"] == "unknown"
    assert items[0]["retry_count"] == 0


def test_load_failed_items_from_logs_includes_only_failed_status(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    day_dir = Path(manager.logs_dir) / "2026-02-01"
    day_dir.mkdir(parents=True)
    (day_dir / "ok.json").write_text(json.dumps({"id": "a", "status": "ok"}), encoding="utf-8")
    (day_dir / "failed.json").write_text(
        json.dumps({"id": "b", "status": "failed", "stage": "nlp", "url": "u", "error": "e"}),
        encoding="utf-8",
    )

    items = manager._load_failed_items("2026-02-01")

    assert len(items) == 1
    assert items[0]["id"] == "b"


def test_load_failed_items_from_logs_filters_by_stage(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    day_dir = Path(manager.logs_dir) / "2026-02-01"
    day_dir.mkdir(parents=True)
    (day_dir / "f1.json").write_text(
        json.dumps({"id": "a", "status": "failed", "stage": "fetch", "url": "u", "error": "e"}),
        encoding="utf-8",
    )
    (day_dir / "f2.json").write_text(
        json.dumps({"id": "b", "status": "failed", "stage": "nlp", "url": "u", "error": "e"}),
        encoding="utf-8",
    )

    items = manager._load_failed_items("2026-02-01", stage="fetch")

    assert len(items) == 1
    assert items[0]["id"] == "a"
    assert items[0]["stage"] == "fetch"


def test_load_failed_items_from_logs_ignores_invalid_json(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    day_dir = Path(manager.logs_dir) / "2026-02-01"
    day_dir.mkdir(parents=True)
    (day_dir / "broken.json").write_text("{", encoding="utf-8")

    assert manager._load_failed_items("2026-02-01") == []


def test_load_failed_items_from_logs_defaults_retry_count_and_data(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    day_dir = Path(manager.logs_dir) / "2026-02-01"
    day_dir.mkdir(parents=True)
    (day_dir / "failed.json").write_text(
        json.dumps({"id": "b", "status": "failed", "stage": "nlp", "url": "u", "error": "e"}),
        encoding="utf-8",
    )

    items = manager._load_failed_items("2026-02-01")

    assert items[0]["retry_count"] == 0
    assert items[0]["data"] == {}


def test_retry_item_dry_run_returns_true_without_dispatch(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    retry_fetch_mock = MagicMock(return_value=False)
    monkeypatch.setattr(manager, "_retry_fetch", retry_fetch_mock)

    assert manager._retry_item({"id": "1", "stage": "fetch"}, dry_run=True) is True
    retry_fetch_mock.assert_not_called()


@pytest.mark.parametrize(
    ("stage", "method_name"),
    [
        ("fetch", "_retry_fetch"),
        ("nlp", "_retry_nlp"),
        ("embed", "_retry_embed"),
        ("score", "_retry_score"),
        ("export", "_retry_export"),
    ],
)
def test_retry_item_dispatches_to_each_stage_method(tmp_path, monkeypatch, stage, method_name):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)
    handler = MagicMock(return_value=True)
    monkeypatch.setattr(manager, method_name, handler)

    assert manager._retry_item({"id": "1", "stage": stage}, dry_run=False) is True
    handler.assert_called_once()


def test_retry_item_unknown_stage_returns_false(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_item({"id": "1", "stage": "unknown"}, dry_run=False) is False


def test_retry_fetch_returns_false_without_url(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_fetch({"id": "1"}) is False


def test_retry_fetch_success_updates_frontmatter_with_truncated_text(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    response = MagicMock()
    response.text = "<html><body>ok</body></html>"
    response.raise_for_status.return_value = None

    soup = MagicMock()
    soup.get_text.return_value = "x" * 4000
    soup.return_value = [MagicMock(), MagicMock()]

    with (
        patch("httpx.get", return_value=response),
        patch("bs4.BeautifulSoup", return_value=soup),
    ):
        ok = manager._retry_fetch({"id": "1", "url": "https://example.com", "path": "Inbox/Inputs/a.md"})

    assert ok is True
    vault.update_frontmatter.assert_called_once()
    _, updates = vault.update_frontmatter.call_args.args
    assert updates["status"] == "inbox"
    assert len(updates["text"]) == 3000


def test_retry_fetch_success_without_path_returns_true(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    response = MagicMock()
    response.text = "<html><body>ok</body></html>"
    response.raise_for_status.return_value = None

    soup = MagicMock()
    soup.get_text.return_value = "content"
    soup.return_value = []

    with (
        patch("httpx.get", return_value=response),
        patch("bs4.BeautifulSoup", return_value=soup),
    ):
        ok = manager._retry_fetch({"id": "1", "url": "https://example.com"})

    assert ok is True
    vault.update_frontmatter.assert_not_called()


def test_retry_fetch_handles_http_client_failure(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    with patch("httpx.get", side_effect=RuntimeError("request fail")):
        assert manager._retry_fetch({"id": "1", "url": "https://example.com"}) is False


def test_retry_nlp_returns_false_without_path(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_nlp({"id": "1"}) is False


def test_retry_nlp_returns_false_when_text_missing(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = ({}, "body")

    assert manager._retry_nlp({"path": "Inbox/Inputs/test.md"}) is False


def test_retry_nlp_updates_note_on_success(tmp_path, monkeypatch):
    manager, vault, llm, _ = _build_manager(tmp_path, monkeypatch)
    llm.summarize.return_value = "summary"
    llm.generate_tags.return_value = ["a", "b"]
    vault.read_note.return_value = ({"text": "sample text"}, "body")

    item = {"path": "Inbox/Inputs/test.md"}
    assert manager._retry_nlp(item) is True

    vault.update_frontmatter.assert_called_once()
    _, updates = vault.update_frontmatter.call_args.args
    assert updates["status"] == "inbox"
    assert updates["summary"] == "summary"
    assert updates["failed_stage"] is None
    assert updates["error_message"] is None


def test_retry_nlp_handles_llm_failure(tmp_path, monkeypatch):
    manager, vault, llm, _ = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = ({"text": "sample text"}, "body")
    llm.summarize.side_effect = RuntimeError("llm failed")

    assert manager._retry_nlp({"path": "Inbox/Inputs/test.md"}) is False


def test_retry_embed_returns_false_without_path(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_embed({"id": "1"}) is False


def test_retry_embed_updates_frontmatter_on_success(tmp_path, monkeypatch):
    manager, vault, _, embedder = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = ({"title": "T", "summary": "S"}, "body")

    assert manager._retry_embed({"path": "Inbox/Inputs/test.md"}) is True
    embedder.embed.assert_called_once_with("T S")
    _, updates = vault.update_frontmatter.call_args.args
    assert updates["embedded"] is True


def test_retry_embed_handles_embedder_failure(tmp_path, monkeypatch):
    manager, vault, _, embedder = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = ({"title": "T", "summary": "S"}, "body")
    embedder.embed.side_effect = RuntimeError("embed failed")

    assert manager._retry_embed({"path": "Inbox/Inputs/test.md"}) is False


def test_retry_score_returns_false_without_path(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_score({"id": "1"}) is False


def test_retry_score_updates_frontmatter_on_success(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = (
        {"title": "Title", "summary": "Summary", "tags": ["a"]},
        "body",
    )

    score_obj = MagicMock()
    score_obj.to_dict.return_value = {"total": 0.9}
    scorer_instance = MagicMock()
    scorer_instance.score.return_value = score_obj

    with patch("picko.scoring.ContentScorer", return_value=scorer_instance):
        ok = manager._retry_score({"path": "Inbox/Inputs/test.md"})

    assert ok is True
    scorer_instance.score.assert_called_once()
    _, updates = vault.update_frontmatter.call_args.args
    assert updates["score"] == {"total": 0.9}


def test_retry_score_handles_scorer_failure(tmp_path, monkeypatch):
    manager, vault, _, _ = _build_manager(tmp_path, monkeypatch)
    vault.read_note.return_value = (
        {"title": "Title", "summary": "Summary", "tags": ["a"]},
        "body",
    )

    scorer_instance = MagicMock()
    scorer_instance.score.side_effect = RuntimeError("score failed")

    with patch("picko.scoring.ContentScorer", return_value=scorer_instance):
        assert manager._retry_score({"path": "Inbox/Inputs/test.md"}) is False


def test_retry_export_returns_false(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    assert manager._retry_export({"id": "1"}) is False


def test_save_retry_log_creates_file_with_expected_payload(tmp_path, monkeypatch):
    manager, _, _, _ = _build_manager(tmp_path, monkeypatch)

    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 2, 27, 8, 9, 10)

    monkeypatch.setattr("scripts.retry_failed.datetime", FakeDateTime)
    payload = {"date": "2026-02-27", "retried": 2}

    manager._save_retry_log("2026-02-27", payload)

    out = Path(manager.logs_dir) / "2026-02-27" / "retry_080910.json"
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == payload


def test_main_uses_parsed_args_and_prints_summary(tmp_path, monkeypatch, capsys):
    args = SimpleNamespace(date="2026-02-01", stage="nlp", max_attempts=4, dry_run=True)

    parser = MagicMock()
    parser.parse_args.return_value = args
    monkeypatch.setattr("scripts.retry_failed.argparse.ArgumentParser", MagicMock(return_value=parser))

    manager_instance = MagicMock()
    manager_instance.run.return_value = {
        "date": "2026-02-01",
        "failed_found": 2,
        "retried": 2,
        "succeeded": 1,
        "still_failed": 1,
        "errors": ["x"],
    }
    manager_cls = MagicMock(return_value=manager_instance)
    monkeypatch.setattr("scripts.retry_failed.RetryManager", manager_cls)

    main()

    manager_cls.assert_called_once_with(max_attempts=4)
    manager_instance.run.assert_called_once_with(date="2026-02-01", stage="nlp", dry_run=True)
    output = capsys.readouterr().out
    assert "Retry Results for 2026-02-01" in output
    assert "Errors:" in output


def test_retry_manager_init_raises_on_config_loading_failure(monkeypatch):
    monkeypatch.setattr(
        "scripts.retry_failed.get_config",
        MagicMock(side_effect=RuntimeError("cfg fail")),
    )

    with pytest.raises(RuntimeError, match="cfg fail"):
        RetryManager()
