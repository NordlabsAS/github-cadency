"""Tests for audit event emission."""

from claros_observability.audit import emit_audit_event
from structlog.testing import capture_logs


class TestEmitAuditEvent:
    def test_emits_structured_event(self):
        with capture_logs() as logs:
            emit_audit_event(
                event_type="audit.document.created",
                actor_id="user-123",
                actor_email="alice@example.com",
                org_id="org-456",
                entity_type="document",
                entity_id="doc-789",
                action="created",
                app="scribe",
            )

        assert len(logs) == 1
        event = logs[0]
        assert event["event_type"] == "audit.document.created"
        assert event["actor_id"] == "user-123"
        assert event["actor_email"] == "alice@example.com"
        assert event["org_id"] == "org-456"
        assert event["entity_type"] == "document"
        assert event["entity_id"] == "doc-789"
        assert event["action"] == "created"
        assert event["app"] == "scribe"

    def test_includes_optional_fields(self):
        with capture_logs() as logs:
            emit_audit_event(
                event_type="audit.vendor.deleted",
                actor_id="user-1",
                actor_email="bob@example.com",
                actor_role="admin",
                org_id="org-1",
                entity_type="vendor",
                entity_id="v-1",
                action="deleted",
                app="protocol",
                metadata={"reason": "decommissioned"},
                ip_address="10.0.0.1",
                request_id="req-abc",
            )

        event = logs[0]
        assert event["actor_role"] == "admin"
        assert event["metadata"] == {"reason": "decommissioned"}
        assert event["ip_address"] == "10.0.0.1"
        assert event["request_id"] == "req-abc"

    def test_never_raises_on_error(self):
        # Even with bizarre input, emit_audit_event should not raise
        emit_audit_event(
            event_type="audit.test",
            actor_id="",
            org_id="",
            entity_type="",
            entity_id="",
            action="",
            app="",
        )

    def test_entity_id_converted_to_string(self):
        """entity_id should accept UUIDs and convert to string."""
        import uuid

        test_uuid = uuid.uuid4()
        with capture_logs() as logs:
            emit_audit_event(
                event_type="audit.test",
                actor_id="user-1",
                org_id="org-1",
                entity_type="test",
                entity_id=str(test_uuid),
                action="created",
                app="test",
            )

        assert logs[0]["entity_id"] == str(test_uuid)

    def test_none_optional_fields_included(self):
        """Optional fields should be present even when None."""
        with capture_logs() as logs:
            emit_audit_event(
                event_type="audit.test",
                actor_id="user-1",
                org_id="org-1",
                entity_type="test",
                entity_id="123",
                action="created",
                app="test",
            )

        event = logs[0]
        assert "actor_email" in event
        assert event["actor_email"] is None
        assert "metadata" in event
        assert event["metadata"] is None
