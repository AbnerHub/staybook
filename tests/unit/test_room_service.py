"""Unit tests for the RoomService business logic layer.

Validates Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 4.4, 5.1, 5.3, 5.4, 5.6, 7.2
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    RoomDuplicateException,
    RoomNotFoundException,
    RoomOccupiedException,
)
from app.models.room import Room, RoomStatus, RoomType
from app.schemas.room import RoomCreate, RoomUpdate
from app.services.room_service import RoomService


@pytest.fixture
def mock_repository():
    """Create a mock RoomRepository."""
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    """Create a RoomService with a mocked repository."""
    return RoomService(repository=mock_repository)


@pytest.fixture
def sample_room():
    """Create a sample Room instance for testing."""
    room = Room(
        id=1,
        room_number="101",
        room_type=RoomType.INDIVIDUAL,
        price_per_night=99.99,
        capacity=2,
        status=RoomStatus.DISPONIBLE,
        description="Habitación individual",
        floor=1,
    )
    return room


class TestCreateRoom:
    """Tests for RoomService.create_room."""

    def test_create_room_success(self, service, mock_repository):
        """Successfully creates a room when room_number is unique."""
        mock_repository.get_by_room_number.return_value = None
        mock_repository.create.return_value = Room(
            id=1,
            room_number="101",
            room_type=RoomType.DOBLE,
            price_per_night=150.00,
            capacity=4,
            status=RoomStatus.DISPONIBLE,
            description=None,
            floor=2,
        )

        data = RoomCreate(
            room_number="101",
            room_type=RoomType.DOBLE,
            price_per_night=150.00,
            capacity=4,
            floor=2,
        )

        result = service.create_room(data)

        assert result.room_number == "101"
        assert result.room_type == RoomType.DOBLE
        assert result.status == RoomStatus.DISPONIBLE
        mock_repository.get_by_room_number.assert_called_once_with("101")
        mock_repository.create.assert_called_once()

    def test_create_room_duplicate_raises_exception(
        self, service, mock_repository, sample_room
    ):
        """Raises RoomDuplicateException when room_number already exists."""
        mock_repository.get_by_room_number.return_value = sample_room

        data = RoomCreate(
            room_number="101",
            room_type=RoomType.SUITE,
            price_per_night=200.00,
            capacity=3,
        )

        with pytest.raises(RoomDuplicateException):
            service.create_room(data)

        mock_repository.create.assert_not_called()

    def test_create_room_defaults_status_to_disponible(
        self, service, mock_repository
    ):
        """Status defaults to 'disponible' when not explicitly set."""
        mock_repository.get_by_room_number.return_value = None
        mock_repository.create.side_effect = lambda room: room

        data = RoomCreate(
            room_number="201",
            room_type=RoomType.INDIVIDUAL,
            price_per_night=80.00,
            capacity=1,
        )

        result = service.create_room(data)

        assert result.status == RoomStatus.DISPONIBLE

    @patch("app.services.room_service.audit_log")
    def test_create_room_calls_audit_log(
        self, mock_audit, service, mock_repository
    ):
        """Audit log is called on successful room creation."""
        mock_repository.get_by_room_number.return_value = None
        created_room = Room(
            id=5,
            room_number="301",
            room_type=RoomType.SUITE,
            price_per_night=300.00,
            capacity=4,
            status=RoomStatus.DISPONIBLE,
        )
        mock_repository.create.return_value = created_room

        data = RoomCreate(
            room_number="301",
            room_type=RoomType.SUITE,
            price_per_night=300.00,
            capacity=4,
        )

        service.create_room(data)

        mock_audit.assert_called_once_with("create", 5, "success")


class TestListRooms:
    """Tests for RoomService.list_rooms."""

    def test_list_rooms_returns_all(self, service, mock_repository):
        """Returns all rooms from the repository."""
        rooms = [
            Room(id=1, room_number="101", room_type=RoomType.INDIVIDUAL,
                 price_per_night=80, capacity=1, status=RoomStatus.DISPONIBLE),
            Room(id=2, room_number="102", room_type=RoomType.DOBLE,
                 price_per_night=120, capacity=2, status=RoomStatus.OCUPADA),
        ]
        mock_repository.get_all.return_value = rooms

        result = service.list_rooms()

        assert len(result) == 2
        mock_repository.get_all.assert_called_once()

    def test_list_rooms_empty(self, service, mock_repository):
        """Returns empty list when no rooms exist."""
        mock_repository.get_all.return_value = []

        result = service.list_rooms()

        assert result == []


class TestListAvailableRooms:
    """Tests for RoomService.list_available_rooms."""

    def test_list_available_rooms(self, service, mock_repository):
        """Returns only rooms with status 'disponible'."""
        available_rooms = [
            Room(id=1, room_number="101", room_type=RoomType.INDIVIDUAL,
                 price_per_night=80, capacity=1, status=RoomStatus.DISPONIBLE),
        ]
        mock_repository.get_available.return_value = available_rooms

        result = service.list_available_rooms()

        assert len(result) == 1
        assert result[0].status == RoomStatus.DISPONIBLE
        mock_repository.get_available.assert_called_once()


class TestGetRoom:
    """Tests for RoomService.get_room."""

    def test_get_room_found(self, service, mock_repository, sample_room):
        """Returns the room when it exists."""
        mock_repository.get_by_id.return_value = sample_room

        result = service.get_room(1)

        assert result.id == 1
        assert result.room_number == "101"
        mock_repository.get_by_id.assert_called_once_with(1)

    def test_get_room_not_found(self, service, mock_repository):
        """Raises RoomNotFoundException when room does not exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(RoomNotFoundException):
            service.get_room(999)


