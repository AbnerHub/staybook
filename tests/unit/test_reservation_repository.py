"""Unit tests for ReservationRepository."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import Guest  # noqa: F401 — register table for FK
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room  # noqa: F401 — register table for FK
from app.repositories.reservation_repository import ReservationRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    return ReservationRepository(db_session)


def _make_reservation(**overrides) -> Reservation:
    defaults = {
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": date(2026, 9, 1),
        "check_out_date": date(2026, 9, 5),
        "status": ReservationStatus.CONFIRMED,
        "total_price": Decimal("400.00"),
    }
    defaults.update(overrides)
    return Reservation(**defaults)


class TestCrud:
    def test_create_returns_reservation_with_id(self, repository):
        reservation = _make_reservation()
        result = repository.create(reservation)
        assert result.id is not None
        assert result.status == ReservationStatus.CONFIRMED
        assert result.total_price == Decimal("400.00")

    def test_get_by_id(self, repository, db_session):
        reservation = _make_reservation()
        repository.create(reservation)
        db_session.commit()
        assert repository.get_by_id(reservation.id) is not None
        assert repository.get_by_id(999) is None

    def test_get_all_includes_confirmed_and_cancelled(self, repository, db_session):
        repository.create(_make_reservation(room_id=1))
        repository.create(
            _make_reservation(room_id=2, status=ReservationStatus.CANCELLED)
        )
        db_session.commit()
        assert len(repository.get_all()) == 2

    def test_update_persists_changes(self, repository, db_session):
        reservation = _make_reservation()
        repository.create(reservation)
        db_session.commit()
        reservation.status = ReservationStatus.CANCELLED
        result = repository.update(reservation)
        assert result.status == ReservationStatus.CANCELLED

    def test_no_delete_method(self, repository):
        assert not hasattr(repository, "delete")


class TestGetActiveOverlapping:
    def _seed(self, repository, db_session, **overrides):
        r = _make_reservation(**overrides)
        repository.create(r)
        db_session.commit()
        return r

    def test_intersecting_range_detected(self, repository, db_session):
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
        )
        # Requested [Sep 3, Sep 7) intersects existing [Sep 1, Sep 5)
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 3), check_out=date(2026, 9, 7)
        )
        assert len(result) == 1

    def test_adjacent_range_not_detected(self, repository, db_session):
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
        )
        # Requested [Sep 5, Sep 8) is adjacent to existing [Sep 1, Sep 5): no overlap
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 5), check_out=date(2026, 9, 8)
        )
        assert result == []

    def test_adjacent_range_before_not_detected(self, repository, db_session):
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 5), check_out_date=date(2026, 9, 8),
        )
        # Requested [Sep 1, Sep 5) ends exactly where existing starts: no overlap
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 1), check_out=date(2026, 9, 5)
        )
        assert result == []

    def test_cancelled_excluded(self, repository, db_session):
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
            status=ReservationStatus.CANCELLED,
        )
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 2), check_out=date(2026, 9, 4)
        )
        assert result == []

    def test_different_room_excluded(self, repository, db_session):
        self._seed(
            repository, db_session, room_id=2,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
        )
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 2), check_out=date(2026, 9, 4)
        )
        assert result == []

    def test_exclude_id_excludes_self(self, repository, db_session):
        r = self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
        )
        # Same range but excluding its own id → no overlap
        result = repository.get_active_overlapping(
            room_id=1,
            check_in=date(2026, 9, 1),
            check_out=date(2026, 9, 5),
            exclude_id=r.id,
        )
        assert result == []

    def test_checked_in_blocks(self, repository, db_session):
        """A checked_in reservation is active and must block overlaps."""
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
            status=ReservationStatus.CHECKED_IN,
        )
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 2), check_out=date(2026, 9, 4)
        )
        assert len(result) == 1

    def test_checked_out_excluded(self, repository, db_session):
        """A checked_out reservation is not active and must not block overlaps."""
        self._seed(
            repository, db_session,
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5),
            status=ReservationStatus.CHECKED_OUT,
        )
        result = repository.get_active_overlapping(
            room_id=1, check_in=date(2026, 9, 2), check_out=date(2026, 9, 4)
        )
        assert result == []
