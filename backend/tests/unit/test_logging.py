"""Tests for the structured logging module."""

import json

import structlog

from app.logging import configure_logging, get_logger


class TestConfigureLogging:
    def test_callable(self):
        assert callable(configure_logging)

    def test_configure_json_mode(self, capsys):
        configure_logging(level="INFO", json_output=True)
        logger = get_logger("test.json")
        logger.info("hello", foo="bar")
        captured = capsys.readouterr()
        line = json.loads(captured.out.strip())
        assert line["event"] == "hello"
        assert line["foo"] == "bar"
        assert line["level"] == "info"
        assert "timestamp" in line

    def test_configure_console_mode(self, capsys):
        configure_logging(level="INFO", json_output=False)
        logger = get_logger("test.console")
        logger.info("hello console")
        captured = capsys.readouterr()
        assert "hello console" in captured.out

    def test_level_filtering(self, capsys):
        configure_logging(level="WARNING", json_output=True)
        logger = get_logger("test.level")
        logger.info("should be filtered")
        logger.warning("should appear")
        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split("\n") if l]
        assert len(lines) == 1
        assert json.loads(lines[0])["event"] == "should appear"


class TestGetLogger:
    def test_returns_bound_logger(self):
        configure_logging(level="INFO", json_output=True)
        logger = get_logger("test.bound")
        assert logger is not None

    def test_logger_without_name(self):
        configure_logging(level="INFO", json_output=True)
        logger = get_logger()
        assert logger is not None

    def test_contextvars_binding(self, capsys):
        configure_logging(level="INFO", json_output=True)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id="abc123")
        logger = get_logger("test.ctx")
        logger.info("with context")
        captured = capsys.readouterr()
        line = json.loads(captured.out.strip())
        assert line["request_id"] == "abc123"
        structlog.contextvars.clear_contextvars()
