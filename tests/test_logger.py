from datetime import datetime
from unittest.mock import MagicMock

from picko.logger import get_logger, setup_logger


def test_setup_logger_creates_daily_log_file(tmp_path):
    logger_instance = setup_logger("collector", log_dir=tmp_path, level="INFO")
    logger_instance.info("hello")

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = tmp_path / today / "collector.log"

    assert log_file.exists()


def test_get_logger_calls_setup_logger(monkeypatch):
    sentinel_logger = MagicMock()

    def _fake_setup(script_name, log_dir=None, level="INFO", retention_days=30):
        assert script_name == "writer"
        assert log_dir is None
        assert level == "INFO"
        assert retention_days == 30
        return sentinel_logger

    monkeypatch.setattr("picko.logger.setup_logger", _fake_setup)

    result = get_logger("writer")

    assert result is sentinel_logger


def test_log_format_written_to_file(tmp_path):
    logger_instance = setup_logger("formatter", log_dir=tmp_path, level="INFO")
    logger_instance.info("formatted message")

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = tmp_path / today / "formatter.log"
    content = log_file.read_text(encoding="utf-8")

    assert "formatted message" in content
    assert " | INFO" in content
    assert "formatter" in content


def test_logger_instances_are_unique_per_name(tmp_path):
    logger_a = setup_logger("script_a", log_dir=tmp_path, level="INFO")
    logger_a.info("message from a")

    logger_b = setup_logger("script_b", log_dir=tmp_path, level="INFO")
    logger_b.info("message from b")

    today = datetime.now().strftime("%Y-%m-%d")
    log_a = (tmp_path / today / "script_a.log").read_text(encoding="utf-8")
    log_b = (tmp_path / today / "script_b.log").read_text(encoding="utf-8")

    assert logger_a != logger_b
    assert "script_a" in log_a
    assert "message from a" in log_a
    assert "script_b" in log_b
    assert "message from b" in log_b
