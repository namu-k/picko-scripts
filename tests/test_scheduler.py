from xml.etree import ElementTree

from scripts.scheduler import format_cron_time, render_cron, render_launchd, render_systemd


def test_time_parsing_0800_to_cron_expression():
    assert format_cron_time("08:00") == "0 8 * * *"


def test_cron_output_format_valid(tmp_path):
    project_root = tmp_path / "picko"
    project_root.mkdir()
    workflow_path = project_root / "config" / "workflows" / "daily.yml"

    cron_line = render_cron(workflow_path=workflow_path, project_root=project_root, run_time="08:00")

    assert cron_line.startswith("0 8 * * * ")
    assert "python -m scripts.run_workflow" in cron_line


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
