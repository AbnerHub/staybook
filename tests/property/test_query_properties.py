# Feature: history-occupancy-availability-management
"""Property-based and unit tests for QueryService.

Covers:
- P1/P2: occupancy summary consistency (Req 1, 2)
- P3/P6: availability core semantics (Req 3, 10)
- P4: occupied-now but available-future
- P7: maintenance always excluded
- P5: half-open adjacency
- P8/P9/P10: history filters
- P13: read-only behavior
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import Guest, IdentificationType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.services.query_service import HistoryFilters, QueryService


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _service(session):
    return QueryService(
        room_repository=RoomRepository(session),
        reservation_repository=ReservationRepository(session),
    )


def _guest(session):
    session.add(
        Guest(
            first_name="John", last_name="Doe", email="john@example.com",
            phone="5551234", identification_type=IdentificationType.NATIONAL_ID,
            identification_number="X1",
        )
    )
    session.flush()


def _room(session, number, status=RoomStatus.DISPONIBLE) -> Room:
    room = Room(
        room_number=number, room_type=RoomType.INDIVIDUAL,
        price_per_night=Decimal("100.00"), capacity=2, status=status,
    )
    session.add(room)
    session.flush()
    return room


def _reservation(session, room_id, ci, co, status=ReservationStatus.CONFIRMED):
    session.add(
        Reservation(
            guest_id=1, room_id=room_id, check_in_date=ci, check_out_date=co,
            status=status, total_price=Decimal("400.00"),
        )
    )
    session.flush()


# --- P1/P2: occupancy summary ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_disp=st.integers(0, 5),
    n_ocup=st.integers(0, 5),
    n_mant=st.integers(0, 5),
)
def test_occupancy_summary_consistency(n_disp, n_ocup, n_mant):
    session = _make_session()
    try:
        counter = 0
        for _ in range(n_disp):
            counter += 1
            _room(session, f"D{counter}", RoomStatus.DISPONIBLE)
        for _ in range(n_ocup):
            counter += 1
            _room(session, f"O{counter}", RoomStatus.OCUPADA)
        for _ in range(n_mant):
            counter += 1
            _room(session, f"M{counter}", RoomStatus.MANTENIMIENTO)
        session.commit()

        summary = _service(session).get_current_occupancy()
        total = n_disp + n_ocup + n_mant
        assert summary.total_rooms == total
        assert summary.occupied_rooms == n_ocup
        assert summary.available_rooms == n_disp
        assert summary.maintenance_rooms == n_mant
        assert (
            summary.occupied_rooms
            + summary.available_rooms
            + summary.maintenance_rooms
            == summary.total_rooms
        )
        if total == 0:
            assert summary.occupancy_rate == 0.0
        else:
            assert summary.occupancy_rate == pytest.approx(n_ocup / total)
    finally:
        session.close()


def test_occupied_list_equals_ocupada_rooms():
    session = _make_session()
    try:
        _room(session, "101", RoomStatus.OCUPADA)
        _room(session, "102", RoomStatus.DISPONIBLE)
        _room(session, "103", RoomStatus.OCUPADA)
        session.commit()
        occupied = _service(session).list_occupied_rooms()
        assert {r.room_number for r in occupied} == {"101", "103"}
        assert all(r.status == RoomStatus.OCUPADA for r in occupied)
    finally:
        session.close()


def test_occupied_list_empty():
    session = _make_session()
    try:
        _room(session, "101", RoomStatus.DISPONIBLE)
        session.commit()
        assert _service(session).list_occupied_rooms() == []
    finally:
        session.close()


# --- P3/P6: availability core semantics ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    status=st.sampled_from(list(ReservationStatus)),
)
def test_availability_blocking_by_status(status):
    session = _make_session()
    try:
        _guest(session)
        room = _room(session, "101", RoomStatus.DISPONIBLE)
        _reservation(
            session, room.id, date(2026, 9, 1), date(2026, 9, 5), status=status
        )
        session.commit()
        available = _service(session).list_available_rooms(
            date(2026, 9, 2), date(2026, 9, 4)
        )
        ids = {r.id for r in available}
        if status in (ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN):
            assert room.id not in ids  # active → blocked
        else:
            assert room.id in ids  # cancelled/checked_out → not blocked
    finally:
        session.close()


# --- P4: occupied-now but available-future ---


def test_occupied_now_but_available_future():
    session = _make_session()
    try:
        _guest(session)
        # Room is OCUPADA now, with a checked_in reservation ending Sep 5.
        room = _room(session, "101", RoomStatus.OCUPADA)
        _reservation(
            session, room.id, date(2026, 9, 1), date(2026, 9, 5),
            status=ReservationStatus.CHECKED_IN,
        )
        session.commit()
        # Future range [Sep 10, Sep 12) does not overlap → available despite ocupada.
        available = _service(session).list_available_rooms(
            date(2026, 9, 10), date(2026, 9, 12)
        )
        assert room.id in {r.id for r in available}
    finally:
        session.close()


# --- P7: maintenance always excluded ---


def test_maintenance_never_available():
    session = _make_session()
    try:
        room = _room(session, "101", RoomStatus.MANTENIMIENTO)
        session.commit()
        # No reservations at all, otherwise-free range → still not available.
        available = _service(session).list_available_rooms(
            date(2026, 9, 1), date(2026, 9, 5)
        )
        assert room.id not in {r.id for r in available}
    finally:
        session.close()


# --- P5: half-open adjacency ---


def test_adjacent_reservation_does_not_block():
    session = _make_session()
    try:
        _guest(session)
        room = _room(session, "101", RoomStatus.DISPONIBLE)
        _reservation(session, room.id, date(2026, 9, 1), date(2026, 9, 5))
        session.commit()
        # Request [Sep 5, Sep 8) is adjacent → available.
        available = _service(session).list_available_rooms(
            date(2026, 9, 5), date(2026, 9, 8)
        )
        assert room.id in {r.id for r in available}
        # Request [Aug 29, Sep 1) ends where existing starts → available.
        available2 = _service(session).list_available_rooms(
            date(2026, 8, 29), date(2026, 9, 1)
        )
        assert room.id in {r.id for r in available2}
    finally:
        session.close()


def test_intersecting_reservation_blocks():
    session = _make_session()
    try:
        _guest(session)
        room = _room(session, "101", RoomStatus.DISPONIBLE)
        _reservation(session, room.id, date(2026, 9, 1), date(2026, 9, 5))
        session.commit()
        available = _service(session).list_available_rooms(
            date(2026, 9, 3), date(2026, 9, 7)
        )
        assert room.id not in {r.id for r in available}
    finally:
        session.close()


def test_availability_empty_when_all_blocked_or_maintenance():
    session = _make_session()
    try:
        _guest(session)
        r1 = _room(session, "101", RoomStatus.MANTENIMIENTO)  # noqa: F841
        r2 = _room(session, "102", RoomStatus.DISPONIBLE)
        _reservation(session, r2.id, date(2026, 9, 1), date(2026, 9, 5))
        session.commit()
        available = _service(session).list_available_rooms(
            date(2026, 9, 2), date(2026, 9, 4)
        )
        assert available == []
    finally:
        session.close()


# --- P8/P9/P10: history filters ---


def test_history_no_filters_all_statuses():
    session = _make_session()
    try:
        _guest(session)
        room = _room(session, "101")
        _reservation(session, room.id, date(2026, 9, 1), date(2026, 9, 5),
                     status=ReservationStatus.CONFIRMED)
        _reservation(session, room.id, date(2026, 10, 1), date(2026, 10, 5),
                     status=ReservationStatus.CANCELLED)
        session.commit()
        result = _service(session).get_reservation_history(HistoryFilters())
        assert len(result) == 2
    finally:
        session.close()


def test_history_combined_filters_and():
    session = _make_session()
    try:
        _guest(session)
        _room(session, "101")
        _room(session, "102")
        _reservation(session, 1, date(2026, 9, 1), date(2026, 9, 5),
                     status=ReservationStatus.CONFIRMED)
        _reservation(session, 2, date(2026, 9, 1), date(2026, 9, 5),
                     status=ReservationStatus.CONFIRMED)
        _reservation(session, 1, date(2026, 10, 1), date(2026, 10, 5),
                     status=ReservationStatus.CANCELLED)
        session.commit()
        result = _service(session).get_reservation_history(
            HistoryFilters(room_id=1, status=ReservationStatus.CONFIRMED)
        )
        assert len(result) == 1
        assert result[0].room_id == 1
    finally:
        session.close()


def test_history_nonexistent_id_returns_empty():
    session = _make_session()
    try:
        _guest(session)
        _room(session, "101")
        _reservation(session, 1, date(2026, 9, 1), date(2026, 9, 5))
        session.commit()
        result = _service(session).get_reservation_history(
            HistoryFilters(guest_id=9999)
        )
        assert result == []
    finally:
        session.close()


# --- P13: read-only ---


def test_queries_are_read_only():
    session = _make_session()
    try:
        _guest(session)
        _room(session, "101", RoomStatus.OCUPADA)
        _room(session, "102", RoomStatus.DISPONIBLE)
        _reservation(session, 2, date(2026, 9, 1), date(2026, 9, 5))
        session.commit()

        before_rooms = {
            r.id: r.status for r in session.query(Room).all()
        }
        before_res = {
            r.id: r.status for r in session.query(Reservation).all()
        }

        service = _service(session)
        service.get_current_occupancy()
        service.list_occupied_rooms()
        service.list_available_rooms(date(2026, 9, 10), date(2026, 9, 12))
        service.get_reservation_history(HistoryFilters())
        session.expire_all()

        after_rooms = {r.id: r.status for r in session.query(Room).all()}
        after_res = {r.id: r.status for r in session.query(Reservation).all()}
        assert before_rooms == after_rooms
        assert before_res == after_res
    finally:
        session.close()
