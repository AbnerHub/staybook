"""Unit tests for the ReservationService business logic layer.

Validates Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 4.2, 6.2, 7.4, 7.6, 7.9,
8.1, 8.2, 8.4, 12.1
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    GuestNotFoundException,
    ReservationAlreadyCancelledException,
    ReservationCancelledNotEditableException,
    ReservationInvalidDatesException,
    ReservationNotFoundException,
    ReservationOverlapException,
    RoomNotFoundException,
)
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import ReservationCreate, ReservationUpdate


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def mock_room_repository():
    return MagicMock()


@pytest.fixture
def mock_guest_repository():
    return MagicMock()


@pytest.fixture
def service(mock_repository, mock_room_repository, mock_guest_repository):
    from app.services.reservation_service import ReservationService

    return ReservationService(
        repository=mock_repository,
        room_repository=mock_room_repository,
        guest_repository=mock_guest_repository,
    )


def _room(price="100.00"):
    r = MagicMock()
    r.price_per_night = Decimal(price)
    return r


def _create_data(**overrides) -> ReservationCreate:
    data = {
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": date(2026, 9, 1),
        "check_out_date": date(2026, 9, 5),
    }
    data.update(overrides)
    return ReservationCreate(**data)


def _existing_reservation(**overrides) -> Reservation:
    defaults = {
        "id": 1,
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": date(2026, 9, 1),
        "check_out_date": date(2026, 9, 5),
        "status": ReservationStatus.CONFIRMED,
        "total_price": Decimal("400.00"),
    }
    defaults.update(overrides)
    return Reservation(**defaults)


class TestCreate:
    def test_success_computes_total_price(
        self, service, mock_repository, mock_room_repository, mock_guest_repository
    ):
        mock_guest_repository.get_by_id.return_value = object()
        mock_room_repository.get_by_id.return_value = _room("100.00")
        mock_repository.get_active_overlapping.return_value = []
        mock_repository.create.side_effect = lambda r: r

        result = service.create_reservation(_create_data())

        # 4 nights * 100.00
        assert result.total_price == Decimal("400.00")
        assert result.status == ReservationStatus.CONFIRMED

    def test_missing_guest_raises(
        self, service, mock_guest_repository, mock_repository
    ):
        mock_guest_repository.get_by_id.return_value = None
        with pytest.raises(GuestNotFoundException):
            service.create_reservation(_create_data())
        mock_repository.create.assert_not_called()

    def test_missing_room_raises(
        self, service, mock_guest_repository, mock_room_repository, mock_repository
    ):
        mock_guest_repository.get_by_id.return_value = object()
        mock_room_repository.get_by_id.return_value = None
        with pytest.raises(RoomNotFoundException):
            service.create_reservation(_create_data())
        mock_repository.create.assert_not_called()

    def test_overlap_raises(
        self, service, mock_guest_repository, mock_room_repository, mock_repository
    ):
        mock_guest_repository.get_by_id.return_value = object()
        mock_room_repository.get_by_id.return_value = _room()
        mock_repository.get_active_overlapping.return_value = [_existing_reservation()]
        with pytest.raises(ReservationOverlapException):
            service.create_reservation(_create_data())
        mock_repository.create.assert_not_called()

    def test_invalid_dates_raises_via_service(
        self, service, mock_guest_repository, mock_room_repository
    ):
        # Bypass schema validation to exercise the service-level guard.
        data = ReservationCreate.model_construct(
            guest_id=1,
            room_id=1,
            check_in_date=date(2026, 9, 5),
            check_out_date=date(2026, 9, 1),
        )
        mock_guest_repository.get_by_id.return_value = object()
        mock_room_repository.get_by_id.return_value = _room()
        with pytest.raises(ReservationInvalidDatesException):
            service.create_reservation(data)

    @patch("app.services.reservation_service.audit_log")
    def test_calls_audit_log(
        self, mock_audit, service, mock_guest_repository,
        mock_room_repository, mock_repository
    ):
        mock_guest_repository.get_by_id.return_value = object()
        mock_room_repository.get_by_id.return_value = _room()
        mock_repository.get_active_overlapping.return_value = []
        created = _existing_reservation()
        mock_repository.create.return_value = created

        service.create_reservation(_create_data())

        mock_audit.assert_called_once_with("create", created.id, "success")


class TestGet:
    def test_returns(self, service, mock_repository):
        r = _existing_reservation()
        mock_repository.get_by_id.return_value = r
        assert service.get_reservation(1) is r

    def test_not_found_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(ReservationNotFoundException):
            service.get_reservation(999)


class TestUpdate:
    def test_not_found_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(ReservationNotFoundException):
            service.update_reservation(999, ReservationUpdate(room_id=2))

    def test_cancelled_not_editable(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _existing_reservation(
            status=ReservationStatus.CANCELLED
        )
        with pytest.raises(ReservationCancelledNotEditableException):
            service.update_reservation(1, ReservationUpdate(room_id=2))

    def test_partial_update_recalculates_price(
        self, service, mock_repository, mock_room_repository
    ):
        mock_repository.get_by_id.return_value = _existing_reservation()
        mock_room_repository.get_by_id.return_value = _room("100.00")
        mock_repository.get_active_overlapping.return_value = []
        mock_repository.update.side_effect = lambda r: r

        # Extend to Sep 8 => 7 nights
        result = service.update_reservation(
            1, ReservationUpdate(check_out_date=date(2026, 9, 8))
        )
        assert result.check_out_date == date(2026, 9, 8)
        assert result.check_in_date == date(2026, 9, 1)  # preserved
        assert result.total_price == Decimal("700.00")

    def test_update_overlap_excludes_self(
        self, service, mock_repository, mock_room_repository
    ):
        reservation = _existing_reservation()
        mock_repository.get_by_id.return_value = reservation
        mock_room_repository.get_by_id.return_value = _room()
        mock_repository.get_active_overlapping.return_value = []
        mock_repository.update.side_effect = lambda r: r

        service.update_reservation(1, ReservationUpdate(check_in_date=date(2026, 9, 1)))

        _, kwargs = mock_repository.get_active_overlapping.call_args
        assert kwargs["exclude_id"] == reservation.id

    def test_update_missing_room_raises(
        self, service, mock_repository, mock_room_repository
    ):
        mock_repository.get_by_id.return_value = _existing_reservation()
        mock_room_repository.get_by_id.return_value = None
        with pytest.raises(RoomNotFoundException):
            service.update_reservation(1, ReservationUpdate(room_id=999))


class TestCancel:
    def test_success_sets_cancelled(self, service, mock_repository):
        reservation = _existing_reservation()
        mock_repository.get_by_id.return_value = reservation
        mock_repository.update.side_effect = lambda r: r

        result = service.cancel_reservation(1)
        assert result.status == ReservationStatus.CANCELLED

    def test_not_found_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(ReservationNotFoundException):
            service.cancel_reservation(999)

    def test_already_cancelled_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = _existing_reservation(
            status=ReservationStatus.CANCELLED
        )
        with pytest.raises(ReservationAlreadyCancelledException):
            service.cancel_reservation(1)

    @patch("app.services.reservation_service.audit_log")
    def test_calls_audit_log(self, mock_audit, service, mock_repository):
        reservation = _existing_reservation()
        mock_repository.get_by_id.return_value = reservation
        mock_repository.update.side_effect = lambda r: r

        service.cancel_reservation(1)
        mock_audit.assert_called_once_with("cancel", reservation.id, "success")