class TestUpdateRoom:
    """Tests for RoomService.update_room."""

    def test_update_room_partial_fields(
        self, service, mock_repository, sample_room
    ):
        """Updates only the provided fields, preserving others."""
        mock_repository.get_by_id.return_value = sample_room
        mock_repository.update.return_value = sample_room

        data = RoomUpdate(price_per_night=120.00)

        result = service.update_room(1, data)

        assert result.price_per_night == 120.00
        assert result.room_number == "101"  # unchanged
        mock_repository.update.assert_called_once()

    def test_update_room_not_found(self, service, mock_repository):
        """Raises RoomNotFoundException when room does not exist."""
        mock_repository.get_by_id.return_value = None

        data = RoomUpdate(price_per_night=100.00)

        with pytest.raises(RoomNotFoundException):
            service.update_room(999, data)

    def test_update_room_duplicate_room_number(
        self, service, mock_repository, sample_room
    ):
        """Raises RoomDuplicateException when new room_number already exists."""
        other_room = Room(
            id=2, room_number="202", room_type=RoomType.DOBLE,
            price_per_night=150, capacity=3, status=RoomStatus.DISPONIBLE,
        )
        mock_repository.get_by_id.return_value = sample_room
        mock_repository.get_by_room_number.return_value = other_room

        data = RoomUpdate(room_number="202")

        with pytest.raises(RoomDuplicateException):
            service.update_room(1, data)

        mock_repository.update.assert_not_called()

    def test_update_room_same_room_number_no_conflict(
        self, service, mock_repository, sample_room
    ):
        """No conflict when updating with the same room_number."""
        mock_repository.get_by_id.return_value = sample_room
        mock_repository.update.return_value = sample_room

        data = RoomUpdate(room_number="101")

        result = service.update_room(1, data)

        # Should not check for duplicates since the number didn't change
        mock_repository.get_by_room_number.assert_not_called()
        assert result.room_number == "101"

    @patch("app.services.room_service.audit_log")
    def test_update_room_calls_audit_log(
        self, mock_audit, service, mock_repository, sample_room
    ):
        """Audit log is called on successful room update."""
        mock_repository.get_by_id.return_value = sample_room
        mock_repository.update.return_value = sample_room

        data = RoomUpdate(capacity=5)

        service.update_room(1, data)

        mock_audit.assert_called_once_with("update", 1, "success")


class TestDeleteRoom:
    """Tests for RoomService.delete_room."""

    def test_delete_room_disponible(
        self, service, mock_repository, sample_room
    ):
        """Successfully deletes a room with status 'disponible'."""
        mock_repository.get_by_id.return_value = sample_room

        service.delete_room(1)

        mock_repository.delete.assert_called_once_with(sample_room)

    def test_delete_room_mantenimiento(self, service, mock_repository):
        """Successfully deletes a room with status 'mantenimiento'."""
        room = Room(
            id=3, room_number="303", room_type=RoomType.SUITE,
            price_per_night=250, capacity=4, status=RoomStatus.MANTENIMIENTO,
        )
        mock_repository.get_by_id.return_value = room

        service.delete_room(3)

        mock_repository.delete.assert_called_once_with(room)

    def test_delete_room_ocupada_raises_exception(self, service, mock_repository):
        """Raises RoomOccupiedException when room status is 'ocupada'."""
        room = Room(
            id=2, room_number="202", room_type=RoomType.DOBLE,
            price_per_night=150, capacity=2, status=RoomStatus.OCUPADA,
        )
        mock_repository.get_by_id.return_value = room

        with pytest.raises(RoomOccupiedException):
            service.delete_room(2)

        mock_repository.delete.assert_not_called()

    def test_delete_room_not_found(self, service, mock_repository):
        """Raises RoomNotFoundException when room does not exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(RoomNotFoundException):
            service.delete_room(999)

    @patch("app.services.room_service.audit_log")
    def test_delete_room_calls_audit_log(
        self, mock_audit, service, mock_repository, sample_room
    ):
        """Audit log is called on successful room deletion."""
        mock_repository.get_by_id.return_value = sample_room

        service.delete_room(1)

        mock_audit.assert_called_once_with("delete", 1, "success")
