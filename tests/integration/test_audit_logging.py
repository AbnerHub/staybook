# Feature: room-management, Property 10: Audit log data safety
"""Integration tests for audit log data safety.

Validates: Requirements 10.1, 10.2

After create/update/delete operations via the RoomService, verify that
audit log entries contain only operation, timestamp, room_id, and result —
and NEVER contain tokens, passwords, or other sensitive information.
"""

import logging
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.room import RoomStatus, RoomType
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomUpdate
from app.services.room_service import RoomService


# Sensitive data patterns that must NEVER appear in audit logs
SENSITIVE_KEYWORDS = [
    "token",
    "password",
    "secret",
    "bearer",
    "authorization",
    "credential",
    "api_key",
    "apikey",
    "private_key",
]

# JWT-like pattern: base64.base64.base64
JWT_PATTERN = re.compile(
    r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)

# Generic Bearer token pattern
BEARER_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database session for integration tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def room_service(db_session):
    """Create a RoomService instance backed by in-memory SQLite."""
    repository = RoomRepository(db=db_session)
    return RoomService(repository=repository)


@pytest.fixture()
def sample_room_data():
    """Valid room creation data."""
    return RoomCreate(
        room_number="101",
        room_type=RoomType.INDIVIDUAL,
        price_per_night=99.99,
        capacity=2,
        status=RoomStatus.DISPONIBLE,
        description="Habitación estándar",
        floor=1,
    )


def _assert_log_has_required_fields(record: logging.LogRecord) -> None:
    """Assert that the log record has the required audit fields."""
    assert hasattr(record, "operation"), "Log record missing 'operation' field"
    assert hasattr(record, "timestamp"), "Log record missing 'timestamp' field"
    assert hasattr(record, "room_id"), "Log record missing 'room_id' field"
    assert hasattr(record, "result"), "Log record missing 'result' field"


def _assert_log_has_no_sensitive_data(record: logging.LogRecord) -> None:
    """Assert that the log record does not contain any sensitive information."""
    # Serialize all record fields to a single string for inspection
    record_str = str(record.__dict__).lower()

    # Check sensitive keywords
    for keyword in SENSITIVE_KEYWORDS:
        assert keyword not in record_str, (
            f"Audit log contains sensitive keyword '{keyword}': {record_str}"
        )

    # Check JWT-like patterns
    record_full = str(record.__dict__)
    assert not JWT_PATTERN.search(record_full), (
        f"Audit log contains JWT-like pattern: {record_full}"
    )

    # Check Bearer token patterns
    assert not BEARER_PATTERN.search(record_full), (
        f"Audit log contains Bearer token pattern: {record_full}"
    )


