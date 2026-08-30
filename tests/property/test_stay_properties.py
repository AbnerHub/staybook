# Feature: checkin-checkout-management
"""Property-based and unit tests for StayService.

Covers:
- P1/P2/P3: valid check-in + date rule (Req 2.1, 2.2, 3.1, 3.2, 3.3)
- P4: invalid check-in transitions (Req 2.4)
- P5/P6: valid/invalid check-out (Req 4.1, 4.2, 4.4, 4.5)
- P7/P9: atomicity + preservation (Req 5.1, 5.2, 2.6, 4.7)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    CheckInDateNotAllowedException,
    ReservationInvalidTransitionException,
)
from app.db.base import Base
from app.models.guest import Guest, IdentificationType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.services.stay_service import StayService

CHECK_IN = date(2026, 9, 1)
CHECK_OUT = date(2026, 9, 5)


@pytest.fixture
def stay_factory():
    """Factory building a StayService over in-memory SQLite, seeded with a
    room (id=1), guest (id=1) and one reservation with a given status.
    Returns (service, session, reservation, room)."""

    def _build(
        status: ReservationStatus = ReservationStatus.CONFIRMED,
        today: date = CHECK_IN,
    ):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        session.add(
            Guest(
                first_name="John", last_name="Doe", email="john@example.com",
                phone="5551234",
                identification_type=IdentificationType.NATIONAL_ID,
                identification_number="X1",
            )
        )
        room = Room(
            room_number="101", room_type=RoomType.INDIVIDUAL,
            price_per_night=Decimal("100.00"), capacity=2,
            status=RoomStatus.DISPONIBLE,
        )
        session.add(room)
        session.flush()

        reservation = Reservation(
            guest_id=1, room_id=room.id,
            check_in_date=CHECK_IN, check_out_date=CHECK_OUT,
            status=status, total_price=Decimal("400.00"),
        )
        session.add(reservation)
        session.commit()

        service = StayService(
            session=session,
            reservation_repository=ReservationRepository(session),
            room_repository=RoomRepository(session),
            today_provider=lambda: today,
        )
        return service, session, reservation, room

    return _build


# --- P1: valid check-in ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(day_offset=st.integers(min_value=0, max_value=3))
def test_valid_checkin(stay_factory, day_offset):
    """check_in_date <= today < check_out_date → checked_in + room ocupada."""
    today = CHECK_IN + timedelta(days=day_offset)  # Sep 1..4 (< Sep 5)
    service, session, reservation, _room = stay_factory(today=today)
    try:
        result = service.check_in(reservation.id)
        assert result.status == ReservationStatus.CHECKED_IN
        assert service.room_repository.get_by_id(_room.id).status == RoomStatus.OCUPADA
    finally:
        session.close()


# --- P2: early check-in ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(days_before=st.integers(min_value=1, max_value=30))
def test_early_checkin_rejected(stay_factory, days_before):
    today = CHECK_IN - timedelta(days=days_before)
    service, session, reservation, _room = stay_factory(today=today)
    try:
        with pytest.raises(CheckInDateNotAllowedException):
            service.check_in(reservation.id)
        # No changes persisted
        assert service.reservation_repository.get_by_id(
            reservation.id
        ).status == ReservationStatus.CONFIRMED
        assert service.room_repository.get_by_id(_room.id).status == RoomStatus.DISPONIBLE
    finally:
        session.close()


# --- P3: late check-in (on or after check_out_date) ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(days_after=st.integers(min_value=0, max_value=30))
def test_late_checkin_rejected(stay_factory, days_after):
    today = CHECK_OUT + timedelta(days=days_after)  # >= Sep 5
    service, session, reservation, _room = stay_factory(today=today)
    try:
        with pytest.raises(CheckInDateNotAllowedException):
            service.check_in(reservation.id)
        assert service.reservation_repository.get_by_id(
            reservation.id
        ).status == ReservationStatus.CONFIRMED
    finally:
        session.close()


def test_checkin_on_checkout_date_rejected(stay_factory):
    """Boundary: today == check_out_date is not allowed."""
    service, session, reservation, _room = stay_factory(today=CHECK_OUT)
    try:
        with pytest.raises(CheckInDateNotAllowedException):
            service.check_in(reservation.id)
    finally:
        session.close()


# --- P4: invalid check-in transitions ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    status=st.sampled_from(
        [
            ReservationStatus.CHECKED_IN,
            ReservationStatus.CHECKED_OUT,
            ReservationStatus.CANCELLED,
        ]
    )
)
def test_invalid_checkin_transition(stay_factory, status):
    """Any status other than confirmed → check-in rejected (409)."""
    service, session, reservation, _room = stay_factory(status=status, today=CHECK_IN)
    try:
        with pytest.raises(ReservationInvalidTransitionException):
            service.check_in(reservation.id)
    finally:
        session.close()


# --- P5: valid check-out (any date) ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(day_offset=st.integers(min_value=-10, max_value=30))
def test_valid_checkout_any_date(stay_factory, day_offset):
    today = CHECK_IN + timedelta(days=day_offset)
    service, session, reservation, _room = stay_factory(
        status=ReservationStatus.CHECKED_IN, today=today
    )
    try:
        result = service.check_out(reservation.id)
        assert result.status == ReservationStatus.CHECKED_OUT
        assert service.room_repository.get_by_id(_room.id).status == RoomStatus.DISPONIBLE
    finally:
        session.close()


# --- P6: invalid check-out transitions ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    status=st.sampled_from(
        [
            ReservationStatus.CONFIRMED,
            ReservationStatus.CHECKED_OUT,
            ReservationStatus.CANCELLED,
        ]
    )
)
def test_invalid_checkout_transition(stay_factory, status):
    """Any status other than checked_in → check-out rejected (409)."""
    service, session, reservation, _room = stay_factory(status=status, today=CHECK_IN)
    try:
        with pytest.raises(ReservationInvalidTransitionException):
            service.check_out(reservation.id)
    finally:
        session.close()


# --- P9: preservation ---


def test_checkin_preserves_fields(stay_factory):
    service, session, reservation, _room = stay_factory(today=CHECK_IN)
    try:
        original = (
            reservation.id, reservation.guest_id, reservation.room_id,
            reservation.check_in_date, reservation.check_out_date,
            reservation.total_price,
        )
        service.check_in(reservation.id)
        r = service.reservation_repository.get_by_id(reservation.id)
        assert (
            r.id, r.guest_id, r.room_id, r.check_in_date, r.check_out_date,
            r.total_price,
        ) == original
    finally:
        session.close()


def test_checkout_preserves_and_does_not_delete(stay_factory):
    service, session, reservation, _room = stay_factory(
        status=ReservationStatus.CHECKED_IN, today=CHECK_IN
    )
    try:
        rid = reservation.id
        service.check_out(rid)
        # Still exists (not deleted), fields preserved except status
        r = service.reservation_repository.get_by_id(rid)
        assert r is not None
        assert r.total_price == Decimal("400.00")
        assert r.check_in_date == CHECK_IN
    finally:
        session.close()


# --- P7: atomicity ---


def test_atomicity_rollback_on_failure():
    """If the second update (room) fails, rollback is invoked and nothing persists."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        Guest(
            first_name="John", last_name="Doe", email="john@example.com",
            phone="5551234", identification_type=IdentificationType.NATIONAL_ID,
            identification_number="X1",
        )
    )
    room = Room(
        room_number="101", room_type=RoomType.INDIVIDUAL,
        price_per_night=Decimal("100.00"), capacity=2, status=RoomStatus.DISPONIBLE,
    )
    session.add(room)
    session.flush()
    reservation = Reservation(
        guest_id=1, room_id=room.id, check_in_date=CHECK_IN, check_out_date=CHECK_OUT,
        status=ReservationStatus.CONFIRMED, total_price=Decimal("400.00"),
    )
    session.add(reservation)
    session.commit()

    reservation_repo = ReservationRepository(session)
    # Room repo whose update fails, and a session spy to assert rollback.
    room_repo = MagicMock()
    room_repo.get_by_id.return_value = room
    room_repo.update.side_effect = RuntimeError("boom")

    spy_session = MagicMock(wraps=session)

    service = StayService(
        session=spy_session,
        reservation_repository=reservation_repo,
        room_repository=room_repo,
        today_provider=lambda: CHECK_IN,
    )

    with pytest.raises(RuntimeError):
        service.check_in(reservation.id)

    spy_session.rollback.assert_called_once()
    spy_session.commit.assert_not_called()

    session.rollback()
    # Reservation status not persisted as checked_in
    fresh = sessionmaker(bind=engine)()
    try:
        persisted = fresh.get(Reservation, reservation.id)
        assert persisted.status == ReservationStatus.CONFIRMED
    finally:
        fresh.close()
        session.close()
