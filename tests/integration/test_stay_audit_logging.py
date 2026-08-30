# Feature: checkin-checkout-management, Property 11: Audit log data safety
"""Integration tests for check-in/check-out audit log data safety.

Validates: Requirements 11.1, 11.2, 11.3

After check-in / check-out via StayService, verify audit log entries contain
only operation, timestamp, reservation id, and result — never guest PII,
tokens, or passwords.
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
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.services.stay_service import StayService

SENSITIVE_KEYWORDS = [
    "token", "password", "secret", "bearer",
    "authorization", "credential", "api_key", "apikey", "private_key",
]
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
BEARER_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)

GUEST_EMAIL = "john@example.com"
GUEST_PHONE = "5551234"
GUEST_ID_NUMBER = "X1234567"

TODAY = date(2026, 9, 2)
CHECK_IN = date(2026, 9, 1)
CHECK_OUT = date(2026, 9, 5)


@pytest.fixture()
def service_and_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        Guest(
            first_name="John", last_name="Doe", email=GUEST_EMAIL,
            phone=GUEST_PHONE, identification_type=IdentificationType.NATIONAL_ID,
            identification_number=GUEST_ID_NUMBER,
        )
    )
    session.add(
        Room(
            room_number="101", room_type=RoomType.INDIVIDUAL,
            price_per_night=Decimal("100.00"), capacity=2,
            status=RoomStatus.DISPONIBLE,
        )
    )
    session.flush()
    session.add(
        Reservation(
            guest_id=1, room_id=1, check_in_date=CHECK_IN, check_out_date=CHECK_OUT,
            status=ReservationStatus.CONFIRMED, total_price=Decimal("400.00"),
        )
    )
    session.commit()

    service = StayService(
        session=session,
        reservation_repository=ReservationRepository(session),
        room_repository=RoomRepository(session),
        today_provider=lambda: TODAY,
    )
    try:
        yield service, session
    finally:
        session.close()
        engine.dispose()


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


def test_check_in_audit(service_and_session, caplog):
    service, _session = service_and_session
    with caplog.at_level(logging.INFO, logger="staybook.audit"):
        service.check_in(1)
    records = [r for r in caplog.records if r.message == "audit_event"]
    assert len(records) == 1
    assert records[0].operation == "check_in"
    assert records[0].result == "success"
    assert records[0].room_id == 1  # audit_log reuses this key as the entity id
    _assert_no_sensitive_data(records[0])


def test_check_out_audit(service_and_session, caplog):
    service, _session = service_and_session
    service.check_in(1)
    with caplog.at_level(logging.INFO, logger="staybook.audit"):
        service.check_out(1)
    records = [r for r in caplog.records if r.message == "audit_event"]
    assert len(records) == 1
    assert records[0].operation == "check_out"
    assert records[0].result == "success"
    _assert_no_sensitive_data(records[0])
