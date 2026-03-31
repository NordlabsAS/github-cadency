"""Shared observability — structured logging and telemetry."""

from claros_observability.audit import emit_audit_event
from claros_observability.logging import configure_logging, get_logger

__all__ = ["get_logger", "configure_logging", "emit_audit_event"]
