"""Tests for observability logging."""

from claros_observability import configure_logging, get_logger


class TestLogging:
    def test_imports(self):
        assert callable(get_logger)
        assert callable(configure_logging)

    def test_get_logger(self):
        logger = get_logger("test")
        assert logger is not None
