"""Unit tests for the read-only query repository methods."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import Guest, IdentificationType  # noqa: F401 (FK table)
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def room_repo(db_session):
    return RoomRepository(db_session)


@pytest.fixture
def res_repo(db_session):
    return ReservationRepository(db_session)


def _room(number, status=RoomStatus.DISPONIBLE) -> Room:
    return Room(
        room_number=number, room_type=RoomType.INDIVIDUAL,
        price_per_night=Decimal("100.00"), capacity=2, status=status,
    )


def _reservation(room_id, ci, co, status=ReservationStatus.CONFIRMED) -> Reservation:
    return Reservation(
        guest_id=1, room_id=room_id, check_in_date=ci, check_out_date=co,
        status=status, total_price=Decimal("400.00"),
    )


class TestRoomCounts:
    def test_counts_by_status(self, room_repo, db_session):
        room_repo.create(_room("101", RoomStatus.DISPONIBLE))
        room_repo.create(_room("102", RoomStatus.OCUPADA))
        room_repo.create(_room("103", RoomStatus.MANTENIMIENTO))
        room_repo.create(_room("104", RoomStatus.OCUPADA))
        db_session.commit()

        assert room_repo.count_all() == 4
        assert room_repo.count_by_status(RoomStatus.OCUPADA) == 2
        assert room_repo.count_by_status(RoomStatus.DISPONIBLE) == 1
        assert room_repo.count_by_status(RoomStatus.MANTENIMIENTO) == 1

    def test_count_all_zero(self, room_repo):
        assert room_repo.count_all() == 0

    def test_get_by_status(self, room_repo, db_session):
        room_repo.create(_room("101", RoomStatus.OCUPADA))
        room_repo.create(_room("102", RoomStatus.DISPONIBLE))
        db_session.commit()
        occupied = room_repo.get_by_status(RoomStatus.OCUPADA)
        assert len(occupied) == 1
        assert occupied[0].room_number == "101"

    def test_get_not_in_maintenance(self, room_repo, db_session):
        room_repo.create(_room("101", RoomStatus.DISPONIBLE))
        room_repo.create(_room("102", RoomStatus.OCUPADA))
        room_repo.create(_room("103", RoomStatus.MANTENIMIENTO))
        db_session.commit()
        result = room_repo.get_not_in_maintenance()
        numbers = {r.room_number for r in result}
        assert numbers == {"101", "102"}


class TestActiveOverlapIds:
    def _seed_room(self, room_repo, db_session):
        room = _room("101")
        room_repo.create(room)
        db_session.commit()
        return room

    def test_intersecting_active_included(self, room_repo, res_repo, db_session):
        room = self._seed_room(room_repo, db_session)
        res_repo.create(
            _reservation(room.id, date(2026, 9, 1), date(2026, 9, 5))
        )
        db_session.commit()
        ids = res_repo.get_room_ids_with_active_overlap(
            date(2026, 9, 3), date(2026, 9, 7)
        )
        assert ids == {room.id}

    def test_adjacent_not_included(self, room_repo, res_repo, db_session):
        room = self._seed_room(room_repo, db_session)
        res_repo.create(
            _reservation(room.id, date(2026, 9, 1), date(2026, 9, 5))
        )
        db_session.commit()
        # [Sep 5, Sep 8) adjacent to [Sep 1, Sep 5) → no overlap
        ids = res_repo.get_room_ids_with_active_overlap(
            date(2026, 9, 5), date(2026, 9, 8)
        )
        assert ids == set()

    def test_checked_in_included(self, room_repo, res_repo, db_session):
        room = self._seed_room(room_repo, db_session)
        res_repo.create(
            _reservation(
                room.id, date(2026, 9, 1), date(2026, 9, 5),
                status=ReservationStatus.CHECKED_IN,
            )
        )
        db_session.commit()
        ids = res_repo.get_room_ids_with_active_overlap(
            date(2026, 9, 2), date(2026, 9, 4)
        )
        assert ids == {room.id}

    def test_cancelled_and_checked_out_excluded(
        self, room_repo, res_repo, db_session
    ):
        room = self._seed_room(room_repo, db_session)
        res_repo.create(
            _reservation(
                room.id, date(2026, 9, 1), date(2026, 9, 5),
                status=ReservationStatus.CANCELLED,
            )
        )
        res_repo.create(
            _reservation(
                room.id, date(2026, 9, 1), date(2026, 9, 5),
                status=ReservationStatus.CHECKED_OUT,
            )
        )
        db_session.commit()
        ids = res_repo.get_room_ids_with_active_overlap(
            date(2026, 9, 2), date(2026, 9, 4)
        )
        assert ids == set()


class TestQueryHistory:
    def _seed(self, room_repo, res_repo, db_session):
        room_repo.create(_room("101"))
        room_repo.create(_room("102"))
        db_session.commit()
        res_repo.create(
            _reservation(1, date(2026, 9, 1), date(2026, 9, 5),
                         status=ReservationStatus.CONFIRMED)
        )
        res_repo.create(
            _reservation(1, date(2026, 10, 1), date(2026, 10, 5),
                         status=ReservationStatus.CHECKED_OUT)
        )
        res_repo.create(
            _reservation(2, date(2026, 9, 1), date(2026, 9, 3),
                         status=ReservationStatus.CANCELLED)
        )
        db_session.commit()

    def test_no_filters_returns_all_statuses(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        assert len(res_repo.query_history()) == 3

    def test_filter_by_room(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        assert len(res_repo.query_history(room_id=1)) == 2

    def test_filter_by_status(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        result = res_repo.query_history(status=ReservationStatus.CANCELLED)
        assert len(result) == 1
        assert result[0].room_id == 2

    def test_combined_and_filters(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        result = res_repo.query_history(
            room_id=1, status=ReservationStatus.CONFIRMED
        )
        assert len(result) == 1

    def test_date_range_intersection(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        # September window intersects only the two September reservations
        result = res_repo.query_history(
            date_from=date(2026, 9, 1), date_to=date(2026, 9, 30)
        )
        assert len(result) == 2

    def test_no_matches_returns_empty(self, room_repo, res_repo, db_session):
        self._seed(room_repo, res_repo, db_session)
        assert res_repo.query_history(guest_id=9999) == []
