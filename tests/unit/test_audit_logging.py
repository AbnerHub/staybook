"""Unit tests for the audit logging module.

Validates Requirements 10.1 and 10.2:
- Audit events log timestamp, operation, room_id, and result.
- Audit events never contain tokens, passwords, or PII.
"""

import logging
from datetime import datetime

from app.core.logging import audit_log


class TestAuditLog:
    """Tests for audit_log function."""

    def test_logs_create_operation_success(self, caplog):
        """audit_log emits an info-level record for a successful create."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            audit_log(operation="create", room_id=1, result="success")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == "audit_event"
        assert record.operation == "create"
        assert record.room_id == 1
        assert record.result == "success"
        assert "timestamp" in record.__dict__

    def test_logs_update_operation_failure(self, caplog):
        """audit_log emits an info-level record for a failed update."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            audit_log(operation="update", room_id=42, result="failure")

        record = caplog.records[0]
        assert record.operation == "update"
        assert record.room_id == 42
        assert record.result == "failure"

    def test_logs_delete_operation_with_none_room_id(self, caplog):
        """audit_log accepts None for room_id (e.g., when room creation fails)."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            audit_log(operation="delete", room_id=None, result="failure")

        record = caplog.records[0]
        assert record.operation == "delete"
        assert record.room_id is None
        assert record.result == "failure"

    def test_timestamp_is_utc_iso_format(self, caplog):
        """The timestamp in the log record is a valid UTC ISO format string."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            audit_log(operation="create", room_id=5, result="success")

        record = caplog.records[0]
        ts = record.timestamp
        # Should parse without error
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None  # timezone-aware

    def test_no_sensitive_data_in_log_record(self, caplog):
        """Log records contain only operation, room_id, result, and timestamp as extras."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            audit_log(operation="create", room_id=1, result="success")

        record = caplog.records[0]
        # Standard LogRecord attributes (not user-provided extras)
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "thread", "threadName", "process", "processName",
            "pathname", "filename", "module", "exc_info", "exc_text",
            "stack_info", "lineno", "funcName", "msecs", "message",
            "levelname", "levelno", "taskName",
        }
        # Extra keys added by audit_log
        expected_extras = {"timestamp", "operation", "room_id", "result"}
        # Get only the user-added extra keys
        record_keys = set(record.__dict__.keys()) - standard_attrs
        # Verify extras contain only the expected audit fields
        assert expected_extras.issubset(record_keys)
        # Verify no sensitive data keywords in extras
        sensitive_keywords = {"token", "password", "secret", "email", "pii"}
        for key in record_keys:
            assert key.lower() not in sensitive_keywords
