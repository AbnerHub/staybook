# Feature: reservation-management
"""Property-based tests for ReservationService.

Covers:
- P1/P2: Creation round-trip + total_price calculation (Req 1.1, 1.2, 3.2, 6.1)
- P4: Invalid dates rejection (Req 3.1)
- P5: Overlap and adjacency (Req 4.1, 4.2, 4.3)
- P6: Cancelled reservations release their range (Req 4.4)
- P7: Partial update resulting state + self-exclusion (Req 7.4, 7.5, 7.6)
- P8/P9: Cancellation + missing entities (Req 2.1, 2.2, 8.1, 8.2, 8.4, 8.6, 7.9)
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    GuestNotFoundException,
    ReservationAlreadyCancelledException,
    ReservationCancelledNotEditableException,
    ReservationInvalidDatesException,
    ReservationOverlapException,
    RoomNotFoundException,
)
from app.db.base import Base
from app.models.guest import Guest, IdentificationType
from app.models.reservation import ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.reservation_service import ReservationService

BASE_DATE = date(2026, 9, 1)


@pytest.fixture
def service_factory():
    """Factory building a fresh service backed by in-memory SQLite,
    seeded with one guest and one room (id=1 each)."""

    def _build(price: str = "100.00"):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        guest = Guest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="5551234",
            identification_type=IdentificationType.NATIONAL_ID,
            identification_number="X1",
        )
        room = Room(
            room_number="101",
            room_type=RoomType.INDIVIDUAL,
            price_per_night=Decimal(price),
            capacity=2,
            status=RoomStatus.DISPONIBLE,
        )
        session.add_all([guest, room])
        session.commit()

        service = ReservationService(
            repository=ReservationRepository(session),
            room_repository=RoomRepository(session),
            guest_repository=GuestRepository(session),
        )
        return service, session, guest.id, room.id

    return _build


# --- P1 & P2: round-trip + total_price ---


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(nights=st.integers(min_value=1, max_value=60), offset=st.integers(0, 200))
def test_creation_round_trip_and_total_price(service_factory, nights, offset):
    service, session, guest_id, room_id = service_factory(price="150.00")
    try:
        check_in = BASE_DATE + timedelta(days=offset)
        check_out = check_in + timedelta(days=nights)
        created = service.create_reservation(
            ReservationCreate(
                guest_id=guest_id,
                room_id=room_id,
                check_in_date=check_in,
                check_out_date=check_out,
            )
        )
        session.commit()

        fetched = service.get_reservation(created.id)
        assert fetched.guest_id == guest_id
        assert fetched.room_id == room_id
        assert fetched.check_in_date == check_in
        assert fetched.check_out_date == check_out
        assert fetched.status == ReservationStatus.CONFIRMED
        assert fetched.total_price == Decimal(nights) * Decimal("150.00")
    finally:
        session.close()


# --- P4: invalid dates ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(delta=st.integers(min_value=0, max_value=30))
def test_invalid_dates_rejected(service_factory, delta):
    """check_out <= check_in must be rejected. Schema rejects it (ValidationError);
    the service also enforces it. Either way nothing is persisted."""
    service, session, guest_id, room_id = service_factory()
    try:
        check_in = BASE_DATE
        check_out = BASE_DATE - timedelta(days=delta)  # <= check_in
        with pytest.raises((ReservationInvalidDatesException, ValueError)):
            service.create_reservation(
                ReservationCreate.model_construct(
                    guest_id=guest_id,
                    room_id=room_id,
                    check_in_date=check_in,
                    check_out_date=check_out,
                )
            )
        session.rollback()
        assert service.list_reservations() == []
    finally:
        session.close()


# --- P5: overlap and adjacency ---


def _create(service, guest_id, room_id, in_days, out_days):
    return service.create_reservation(
        ReservationCreate(
            guest_id=guest_id,
            room_id=room_id,
            check_in_date=BASE_DATE + timedelta(days=in_days),
            check_out_date=BASE_DATE + timedelta(days=out_days),
        )
    )


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    a_in=st.integers(0, 10),
    a_len=st.integers(1, 10),
    b_in=st.integers(0, 10),
    b_len=st.integers(1, 10),
)
def test_overlap_detection(service_factory, a_in, a_len, b_in, b_len):
    service, session, guest_id, room_id = service_factory()
    try:
        a_out = a_in + a_len
        b_out = b_in + b_len
        _create(service, guest_id, room_id, a_in, a_out)
        session.commit()

        # Half-open overlap: a_in < b_out AND a_out > b_in
        overlaps = a_in < b_out and a_out > b_in
        if overlaps:
            with pytest.raises(ReservationOverlapException):
                _create(service, guest_id, room_id, b_in, b_out)
            session.rollback()
        else:
            _create(service, guest_id, room_id, b_in, b_out)
            session.commit()
            assert len(service.list_reservations()) == 2
    finally:
        session.close()


def test_adjacent_reservations_allowed(service_factory):
    """Sep 1-5 and Sep 5-8 are adjacent, not overlapping."""
    service, session, guest_id, room_id = service_factory()
    try:
        _create(service, guest_id, room_id, 0, 4)  # Sep 1 -> Sep 5
        _create(service, guest_id, room_id, 4, 7)  # Sep 5 -> Sep 8
        session.commit()
        assert len(service.list_reservations()) == 2
    finally:
        session.close()


# --- P6: cancelled reservations release their range ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(dummy=st.integers(0, 5))
def test_cancelled_releases_range(service_factory, dummy):
    service, session, guest_id, room_id = service_factory()
    try:
        first = _create(service, guest_id, room_id, 0, 5)
        session.commit()

        # Same range would overlap while confirmed
        with pytest.raises(ReservationOverlapException):
            _create(service, guest_id, room_id, 0, 5)
        session.rollback()

        # Cancel the first, then the same range becomes available
        service.cancel_reservation(first.id)
        session.commit()
        second = _create(service, guest_id, room_id, 0, 5)
        session.commit()
        assert second.id != first.id
        assert second.status == ReservationStatus.CONFIRMED
    finally:
        session.close()


# --- P7: partial update resulting state + self-exclusion ---


def test_partial_update_recalculates_and_self_excludes(service_factory):
    service, session, guest_id, room_id = service_factory(price="100.00")
    try:
        r = _create(service, guest_id, room_id, 0, 4)  # 4 nights
        session.commit()
        assert r.total_price == Decimal("400.00")

        # Extend checkout by 2 nights via partial update (only check_out_date).
        updated = service.update_reservation(
            r.id, ReservationUpdate(check_out_date=r.check_out_date + timedelta(days=2))
        )
        session.commit()
        assert updated.total_price == Decimal("600.00")  # 6 nights * 100
        assert updated.check_in_date == r.check_in_date  # preserved
    finally:
        session.close()


def test_update_same_range_self_exclusion(service_factory):
    """Updating a reservation to its own range must not conflict with itself."""
    service, session, guest_id, room_id = service_factory()
    try:
        r = _create(service, guest_id, room_id, 0, 5)
        session.commit()
        # Provide the same dates; overlap check must exclude the reservation itself.
        updated = service.update_reservation(
            r.id, ReservationUpdate(check_in_date=r.check_in_date)
        )
        session.commit()
        assert updated.id == r.id
    finally:
        session.close()


# --- P8 & P9: cancellation + missing entities ---


def test_cancel_preserves_record(service_factory):
    service, session, guest_id, room_id = service_factory()
    try:
        r = _create(service, guest_id, room_id, 0, 5)
        session.commit()
        original_price = r.total_price

        cancelled = service.cancel_reservation(r.id)
        session.commit()
        assert cancelled.status == ReservationStatus.CANCELLED
        assert cancelled.total_price == original_price

        # Still retrievable and listable (not deleted)
        assert service.get_reservation(r.id) is not None
        assert len(service.list_reservations()) == 1
    finally:
        session.close()


def test_recancel_rejected(service_factory):
    service, session, guest_id, room_id = service_factory()
    try:
        r = _create(service, guest_id, room_id, 0, 5)
        session.commit()
        service.cancel_reservation(r.id)
        session.commit()
        with pytest.raises(ReservationAlreadyCancelledException):
            service.cancel_reservation(r.id)
    finally:
        session.close()


def test_update_cancelled_rejected(service_factory):
    service, session, guest_id, room_id = service_factory()
    try:
        r = _create(service, guest_id, room_id, 0, 5)
        session.commit()
        service.cancel_reservation(r.id)
        session.commit()
        with pytest.raises(ReservationCancelledNotEditableException):
            service.update_reservation(
                r.id, ReservationUpdate(check_out_date=r.check_out_date + timedelta(days=1))
            )
    finally:
        session.close()


def test_missing_guest_rejected(service_factory):
    service, session, _guest_id, room_id = service_factory()
    try:
        with pytest.raises(GuestNotFoundException):
            _create(service, 9999, room_id, 0, 5)
    finally:
        session.close()


def test_missing_room_rejected(service_factory):
    service, session, guest_id, _room_id = service_factory()
    try:
        with pytest.raises(RoomNotFoundException):
            _create(service, guest_id, 9999, 0, 5)
    finally:
        session.close()
