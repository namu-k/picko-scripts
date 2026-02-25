"""Tests for render_media CLI."""

from pathlib import Path

from click.testing import CliRunner


class TestRenderMediaCLI:
    """Test render_media CLI commands."""

    def test_cli_help(self):
        """CLI shows help."""
        from scripts.render_media import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "render" in result.output.lower() or "media" in result.output.lower()

    def test_status_command(self, tmp_path: Path, monkeypatch):
        """Status command shows pipeline status."""
        from scripts.render_media import cli

        runner = CliRunner()

        # Mock the status function
        def mock_status(vault_path=None):
            return "📊 이미지 렌더링 상태\n─────────\n대기 중: 0개"

        monkeypatch.setattr("scripts.render_media.get_status", mock_status)

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "이미지" in result.output or "렌더링" in result.output

    def test_review_no_items(self, tmp_path: Path, monkeypatch):
        """Review command with no pending items."""
        from scripts.render_media import cli

        runner = CliRunner()

        def mock_get_pending(vault_path=None):
            return []

        monkeypatch.setattr("scripts.render_media.get_pending_proposals", mock_get_pending)

        result = runner.invoke(cli, ["review"])
        assert "검토" in result.output or "대기" in result.output or "없음" in result.output

    def test_render_command_loads_input(self, tmp_path: Path):
        """Render command loads and parses input file."""
        from scripts.render_media import cli

        # Create a test input file
        input_file = tmp_path / "mm_test.md"
        input_file.write_text(
            """---
id: mm_test_001
account: testaccount
source_type: standalone
channels: [linkedin]
content_types: [image]
created: 2026-02-24
status: draft
---

## 주제/컨셉
테스트 주제

## 포함할 텍스트
테스트 텍스트
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--input", str(input_file)])

        # Should successfully load the input
        assert result.exit_code == 0
        assert "mm_test_001" in result.output or "테스트" in result.output
