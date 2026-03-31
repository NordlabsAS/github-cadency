"""Structured logging setup using structlog."""

import logging

import structlog


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog for the application.

    Call this once at startup, before any logger is created.

    Args:
        level: Python log level name (DEBUG, INFO, WARNING, ERROR).
        json_output: True for JSON (production), False for pretty console (dev).
    """
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a bound structlog logger instance."""
    return structlog.get_logger(name)
