# Feature: reservation-management, Property 11: Audit log data safety
"""Integration tests for reservation audit log data safety.

Validates: Requirements 12.1, 12.2

After create/update/cancel operations via the ReservationService, verify that
audit log entries contain only operation, timestamp, reservation id, and result
— and NEVER contain guest PII, tokens, or passwords.
"""

import logging
import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import Guest, IdentificationType
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.reservation_service import ReservationService

SENSITIVE_KEYWORDS = [
    "token", "password", "secret", "bearer",
    "authorization", "credential", "api_key", "apikey", "private_key",
]

JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
BEARER_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)

# Guest PII seeded — must never appear in audit records.
GUEST_EMAIL = "john@example.com"
GUEST_PHONE = "5551234"
GUEST_ID_NUMBER = "X1234567"


@pytest.fixture()
def service_and_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    session.add(
        Guest(
            first_name="John",
            last_name="Doe",
            email=GUEST_EMAIL,
            phone=GUEST_PHONE,
            identification_type=IdentificationType.NATIONAL_ID,
            identification_number=GUEST_ID_NUMBER,
        )
    )
    session.add(
        Room(
            room_number="101",
            room_type=RoomType.INDIVIDUAL,
            price_per_night=Decimal("100.00"),
            capacity=2,
            status=RoomStatus.DISPONIBLE,
        )
    )
    session.commit()

    service = ReservationService(
        repository=ReservationRepository(session),
        room_repository=RoomRepository(session),
        guest_repository=GuestRepository(session),
    )
    try:
        yield service, session
    finally:
        session.close()
        engine.dispose()


def _create(service, session):
    reservation = service.create_reservation(
        ReservationCreate(
            guest_id=1,
            room_id=1,
            check_in_date=date(2026, 9, 1),
            check_out_date=date(2026, 9, 5),
        )
    )
    session.commit()
    return reservation


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
    assert GUEST_EMAIL not in record_str
    assert GUEST_PHONE not in record_str
    assert GUEST_ID_NUMBER not in record_str


class TestAuditCreate:
    def test_create_emits_audit_log(self, service_and_session, caplog):
        service, session = service_and_session
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            reservation = _create(service, session)
        records = [r for r in caplog.records if r.message == "audit_event"]
        assert len(records) == 1
        assert records[0].operation == "create"
        assert records[0].result == "success"
        assert records[0].room_id == reservation.id
        _assert_required_fields(records[0])

    def test_create_no_sensitive_data(self, service_and_session, caplog):
        service, session = service_and_session
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            _create(service, session)
        for record in caplog.records:
            _assert_no_sensitive_data(record)


class TestAuditUpdate:
    def test_update_emits_audit_log(self, service_and_session, caplog):
        service, session = service_and_session
        reservation = _create(service, session)
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            service.update_reservation(
                reservation.id, ReservationUpdate(check_out_date=date(2026, 9, 6))
            )
        records = [r for r in caplog.records if r.message == "audit_event"]
        assert len(records) == 1
        assert records[0].operation == "update"
        assert records[0].room_id == reservation.id
        _assert_no_sensitive_data(records[0])


class TestAuditCancel:
    def test_cancel_emits_audit_log(self, service_and_session, caplog):
        service, session = service_and_session
        reservation = _create(service, session)
        with caplog.at_level(logging.INFO, logger="staybook.audit"):
            service.cancel_reservation(reservation.id)
        records = [r for r in caplog.records if r.message == "audit_event"]
        assert len(records) == 1
        assert records[0].operation == "cancel"
        assert records[0].room_id == reservation.id
        _assert_no_sensitive_data(records[0])
