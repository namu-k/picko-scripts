"""Tests for render_media CLI and helpers."""

from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner


class _DummyRenderer:
    def __init__(self):
        self.calls = []

    def render_image(self, **kwargs):
        self.calls.append(kwargs)
        return "<html>ok</html>"


def _dummy_input(*, overlay_text="짧은 텍스트", channels=None):
    return SimpleNamespace(
        id="mm_test_001",
        account="testaccount",
        channels=channels or ["linkedin"],
        concept="테스트 주제",
        overlay_text=overlay_text,
    )


class TestRenderMediaCLI:
    def test_cli_help_shows_commands(self):
        from scripts.render_media import cli

        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "render" in result.output
        assert "status" in result.output
        assert "review" in result.output

    def test_render_help_shows_options(self):
        from scripts.render_media import cli

        result = CliRunner().invoke(cli, ["render", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--output-png" in result.output
        assert "--channel" in result.output

    def test_status_command_uses_vault_option(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        seen = {}

        def mock_status(vault_path=None):
            seen["vault"] = vault_path
            return "ok"

        monkeypatch.setattr("scripts.render_media.get_status", mock_status)

        result = CliRunner().invoke(cli, ["--vault", str(tmp_path), "status"])
        assert result.exit_code == 0
        assert seen["vault"] == tmp_path
        assert "ok" in result.output

    def test_review_no_items_for_proposals(self, monkeypatch):
        from scripts.render_media import cli

        monkeypatch.setattr("scripts.render_media.get_pending_proposals", lambda vault_path=None: [])

        result = CliRunner().invoke(cli, ["review"])

        assert result.exit_code == 0
        assert "없음" in result.output

    def test_review_no_items_for_finals(self, monkeypatch):
        from scripts.render_media import cli

        monkeypatch.setattr("scripts.render_media.get_pending_finals", lambda vault_path=None: [])

        result = CliRunner().invoke(cli, ["review", "--finals"])

        assert result.exit_code == 0
        assert "없음" in result.output

    def test_review_filters_by_id_and_calls_review_item(self, monkeypatch):
        from scripts.render_media import cli

        items = [
            {"id": "mm_1", "status": "proposed"},
            {"id": "mm_2", "status": "pending_review"},
        ]
        reviewed = []

        monkeypatch.setattr("scripts.render_media.get_pending_proposals", lambda vault_path=None: items)
        monkeypatch.setattr("scripts.render_media.review_item", lambda item: reviewed.append(item["id"]))

        result = CliRunner().invoke(cli, ["review", "--id", "mm_2"])

        assert result.exit_code == 0
        assert reviewed == ["mm_2"]

    def test_review_filter_id_not_found(self, monkeypatch):
        from scripts.render_media import cli

        monkeypatch.setattr(
            "scripts.render_media.get_pending_proposals",
            lambda vault_path=None: [{"id": "x"}],
        )

        result = CliRunner().invoke(cli, ["review", "--id", "missing"])

        assert result.exit_code == 0
        assert "해당하는" in result.output

    def test_render_writes_html_and_uses_quote_template(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        dummy_renderer = _DummyRenderer()
        output_path = tmp_path / "out.html"
        input_file = tmp_path / "input.md"
        input_file.write_text("x", encoding="utf-8")

        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: _dummy_input(overlay_text="짧음"),
        )
        monkeypatch.setattr("picko.templates.ImageRenderer", lambda: dummy_renderer)

        result = CliRunner().invoke(cli, ["render", "--input", str(input_file), "--output", str(output_path)])

        assert result.exit_code == 0
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "<html>ok</html>"
        assert dummy_renderer.calls[0]["template"] == "quote"

    def test_render_uses_card_template_for_long_overlay(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        dummy_renderer = _DummyRenderer()
        input_file = tmp_path / "input.md"
        input_file.write_text("x", encoding="utf-8")

        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: _dummy_input(overlay_text="x" * 120, channels=["twitter", "linkedin"]),
        )
        monkeypatch.setattr("picko.templates.ImageRenderer", lambda: dummy_renderer)

        result = CliRunner().invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--layout",
                "minimal_light",
                "--theme",
                "socialbuilders",
                "--override",
                "colors.primary=#ff0000",
            ],
        )

        assert result.exit_code == 0
        call = dummy_renderer.calls[0]
        assert call["template"] == "card"
        assert call["layout_preset"] == "minimal_light"
        assert call["layout_theme"] == "socialbuilders"
        assert call["layout_overrides"] == ["colors.primary=#ff0000"]
        assert "출력 생략" in result.output

    def test_render_png_pipeline(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        input_file = tmp_path / "input.md"
        png_path = tmp_path / "out.png"
        input_file.write_text("x", encoding="utf-8")

        called = {}

        monkeypatch.setattr("picko.multimedia_io.parse_multimedia_input", lambda _: _dummy_input())
        monkeypatch.setattr("picko.templates.ImageRenderer", lambda: _DummyRenderer())
        monkeypatch.setattr(
            "picko.html_renderer.get_dimensions_for_channel",
            lambda channel: (1200, 630),
        )

        def _render_png_sync(html, output_path, width, height):
            called.update({"html": html, "output": output_path, "width": width, "height": height})

        monkeypatch.setattr("picko.html_renderer.render_html_to_png_sync", _render_png_sync)

        result = CliRunner().invoke(
            cli,
            [
                "render",
                "--input",
                str(input_file),
                "--output-png",
                str(png_path),
                "--channel",
                "twitter",
            ],
        )

        assert result.exit_code == 0
        assert called["output"] == png_path
        assert called["width"] == 1200
        assert called["height"] == 630
        assert "PNG 렌더링 완료" in result.output

    def test_render_error_file_not_found(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        input_file = tmp_path / "missing.md"
        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: (_ for _ in ()).throw(FileNotFoundError()),
        )

        result = CliRunner().invoke(cli, ["render", "--input", str(input_file)])

        assert result.exit_code == 1
        assert "파일을 찾을 수 없습니다" in result.output

    def test_render_error_permission(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        input_file = tmp_path / "input.md"
        input_file.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: (_ for _ in ()).throw(PermissionError()),
        )

        result = CliRunner().invoke(cli, ["render", "--input", str(input_file)])

        assert result.exit_code == 1
        assert "읽기 권한" in result.output

    def test_render_error_unicode_decode(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        input_file = tmp_path / "input.md"
        input_file.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")),
        )

        result = CliRunner().invoke(cli, ["render", "--input", str(input_file)])

        assert result.exit_code == 1
        assert "인코딩 오류" in result.output

    def test_render_error_value(self, tmp_path: Path, monkeypatch):
        from scripts.render_media import cli

        input_file = tmp_path / "input.md"
        input_file.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "picko.multimedia_io.parse_multimedia_input",
            lambda _: (_ for _ in ()).throw(ValueError("invalid template")),
        )

        result = CliRunner().invoke(cli, ["render", "--input", str(input_file)])

        assert result.exit_code == 1
        assert "invalid template" in result.output


class TestRenderMediaHelpers:
    def test_get_status_empty(self, tmp_path: Path):
        from scripts.render_media import get_status

        output = get_status(tmp_path)

        assert "대기 중인 항목 없음" in output

    def test_get_status_collects_multimedia_and_rendered_items(self, tmp_path: Path):
        from scripts.render_media import get_status

        mm_dir = tmp_path / "Inbox" / "Multimedia"
        img_dir = tmp_path / "Assets" / "Images" / "socialbuilders"
        mm_dir.mkdir(parents=True)
        img_dir.mkdir(parents=True)

        (mm_dir / "mm_ok.md").write_text(
            "---\nid: mm_ok\nstatus: proposed\nchannels: [linkedin, twitter]\n---\nbody",
            encoding="utf-8",
        )
        (mm_dir / "mm_bad.md").write_text("---\n: bad\n", encoding="utf-8")
        (img_dir / "meta_1.md").write_text(
            "---\nid: mm_img\nstatus: rendered\nchannel: instagram\n---\n",
            encoding="utf-8",
        )

        output = get_status(tmp_path)

        assert "mm_ok" in output
        assert "mm_img" in output
        assert "총 2개 항목" in output

    def test_get_pending_proposals_filters_status(self, tmp_path: Path):
        from scripts.render_media import get_pending_proposals

        mm_dir = tmp_path / "Inbox" / "Multimedia"
        mm_dir.mkdir(parents=True)

        (mm_dir / "a.md").write_text(
            "---\nid: a\nstatus: proposed\naccount: acc\nchannels: [linkedin]\ncontent_types: [image]\n---\n",
            encoding="utf-8",
        )
        (mm_dir / "b.md").write_text("---\nid: b\nstatus: draft\n---\n", encoding="utf-8")
        (mm_dir / "c.md").write_text(
            "---\nid: c\nstatus: pending_review\naccount: acc\nchannels: [twitter]\n---\n",
            encoding="utf-8",
        )

        items = get_pending_proposals(tmp_path)

        assert [i["id"] for i in items] == ["a", "c"]

    def test_get_pending_finals_finds_image_or_not_found(self, tmp_path: Path):
        from scripts.render_media import get_pending_finals

        img_dir = tmp_path / "Assets" / "Images" / "socialbuilders"
        img_dir.mkdir(parents=True)

        (img_dir / "meta_yes.md").write_text(
            "---\nid: item_yes\nstatus: rendered\nchannel: instagram\naccount: socialbuilders\n---\n",
            encoding="utf-8",
        )
        (img_dir / "img_instagram_item_yes.png").write_bytes(b"png")
        (img_dir / "meta_no.md").write_text(
            "---\nid: item_no\nstatus: pending_final_review\nchannel: twitter\naccount: socialbuilders\n---\n",
            encoding="utf-8",
        )

        items = get_pending_finals(tmp_path)
        by_id = {item["id"]: item for item in items}

        assert "item_yes" in by_id
        assert "img_instagram_item_yes.png" in by_id["item_yes"]["image_path"]
        assert by_id["item_no"]["image_path"] == "Not found"

    def test_review_item_actions(self, monkeypatch, capsys):
        from scripts.render_media import review_item

        actions = {
            "A": "승인됨",
            "E": "수정 모드",
            "R": "거절됨",
            "S": "건너뜀",
        }

        for choice, expected in actions.items():
            monkeypatch.setattr("click.prompt", lambda *args, **kwargs: choice)
            review_item({"id": "item1", "status": "proposed"})
            out = capsys.readouterr().out
            assert expected in out
