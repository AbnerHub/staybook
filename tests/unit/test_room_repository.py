"""Unit tests for RoomRepository."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.room import Room, RoomStatus, RoomType
from app.repositories.room_repository import RoomRepository


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    """Create a RoomRepository instance with a test session."""
    return RoomRepository(db_session)


def _make_room(**overrides) -> Room:
    """Helper to create a Room instance with defaults."""
    defaults = {
        "room_number": "101",
        "room_type": RoomType.INDIVIDUAL,
        "price_per_night": Decimal("99.99"),
        "capacity": 2,
        "status": RoomStatus.DISPONIBLE,
    }
    defaults.update(overrides)
    return Room(**defaults)


class TestCreate:
    def test_create_returns_room_with_id(self, repository, db_session):
        room = _make_room()
        result = repository.create(room)

        assert result.id is not None
        assert result.room_number == "101"
        assert result.room_type == RoomType.INDIVIDUAL
        assert result.price_per_night == Decimal("99.99")
        assert result.capacity == 2
        assert result.status == RoomStatus.DISPONIBLE

    def test_create_persists_to_database(self, repository, db_session):
        room = _make_room()
        repository.create(room)
        db_session.commit()

        found = db_session.query(Room).filter_by(room_number="101").first()
        assert found is not None
        assert found.id == room.id


class TestGetById:
    def test_returns_room_when_exists(self, repository, db_session):
        room = _make_room()
        repository.create(room)
        db_session.commit()

        result = repository.get_by_id(room.id)
        assert result is not None
        assert result.room_number == "101"

    def test_returns_none_when_not_exists(self, repository):
        result = repository.get_by_id(999)
        assert result is None


class TestGetByRoomNumber:
    def test_returns_room_when_exists(self, repository, db_session):
        room = _make_room(room_number="202")
        repository.create(room)
        db_session.commit()

        result = repository.get_by_room_number("202")
        assert result is not None
        assert result.id == room.id

    def test_returns_none_when_not_exists(self, repository):
        result = repository.get_by_room_number("999")
        assert result is None


class TestGetAll:
    def test_returns_empty_list_when_no_rooms(self, repository):
        result = repository.get_all()
        assert result == []

    def test_returns_all_rooms(self, repository, db_session):
        repository.create(_make_room(room_number="101"))
        repository.create(_make_room(room_number="102"))
        repository.create(_make_room(room_number="103"))
        db_session.commit()

        result = repository.get_all()
        assert len(result) == 3


class TestGetAvailable:
    def test_returns_only_disponible_rooms(self, repository, db_session):
        repository.create(_make_room(room_number="101", status=RoomStatus.DISPONIBLE))
        repository.create(_make_room(room_number="102", status=RoomStatus.OCUPADA))
        repository.create(_make_room(room_number="103", status=RoomStatus.MANTENIMIENTO))
        repository.create(_make_room(room_number="104", status=RoomStatus.DISPONIBLE))
        db_session.commit()

        result = repository.get_available()
        assert len(result) == 2
        assert all(r.status == RoomStatus.DISPONIBLE for r in result)

    def test_returns_empty_when_none_available(self, repository, db_session):
        repository.create(_make_room(room_number="101", status=RoomStatus.OCUPADA))
        db_session.commit()

        result = repository.get_available()
        assert result == []


class TestUpdate:
    def test_persists_field_changes(self, repository, db_session):
        room = _make_room()
        repository.create(room)
        db_session.commit()

        room.price_per_night = Decimal("150.00")
        room.status = RoomStatus.MANTENIMIENTO
        result = repository.update(room)

        assert result.price_per_night == Decimal("150.00")
        assert result.status == RoomStatus.MANTENIMIENTO


class TestDelete:
    def test_removes_room_from_database(self, repository, db_session):
        room = _make_room()
        repository.create(room)
        db_session.commit()

        repository.delete(room)
        db_session.commit()

        assert repository.get_by_id(room.id) is None

    def test_get_all_excludes_deleted_room(self, repository, db_session):
        room1 = _make_room(room_number="101")
        room2 = _make_room(room_number="102")
        repository.create(room1)
        repository.create(room2)
        db_session.commit()

        repository.delete(room1)
        db_session.commit()

        result = repository.get_all()
        assert len(result) == 1
        assert result[0].room_number == "102"
