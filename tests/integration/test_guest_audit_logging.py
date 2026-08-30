# Feature: guest-management, Property 8: Audit log data safety
"""Integration tests for guest audit log data safety.

Validates: Requirements 9.1, 9.2

After create/update operations via the GuestService, verify that audit log
entries contain only operation, timestamp, id, and result — and NEVER contain
tokens, passwords, or guest PII (email, phone, identification number).
"""

import logging
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import IdentificationType
from app.repositories.guest_repository import GuestRepository
from app.schemas.guest import GuestCreate, GuestUpdate
from app.services.guest_service import GuestService

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

JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
BEARER_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)

# Guest PII values used in the sample data — must never appear in logs.
GUEST_EMAIL = "john.doe@example.com"
GUEST_PHONE = "5551234"
GUEST_ID_NUMBER = "X1234567"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def guest_service(db_session):
    return GuestService(repository=GuestRepository(db=db_session))


@pytest.fixture()
def sample_guest_data():
    return GuestCreate(
        first_name="John",
        last_name="Doe",
        email=GUEST_EMAIL,
        phone=GUEST_PHONE,
        identification_type=IdentificationType.NATIONAL_ID,
        identification_number=GUEST_ID_NUMBER,
    )


def _assert_required_fields(record: logging.LogRecord) -> None:
    assert hasattr(record, "operation")
    assert hasattr(record, "timestamp")
    assert hasattr(record, "room_id")  # audit_log reuses this key as the entity id
    assert hasattr(record, "result")


def _assert_no_sensitive_data(record: logging.LogRecord) -> None:
    record_str = str(record.__dict__)
    lowered = record_str.lower()

    for keyword in SENSITIVE_KEYWORDS:
        assert keyword not in lowered, f"Audit log contains '{keyword}': {record_str}"

    assert not JWT_PATTERN.search(record_str)
    assert not BEARER_PATTERN.search(record_str)

    # No guest PII should leak into the audit record.
    assert GUEST_EMAIL not in record_str
    assert GUEST_PHONE not in record_str
    assert GUEST_ID_NUMBER not in record_str


class TestAuditLogCreate:
    def test_create_emits_audit_log(
        self, guest_service, sample_guest_data, caplog
    ):
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            guest = guest_service.create_guest(sample_guest_data)

        records = [r for r in caplog.records if r.message == "audit_event"]
        assert len(records) == 1
        record = records[0]
        assert record.operation == "create"
        assert record.result == "success"
        assert record.room_id == guest.id
        _assert_required_fields(record)

    def test_create_audit_log_no_sensitive_data(
        self, guest_service, sample_guest_data, caplog
    ):
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            guest_service.create_guest(sample_guest_data)

        for record in caplog.records:
            _assert_no_sensitive_data(record)


class TestAuditLogUpdate:
    def test_update_emits_audit_log(
        self, guest_service, sample_guest_data, caplog
    ):
        guest = guest_service.create_guest(sample_guest_data)

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            guest_service.update_guest(guest.id, GuestUpdate(phone="5559999"))

        records = [r for r in caplog.records if r.message == "audit_event"]
        assert len(records) == 1
        record = records[0]
        assert record.operation == "update"
        assert record.result == "success"
        assert record.room_id == guest.id
        _assert_required_fields(record)

    def test_update_audit_log_no_sensitive_data(
        self, guest_service, sample_guest_data, caplog
    ):
        guest = guest_service.create_guest(sample_guest_data)

        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            guest_service.update_guest(guest.id, GuestUpdate(phone="5559999"))

        for record in caplog.records:
            _assert_no_sensitive_data(record)
