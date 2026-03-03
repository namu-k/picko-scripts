import argparse
from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest

import scripts.scheduler as scheduler
from scripts.scheduler import (
    _parse_hour_minute,
    _venv_python_for_unix,
    _workflow_abs,
    build_parser,
    detect_project_root,
    format_cron_time,
    main,
    render_cron,
    render_env_reminder,
    render_launchd,
    render_systemd,
    render_windows,
)


def _plan_args(tmp_path, **overrides):
    defaults = {
        "workflow": str(tmp_path / "config" / "workflows" / "daily.yml"),
        "time": "08:00",
        "cron": False,
        "systemd": False,
        "launchd": False,
        "windows": False,
        "include_env": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_time_parsing_0800_to_cron_expression():
    assert format_cron_time("08:00") == "0 8 * * *"


def test_format_cron_time_accepts_single_digit_hour():
    assert format_cron_time("8:05") == "5 8 * * *"


def test_format_cron_time_rejects_invalid_delimiter():
    with pytest.raises(ValueError, match="Invalid time format"):
        format_cron_time("08-00")


def test_format_cron_time_rejects_non_numeric_value():
    with pytest.raises(ValueError, match="Invalid time format"):
        format_cron_time("ab:00")


def test_format_cron_time_rejects_hour_out_of_range():
    with pytest.raises(ValueError, match="Invalid time value"):
        format_cron_time("24:00")


def test_format_cron_time_rejects_minute_out_of_range():
    with pytest.raises(ValueError, match="Invalid time value"):
        format_cron_time("23:60")


def test_parse_hour_minute_returns_expected_tuple():
    assert _parse_hour_minute("09:30") == (9, 30)


def test_cron_output_format_valid(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "config" / "workflows" / "daily.yml"

    cron_line = render_cron(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    assert cron_line.startswith("0 8 * * * ")
    assert " -m scripts.run_workflow" in cron_line


def test_render_cron_uses_venv_python_when_available(tmp_path):
    project_root = tmp_path / "my project"
    (project_root / ".venv" / "bin").mkdir(parents=True)
    (project_root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    workflow_path = project_root / "wf.yml"

    cron_line = render_cron(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    assert ".venv" in cron_line
    assert "bin" in cron_line
    assert " -m scripts.run_workflow" in cron_line


def test_systemd_output_includes_service_and_timer_units(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "config" / "workflows" / "daily.yml"

    output = render_systemd(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    assert "[Unit]" in output
    assert "[Service]" in output
    assert "[Timer]" in output
    assert "OnCalendar=*-*-* 08:00:00" in output


def test_launchd_output_is_valid_xml(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "config" / "workflows" / "daily.yml"

    plist_xml = render_launchd(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    root = ElementTree.fromstring(plist_xml)
    assert root.tag == "plist"


def test_render_launchd_includes_hour_and_minute_values(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "daily.yml"

    plist_xml = render_launchd(workflow_path=workflow_path, project_root=project_root, run_time="21:07")

    assert "<integer>21</integer>" in plist_xml
    assert "<integer>7</integer>" in plist_xml


def test_render_windows_includes_expected_powershell_command(tmp_path):
    output = render_windows(project_root=tmp_path, run_time="06:40")

    assert "powershell -ExecutionPolicy Bypass -File" in output
    assert '-Hour "6" -Minute "40"' in output


def test_workflow_path_is_included_in_output(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "config" / "workflows" / "daily.yml"

    cron_line = render_cron(workflow_path=workflow_path, project_root=project_root, run_time="08:00")
    systemd_text = render_systemd(workflow_path=workflow_path, project_root=project_root, run_time="08:00")
    launchd_xml = render_launchd(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    workflow_literal = str(workflow_path)
    assert workflow_literal in cron_line
    assert workflow_literal in systemd_text
    assert workflow_literal in launchd_xml


def test_env_reminder_without_setup_lists_required_vars_inline():
    output = render_env_reminder(include_setup=False)

    assert output.startswith("Required env vars")
    assert "OPENAI_API_KEY" in output


def test_env_reminder_with_windows_setup_uses_setx():
    output = render_env_reminder(include_setup=True, windows=True)

    assert "setx OPENAI_API_KEY" in output
    assert "setx OPENROUTER_API_KEY" in output


def test_env_reminder_with_unix_setup_uses_export():
    output = render_env_reminder(include_setup=True, windows=False)

    assert "export OPENAI_API_KEY" in output
    assert "export ANTHROPIC_API_KEY" in output


def test_venv_python_for_unix_returns_python_when_missing(tmp_path):
    assert _venv_python_for_unix(tmp_path) == "python"


def test_venv_python_for_unix_returns_quoted_path_when_present(tmp_path):
    project_root = tmp_path / "my project"
    venv_python = project_root / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")

    result = _venv_python_for_unix(project_root)

    assert ".venv" in result
    assert "bin" in result
    assert "python" in result


def test_workflow_abs_resolves_relative_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative_path = Path("config/workflows/daily.yml")

    resolved = _workflow_abs(relative_path)

    assert resolved.is_absolute()
    assert str(resolved).endswith(str(Path("config") / "workflows" / "daily.yml"))


def test_detect_project_root_prefers_project_root_constant(tmp_path, monkeypatch):
    configured_root = tmp_path / "configured"
    configured_root.mkdir()
    monkeypatch.setattr(scheduler, "PROJECT_ROOT", configured_root)

    resolved = detect_project_root(start=tmp_path / "other")

    assert resolved == configured_root.resolve()


def test_detect_project_root_finds_parent_git_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "PROJECT_ROOT", tmp_path / "does-not-exist")
    repo_root = tmp_path / "repo"
    nested = repo_root / "a" / "b" / "c"
    (repo_root / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)

    resolved = detect_project_root(start=nested)

    assert resolved == repo_root.resolve()


def test_detect_project_root_raises_when_no_git_found(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "PROJECT_ROOT", tmp_path / "does-not-exist")

    with pytest.raises(FileNotFoundError, match="Could not determine project root"):
        detect_project_root(start=tmp_path)


def test_print_section_writes_formatted_block(capsys):
    scheduler._print_section("CRON", "line")

    captured = capsys.readouterr()
    assert captured.out == "[CRON]\nline\n\n"


def test_plan_with_no_explicit_output_prints_all_sections(tmp_path, monkeypatch):
    args = _plan_args(tmp_path)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    section_mock = Mock()
    monkeypatch.setattr(scheduler, "_print_section", section_mock)

    result = scheduler._plan(args)

    assert result == 0
    assert section_mock.call_count == 5


def test_plan_with_cron_flag_prints_cron_and_env(tmp_path, monkeypatch):
    args = _plan_args(tmp_path, cron=True, include_env=True)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    monkeypatch.setattr(scheduler, "render_cron", lambda **_: "cron-text")
    monkeypatch.setattr(scheduler, "render_env_reminder", lambda **_: "env-text")

    print_mock = Mock()
    monkeypatch.setattr("builtins.print", print_mock)

    result = scheduler._plan(args)

    assert result == 0
    print_mock.assert_any_call("cron-text")
    print_mock.assert_any_call("env-text")


def test_plan_with_systemd_flag_prints_systemd_and_env(tmp_path, monkeypatch):
    args = _plan_args(tmp_path, systemd=True)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    monkeypatch.setattr(scheduler, "render_systemd", lambda **_: "systemd-text")
    monkeypatch.setattr(scheduler, "render_env_reminder", lambda **_: "env-text")

    print_mock = Mock()
    monkeypatch.setattr("builtins.print", print_mock)

    scheduler._plan(args)

    print_mock.assert_any_call("systemd-text")
    print_mock.assert_any_call("env-text")


def test_plan_with_launchd_flag_prints_launchd_and_env(tmp_path, monkeypatch):
    args = _plan_args(tmp_path, launchd=True)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    monkeypatch.setattr(scheduler, "render_launchd", lambda **_: "launchd-text")
    monkeypatch.setattr(scheduler, "render_env_reminder", lambda **_: "env-text")

    print_mock = Mock()
    monkeypatch.setattr("builtins.print", print_mock)

    scheduler._plan(args)

    print_mock.assert_any_call("launchd-text")
    print_mock.assert_any_call("env-text")


def test_plan_with_windows_flag_prints_windows_and_env(tmp_path, monkeypatch):
    args = _plan_args(tmp_path, windows=True)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    monkeypatch.setattr(scheduler, "render_windows", lambda **_: "windows-text")
    monkeypatch.setattr(scheduler, "render_env_reminder", lambda **_: "env-text")

    print_mock = Mock()
    monkeypatch.setattr("builtins.print", print_mock)

    scheduler._plan(args)

    print_mock.assert_any_call("windows-text")
    print_mock.assert_any_call("env-text")


def test_plan_resolves_relative_workflow_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = _plan_args(tmp_path, workflow="config/workflows/daily.yml", cron=True)
    monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
    monkeypatch.setattr(scheduler, "render_env_reminder", lambda **_: "env-text")

    captured = {}

    def fake_render_cron(**kwargs):
        captured["workflow_path"] = kwargs["workflow_path"]
        return "cron-text"

    monkeypatch.setattr(scheduler, "render_cron", fake_render_cron)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    scheduler._plan(args)

    assert captured["workflow_path"].is_absolute()


def test_build_parser_requires_command():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_parser_plan_sets_expected_defaults(tmp_path):
    parser = build_parser()
    args = parser.parse_args(["plan", "--workflow", str(tmp_path / "wf.yml")])

    assert args.time == "08:00"
    assert args.cron is False
    assert args.systemd is False
    assert args.launchd is False
    assert args.windows is False
    assert callable(args.func)


def test_main_returns_value_from_command_function(tmp_path):
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(scheduler, "detect_project_root", lambda: tmp_path)
        result = main(["plan", "--workflow", str(tmp_path / "wf.yml"), "--cron"])
    assert result == 0


def test_main_raises_system_exit_when_value_error_occurs(monkeypatch):
    parser = build_parser()

    class FakeArgs:
        @staticmethod
        def func(_):
            raise ValueError("bad input")

    monkeypatch.setattr(parser, "parse_args", lambda argv: FakeArgs())
    monkeypatch.setattr(scheduler, "build_parser", lambda: parser)

    with pytest.raises(SystemExit):
        main(["plan"])


def test_main_returns_one_when_project_root_not_found(monkeypatch, capsys):
    parser = build_parser()

    class FakeArgs:
        @staticmethod
        def func(_):
            raise FileNotFoundError("no root")

    monkeypatch.setattr(parser, "parse_args", lambda argv: FakeArgs())
    monkeypatch.setattr(scheduler, "build_parser", lambda: parser)

    result = main(["plan"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: no root" in captured.err
