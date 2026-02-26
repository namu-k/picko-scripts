from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from picko.config import PROJECT_ROOT

ENV_VARS = [
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "RELAY_API_KEY",
    "ANTHROPIC_API_KEY",
]


def format_cron_time(run_time: str) -> str:
    parts = run_time.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {run_time}. Expected HH:MM")

    hour_raw, minute_raw = parts
    if not hour_raw.isdigit() or not minute_raw.isdigit():
        raise ValueError(f"Invalid time format: {run_time}. Expected HH:MM")

    hour = int(hour_raw)
    minute = int(minute_raw)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time value: {run_time}. Hour 0-23, minute 0-59")

    return f"{minute} {hour} * * *"


def _parse_hour_minute(run_time: str) -> tuple[int, int]:
    cron = format_cron_time(run_time)
    minute_s, hour_s, *_ = cron.split()
    return int(hour_s), int(minute_s)


def detect_project_root(start: Path | None = None) -> Path:
    if PROJECT_ROOT.exists():
        return PROJECT_ROOT.resolve()

    cursor = (start or Path.cwd()).resolve()
    for base in [cursor, *cursor.parents]:
        if (base / ".git").exists():
            return base

    raise FileNotFoundError("Could not determine project root. Expected PROJECT_ROOT or a parent with .git")


def _venv_python_for_unix(project_root: Path) -> str:
    venv_python = project_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return shlex.quote(str(venv_python))
    return "python"


def _workflow_abs(workflow_path: Path) -> Path:
    return workflow_path.expanduser().resolve()


def render_cron(workflow_path: Path, project_root: Path, run_time: str) -> str:
    workflow_abs = _workflow_abs(workflow_path)
    cron_expr = format_cron_time(run_time)
    root_quoted = shlex.quote(str(project_root.resolve()))
    workflow_quoted = shlex.quote(str(workflow_abs))
    python_exec = _venv_python_for_unix(project_root)
    return f"{cron_expr} cd {root_quoted} && {python_exec} -m scripts.run_workflow " f"--workflow {workflow_quoted}"


def render_systemd(workflow_path: Path, project_root: Path, run_time: str) -> str:
    workflow_abs = _workflow_abs(workflow_path)
    hour, minute = _parse_hour_minute(run_time)

    service_unit = f"""# /etc/systemd/system/picko-workflow.service
[Unit]
Description=Picko Workflow Runner
After=network.target

[Service]
Type=oneshot
WorkingDirectory={project_root.resolve()}
ExecStart={project_root.resolve()}/.venv/bin/python -m scripts.run_workflow --workflow {workflow_abs}
"""

    timer_unit = f"""# /etc/systemd/system/picko-workflow.timer
[Unit]
Description=Run Picko Workflow Daily

[Timer]
OnCalendar=*-*-* {hour:02d}:{minute:02d}:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    return f"{service_unit}\n{timer_unit}".rstrip()


def render_launchd(workflow_path: Path, project_root: Path, run_time: str) -> str:
    workflow_abs = _workflow_abs(workflow_path)
    hour, minute = _parse_hour_minute(run_time)
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
  <key>Label</key>
  <string>com.picko.workflow</string>
  <key>ProgramArguments</key>
  <array>
    <string>{project_root.resolve()}/.venv/bin/python</string>
    <string>-m</string>
    <string>scripts.run_workflow</string>
    <string>--workflow</string>
    <string>{workflow_abs}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{project_root.resolve()}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{project_root.resolve()}/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>{project_root.resolve()}/logs/launchd.err.log</string>
</dict>
</plist>
""".rstrip()


def render_windows(project_root: Path, run_time: str) -> str:
    hour, minute = _parse_hour_minute(run_time)
    script_path = project_root.resolve() / "scripts" / "setup_scheduler.ps1"
    return (
        "Use the existing Windows setup script:\n"
        f'  powershell -ExecutionPolicy Bypass -File "{script_path}" -Hour "{hour}" -Minute "{minute}"\n\n'
        "This creates a Windows Task Scheduler task."
    )


def render_env_reminder(include_setup: bool, windows: bool = False) -> str:
    required = ", ".join(ENV_VARS)
    if not include_setup:
        return f"Required env vars (set at least one as needed): {required}"

    if windows:
        setup_lines = "\n".join(f'  setx {name} "<your-key>"' for name in ENV_VARS)
        return f"Required env vars (set at least one as needed):\n{setup_lines}"

    setup_lines = "\n".join(f'  export {name}="<your-key>"' for name in ENV_VARS)
    return f"Required env vars (set at least one as needed):\n{setup_lines}"


def _print_section(title: str, body: str):
    print(f"[{title}]")
    print(body)
    print()


def _plan(args: argparse.Namespace) -> int:
    project_root = detect_project_root()
    workflow_path = Path(args.workflow)
    if not workflow_path.is_absolute():
        workflow_path = (Path.cwd() / workflow_path).resolve()

    selected = {
        "cron": args.cron,
        "systemd": args.systemd,
        "launchd": args.launchd,
        "windows": args.windows,
    }
    selected_names = [name for name, enabled in selected.items() if enabled]

    run_time = args.time
    if not selected_names:
        _print_section(
            "CRON",
            render_cron(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            ),
        )
        _print_section(
            "SYSTEMD",
            render_systemd(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            ),
        )
        _print_section(
            "LAUNCHD",
            render_launchd(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            ),
        )
        _print_section("WINDOWS", render_windows(project_root=project_root, run_time=run_time))
        _print_section("ENV", render_env_reminder(include_setup=args.include_env, windows=False))
        return 0

    if args.cron:
        print(
            render_cron(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            )
        )
    elif args.systemd:
        print(
            render_systemd(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            )
        )
    elif args.launchd:
        print(
            render_launchd(
                workflow_path=workflow_path,
                project_root=project_root,
                run_time=run_time,
            )
        )
    elif args.windows:
        print(render_windows(project_root=project_root, run_time=run_time))

    print()
    print(render_env_reminder(include_setup=args.include_env, windows=args.windows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate scheduler configuration snippets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Generate scheduler plan output")
    plan.add_argument("--workflow", required=True, help="Path to workflow YAML file")
    plan.add_argument("--time", default="08:00", help="Daily run time in HH:MM (default: 08:00)")
    plan.add_argument("--cron", action="store_true", help="Output cron format")
    plan.add_argument("--systemd", action="store_true", help="Output systemd unit files")
    plan.add_argument("--launchd", action="store_true", help="Output launchd plist")
    plan.add_argument("--windows", action="store_true", help="Output Windows scheduler instructions")
    plan.add_argument(
        "--include-env",
        action="store_true",
        help="Include environment variable setup examples",
    )
    plan.set_defaults(func=_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
