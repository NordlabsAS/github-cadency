"""Audit event emission for tamper-evident compliance logging.

Audit events are structured log entries shipped to Loki via Promtail.
Loki's append-only storage with retention policy enforcement provides
the tamper-evidence guarantee required for SOC 2 and ISO 27001.

Usage:
    from myproject_observability import emit_audit_event

    emit_audit_event(
        event_type="audit.document.created",
        actor_id=user.id,
        actor_email=user.email,
        org_id=user.org_id,
        entity_type="document",
        entity_id=str(doc_id),
        action="created",
        app="myapp",
    )
"""

from __future__ import annotations

import contextlib

import structlog

_audit_logger = structlog.get_logger("claros.audit")


def emit_audit_event(
    *,
    event_type: str,
    actor_id: str,
    org_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    app: str,
    actor_email: str | None = None,
    actor_role: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> None:
    """Emit a structured audit event to stdout for Loki ingestion.

    This function never raises — audit failures are logged at ERROR level
    but never block the calling operation.

    Fields are chosen to satisfy SOC 2 CC6.1/CC7.2 requirements:
    - Who: actor_id, actor_email, actor_role
    - What: entity_type, entity_id, action, event_type
    - Where: app, org_id
    - When: auto-added by structlog TimeStamper
    - Context: metadata, ip_address, request_id
    """
    try:
        _audit_logger.info(
            event_type,
            event_type=event_type,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            org_id=org_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            app=app,
            metadata=metadata,
            ip_address=ip_address,
            request_id=request_id,
        )
    except Exception:
        with contextlib.suppress(Exception):
            structlog.get_logger().error(
                "audit.emission_failed",
                event_type=event_type,
                entity_type=entity_type,
                entity_id=str(entity_id),
            )
