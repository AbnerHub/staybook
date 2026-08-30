"""Unit tests for GuestRepository."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.guest import Guest, IdentificationType
from app.repositories.guest_repository import GuestRepository


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
    """Create a GuestRepository instance with a test session."""
    return GuestRepository(db_session)


def _make_guest(**overrides) -> Guest:
    """Helper to create a Guest instance with defaults."""
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "555-1234",
        "identification_type": IdentificationType.NATIONAL_ID,
        "identification_number": "X1234567",
    }
    defaults.update(overrides)
    return Guest(**defaults)


class TestCreate:
    def test_create_returns_guest_with_id(self, repository):
        guest = _make_guest()
        result = repository.create(guest)

        assert result.id is not None
        assert result.first_name == "John"
        assert result.email == "john.doe@example.com"
        assert result.identification_type == IdentificationType.NATIONAL_ID

    def test_create_persists_to_database(self, repository, db_session):
        guest = _make_guest()
        repository.create(guest)
        db_session.commit()

        found = (
            db_session.query(Guest)
            .filter_by(email="john.doe@example.com")
            .first()
        )
        assert found is not None
        assert found.id == guest.id


class TestGetById:
    def test_returns_guest_when_exists(self, repository, db_session):
        guest = _make_guest()
        repository.create(guest)
        db_session.commit()

        result = repository.get_by_id(guest.id)
        assert result is not None
        assert result.email == "john.doe@example.com"

    def test_returns_none_when_not_exists(self, repository):
        assert repository.get_by_id(999) is None


class TestGetByEmail:
    def test_returns_guest_when_exists(self, repository, db_session):
        guest = _make_guest(email="jane@example.com")
        repository.create(guest)
        db_session.commit()

        result = repository.get_by_email("jane@example.com")
        assert result is not None
        assert result.id == guest.id

    def test_returns_none_when_not_exists(self, repository):
        assert repository.get_by_email("missing@example.com") is None


class TestGetByIdentification:
    def test_returns_guest_when_exists(self, repository, db_session):
        guest = _make_guest(
            identification_type=IdentificationType.PASSPORT,
            identification_number="P999",
        )
        repository.create(guest)
        db_session.commit()

        result = repository.get_by_identification(
            IdentificationType.PASSPORT, "P999"
        )
        assert result is not None
        assert result.id == guest.id

    def test_returns_none_when_not_exists(self, repository):
        result = repository.get_by_identification(
            IdentificationType.PASSPORT, "P000"
        )
        assert result is None

    def test_same_number_different_type_is_distinct(self, repository, db_session):
        """A matching number but different type should not be returned."""
        guest = _make_guest(
            identification_type=IdentificationType.NATIONAL_ID,
            identification_number="DUP123",
        )
        repository.create(guest)
        db_session.commit()

        result = repository.get_by_identification(
            IdentificationType.PASSPORT, "DUP123"
        )
        assert result is None


class TestGetAll:
    def test_returns_empty_list_when_no_guests(self, repository):
        assert repository.get_all() == []

    def test_returns_all_guests(self, repository, db_session):
        repository.create(_make_guest(email="a@example.com", identification_number="1"))
        repository.create(_make_guest(email="b@example.com", identification_number="2"))
        repository.create(_make_guest(email="c@example.com", identification_number="3"))
        db_session.commit()

        assert len(repository.get_all()) == 3


class TestUpdate:
    def test_persists_field_changes(self, repository, db_session):
        guest = _make_guest()
        repository.create(guest)
        db_session.commit()

        guest.phone = "555-9999"
        guest.last_name = "Smith"
        result = repository.update(guest)

        assert result.phone == "555-9999"
        assert result.last_name == "Smith"


class TestNoDeleteMethod:
    def test_repository_has_no_delete(self, repository):
        """Guests are preserved for reservation history: no delete method."""
        assert not hasattr(repository, "delete")