class TestAuditLogCreateOperation:
    """Integration tests for audit logging during room creation."""

    def test_create_room_emits_audit_log(
        self, room_service, sample_room_data, caplog
    ):
        """Creating a room emits an audit log entry."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.create_room(sample_room_data)

        assert len(caplog.records) >= 1
        record = caplog.records[0]
        _assert_log_has_required_fields(record)
        assert record.operation == "create"
        assert record.result == "success"

    def test_create_room_audit_log_contains_room_id(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log entry for creation contains the room_id."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room = room_service.create_room(sample_room_data)

        record = caplog.records[0]
        assert record.room_id == room.id

    def test_create_room_audit_log_no_sensitive_data(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log for creation never contains tokens or passwords."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.create_room(sample_room_data)

        for record in caplog.records:
            _assert_log_has_no_sensitive_data(record)


class TestAuditLogUpdateOperation:
    """Integration tests for audit logging during room update."""

    def test_update_room_emits_audit_log(
        self, room_service, sample_room_data, caplog
    ):
        """Updating a room emits an audit log entry."""
        room = room_service.create_room(sample_room_data)
        caplog.clear()

        update_data = RoomUpdate(price_per_night=149.99)
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.update_room(room.id, update_data)

        assert len(caplog.records) >= 1
        record = caplog.records[0]
        _assert_log_has_required_fields(record)
        assert record.operation == "update"
        assert record.result == "success"

    def test_update_room_audit_log_contains_room_id(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log entry for update contains the correct room_id."""
        room = room_service.create_room(sample_room_data)
        caplog.clear()

        update_data = RoomUpdate(capacity=4)
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.update_room(room.id, update_data)

        record = caplog.records[0]
        assert record.room_id == room.id

    def test_update_room_audit_log_no_sensitive_data(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log for update never contains tokens or passwords."""
        room = room_service.create_room(sample_room_data)
        caplog.clear()

        update_data = RoomUpdate(
            description="Updated description", price_per_night=200.00
        )
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.update_room(room.id, update_data)

        for record in caplog.records:
            _assert_log_has_no_sensitive_data(record)


class TestAuditLogDeleteOperation:
    """Integration tests for audit logging during room deletion."""

    def test_delete_room_emits_audit_log(
        self, room_service, sample_room_data, caplog
    ):
        """Deleting a room emits an audit log entry."""
        room = room_service.create_room(sample_room_data)
        caplog.clear()

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.delete_room(room.id)

        assert len(caplog.records) >= 1
        record = caplog.records[0]
        _assert_log_has_required_fields(record)
        assert record.operation == "delete"
        assert record.result == "success"

    def test_delete_room_audit_log_contains_room_id(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log entry for deletion contains the room_id."""
        room = room_service.create_room(sample_room_data)
        room_id = room.id
        caplog.clear()

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.delete_room(room_id)

        record = caplog.records[0]
        assert record.room_id == room_id

    def test_delete_room_audit_log_no_sensitive_data(
        self, room_service, sample_room_data, caplog
    ):
        """The audit log for deletion never contains tokens or passwords."""
        room = room_service.create_room(sample_room_data)
        caplog.clear()

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.delete_room(room.id)

        for record in caplog.records:
            _assert_log_has_no_sensitive_data(record)


class TestAuditLogDataSafetyAcrossOperations:
    """Cross-cutting tests: no sensitive data leaks across any operation."""

    def test_full_lifecycle_no_sensitive_data(
        self, room_service, caplog
    ):
        """Create, update, and delete a room — no sensitive data in any log."""
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            # Create
            data = RoomCreate(
                room_number="201",
                room_type=RoomType.SUITE,
                price_per_night=500.00,
                capacity=4,
                status=RoomStatus.DISPONIBLE,
            )
            room = room_service.create_room(data)

            # Update
            update_data = RoomUpdate(
                status=RoomStatus.MANTENIMIENTO, price_per_night=450.00
            )
            room_service.update_room(room.id, update_data)

            # Delete (allowed because status is 'mantenimiento')
            room_service.delete_room(room.id)

        # Verify all log records
        assert len(caplog.records) == 3
        operations = [r.operation for r in caplog.records]
        assert operations == ["create", "update", "delete"]

        for record in caplog.records:
            _assert_log_has_required_fields(record)
            _assert_log_has_no_sensitive_data(record)

    def test_audit_log_only_contains_allowed_extra_fields(
        self, room_service, sample_room_data, caplog
    ):
        """Audit log extras are limited to operation, timestamp, room_id, result."""
        allowed_extras = {"operation", "timestamp", "room_id", "result"}

        # Standard LogRecord attributes to exclude from check
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "thread", "threadName", "process", "processName",
            "pathname", "filename", "module", "exc_info", "exc_text",
            "stack_info", "lineno", "funcName", "msecs", "message",
            "levelname", "levelno", "taskName",
        }

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            room_service.create_room(sample_room_data)

        for record in caplog.records:
            extra_keys = set(record.__dict__.keys()) - standard_attrs
            # All extra keys should be within the allowed set
            unexpected = extra_keys - allowed_extras
            assert not unexpected, (
                f"Unexpected fields in audit log: {unexpected}"
            )
